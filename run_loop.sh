#!/bin/bash

# Windows PATH fix — detect WSL vs Git Bash
if [ -d "/mnt/c" ]; then
    PRE="/mnt/c"
else
    PRE="/c"
fi
export PATH="${PRE}/Users/Sir_K/anaconda3:${PRE}/Users/Sir_K/anaconda3/Scripts:${PRE}/Program Files/nodejs:${PRE}/Users/Sir_K/AppData/Roaming/npm:${PRE}/Users/Sir_K/AppData/Local/Microsoft/WindowsApps:$PATH"

# ============================================================
# SOAR-ARC Infinite Loop
#
# The only script you need to run.
#
# Each iteration:
#   1. Agent solves 20 tasks, accumulates rules in memory
#   2. Claude Code reads results, improves the agent
#   3. Regression check
#   4. Git commit & push
#   5. Repeat
#
# Usage (from PowerShell — must use Git Bash, NOT WSL):
#   & "C:\Program Files\Git\bin\bash.exe" run_loop.sh
#   & "C:\Program Files\Git\bin\bash.exe" run_loop.sh --max-sessions 10
#   & "C:\Program Files\Git\bin\bash.exe" run_loop.sh --tasks-per-session 30
# ============================================================

MAX_SESSIONS=999
MAX_DURATION=$((48 * 60 * 60))
TASKS_PER_SESSION=16
MAX_TASKS=1000
LOG_DIR="logs"
BRANCH=$(git rev-parse --abbrev-ref HEAD)

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --max-sessions) MAX_SESSIONS="$2"; shift ;;
        --tasks-per-session) TASKS_PER_SESSION="$2"; shift ;;
        *) echo "Unknown: $1"; exit 1 ;;
    esac
    shift
done

mkdir -p "$LOG_DIR"
START_TIME=$(date +%s)
PIPELINE_LOG="${LOG_DIR}/loop.log"
SUMMARY_FILE="${LOG_DIR}/summary.md"

# Write header only if file does not exist yet
if [ ! -f "$SUMMARY_FILE" ]; then
    cat > "$SUMMARY_FILE" <<'SUMHDR'
# SOAR-ARC ez-main — Session Summary

> Auto-generated. Each session appends one entry.

SUMHDR
fi

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$PIPELINE_LOG"
}

get_last_session() {
    if [ -f "${LOG_DIR}/session_log.md" ]; then
        grep -o 'Session [0-9]*' "${LOG_DIR}/session_log.md" | tail -1 | grep -o '[0-9]*' || echo "0"
    else
        echo "0"
    fi
}

# ============================================================
# Clean start: reset memory folders
# ============================================================
log "Cleaning memory folders..."
find semantic_memory -type f ! -name '.gitkeep' -delete 2>/dev/null
find semantic_memory -type d -empty ! -path 'semantic_memory' -delete 2>/dev/null
find procedural_memory -type f ! -name '.gitkeep' -delete 2>/dev/null
find episodic_memory -type f ! -name '.gitkeep' -delete 2>/dev/null
find . -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null

SESSION=$(get_last_session)

log "=========================================="
log "SOAR-ARC Infinite Loop"
log "Tasks per session: $TASKS_PER_SESSION"
log "Max sessions: $MAX_SESSIONS"
log "=========================================="

while true; do

    ELAPSED=$(( $(date +%s) - START_TIME ))
    if [ $ELAPSED -ge $MAX_DURATION ]; then
        log "Time limit reached."
        break
    fi

    SESSION=$((SESSION + 1))
    if [ $SESSION -gt $MAX_SESSIONS ]; then
        log "Max sessions reached."
        break
    fi

    TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
    SESSION_LOG="${LOG_DIR}/session_${SESSION}_${TIMESTAMP}.log"

    log ""
    log "========== SESSION $SESSION =========="

    # ── 1. Agent solves tasks, accumulates memory ────────────
    log "Agent solving $TASKS_PER_SESSION tasks..."
    LEARN_OUTPUT=$(python run_learn.py --limit "$TASKS_PER_SESSION" 2>&1)
    echo "$LEARN_OUTPUT" | tee -a "$PIPELINE_LOG"

    SCORE_LINE=$(echo "$LEARN_OUTPUT" | grep "Correct:" | tail -1)
    RULES_LINE=$(echo "$LEARN_OUTPUT" | grep "Rules:" | tail -1)
    log "Result: $SCORE_LINE"
    log "Memory: $RULES_LINE"

    # ── Auto-grow task pool on 100% score ──────────────────
    CORRECT_N=$(echo "$SCORE_LINE" | grep -oP '\d+(?= /)' || echo "0")
    TOTAL_N=$(echo "$SCORE_LINE" | grep -oP '(?<= / )\d+' || echo "0")
    if [ "$CORRECT_N" -eq "$TOTAL_N" ] && [ "$TOTAL_N" -gt 0 ] && [ "$TASKS_PER_SESSION" -lt "$MAX_TASKS" ]; then
        TASKS_PER_SESSION=$((TASKS_PER_SESSION * 2))
        if [ "$TASKS_PER_SESSION" -gt "$MAX_TASKS" ]; then
            TASKS_PER_SESSION=$MAX_TASKS
        fi
        log "*** 100% score! Growing task pool to $TASKS_PER_SESSION ***"
    fi

    # ── 2. Claude Code improves the agent ────────────────────
    log "Claude Code improving agent..."

    CLAUDE_PROMPT_FILE=$(mktemp)
    cat > "$CLAUDE_PROMPT_FILE" <<'STATIC_TOP'
You are running a session of the SOAR-ARC ez-main experiment.

Read CLAUDE.md for architecture details.

Here are the agent results from this session:

STATIC_TOP
    printf '%s\n' "$LEARN_OUTPUT" >> "$CLAUDE_PROMPT_FILE"
    cat >> "$CLAUDE_PROMPT_FILE" <<'STATIC_BOT'

Your task:
1. Pick 1-3 INCORRECT tasks from above
2. Read their JSON from data/ARC_easy/<name>.json
3. Understand what transformation each task needs
4. Add _try_* methods in GeneralizeOperator (agent/active_operators.py)
5. Add matching _apply_* methods in PredictOperator
6. Verify: python run_task.py must output CORRECT
7. Verify: python run_learn.py shows improvement
8. Append results to logs/session_log.md

Do NOT modify: data/, agent/cycle.py, agent/wm.py
Each strategy must handle a CATEGORY of tasks, not just one.
STATIC_BOT

    claude -p "$(cat "$CLAUDE_PROMPT_FILE")" \
        --permission-mode bypassPermissions \
        --output-format stream-json \
        --verbose \
        2>&1 | tee -a "$PIPELINE_LOG" | tee "$SESSION_LOG"
    rm -f "$CLAUDE_PROMPT_FILE"

    log "Claude Code finished."

    # ── 3. Regression check ──────────────────────────────────
    if python run_task.py 2>&1 | grep -q "RESULT  : CORRECT"; then
        log "Regression: PASSED"
    else
        log "[!] Regression: FAILED"
    fi

    # ── 4. Session summary ───────────────────────────────────
    SUMMARY_FILE="${LOG_DIR}/summary.md"
    PCT=$(echo "$LEARN_OUTPUT" | grep -oP '\(\K[\d.]+(?=%)' | tail -1)
    RULES_BEFORE=$(echo "$LEARN_OUTPUT" | grep "Rules:" | grep -oP '^\s*Rules:\s*\K\d+' || echo "$LEARN_OUTPUT" | grep "Rules:" | grep -oP '\d+' | head -1)
    RULES_AFTER=$(echo "$LEARN_OUTPUT"  | grep "Rules:" | grep -oP '\d+' | tail -1)
    REGRESSION_STATUS="PASSED"
    echo "$LEARN_OUTPUT" | grep -q "Regression: FAILED" && REGRESSION_STATUS="FAILED"

    {
        echo ""
        echo "---"
        echo "## Session $SESSION — $(date '+%Y-%m-%d %H:%M')"
        echo ""
        echo "| | |"
        echo "|---|---|"
        echo "| Score | **${CORRECT_N} / ${TOTAL_N}** (${PCT}%) |"
        echo "| Rules | ${RULES_BEFORE} → ${RULES_AFTER} |"
        echo "| Regression | ${REGRESSION_STATUS} |"
        echo ""
        echo "### Per-task results"
        echo ""
        echo "| # | Task | Result | Rule | Method |"
        echo "|---|------|--------|------|--------|"
        echo "$LEARN_OUTPUT" | grep -oP '\[\d+/\d+\] \S+ \S+.*' | while IFS= read -r line; do
            IDX=$(echo "$line"  | grep -oP '(?<=\[)\d+(?=/)')
            TASK=$(echo "$line" | grep -oP '\] \K\S+')
            RES=$(echo "$line"  | grep -oP '(CORRECT|INCORRECT|ERROR)')
            RULE=$(echo "$line" | grep -oP 'rule=\K\S+')
            VIA=$(echo "$line"  | grep -oP 'via=\K\S+')
            ICON="✅"
            [ "$RES" = "INCORRECT" ] && ICON="❌"
            [ "$RES" = "ERROR" ]     && ICON="⚠️"
            echo "| $IDX | \`$TASK\` | $ICON $RES | \`$RULE\` | $VIA |"
        done
        echo ""
    } >> "$SUMMARY_FILE"

    log "Summary written → $SUMMARY_FILE"

    # ── 5. Git commit & push ─────────────────────────────────
    git add -A
    if ! git diff --cached --quiet; then
        git commit -m "Session $SESSION: $SCORE_LINE ($TIMESTAMP)" 2>&1 | tee -a "$PIPELINE_LOG"
        GIT_TERMINAL_PROMPT=0 git push origin "$BRANCH" 2>&1 | tee -a "$PIPELINE_LOG" && log "Pushed." || log "Push skipped (no credentials cached)."
    else
        log "No changes."
    fi

    log "========== SESSION $SESSION done =========="
    sleep 3

done

log "Loop finished. Sessions: $SESSION"
