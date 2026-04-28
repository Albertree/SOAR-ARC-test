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
TASKS_PER_SESSION=20
MAX_TASKS=1000
TARGET_CORRECT=40
TARGET_TOTAL=40
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
find procedural_memory -type f \( -name 'rule_*.json' -o -name 'episode_*.json' \) -delete 2>/dev/null
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
    LEARN_OUTPUT=$(python run_learn.py --limit "$TASKS_PER_SESSION" --shuffle 2>&1)
    echo "$LEARN_OUTPUT" | tee -a "$PIPELINE_LOG"

    SCORE_LINE=$(echo "$LEARN_OUTPUT" | grep "Correct:" | tail -1)
    RULES_LINE=$(echo "$LEARN_OUTPUT" | grep "Rules:" | tail -1)
    log "Result: $SCORE_LINE"
    log "Memory: $RULES_LINE"

    # ── Auto-grow task pool on 100% score ──────────────────
    CORRECT_N=$(echo "$SCORE_LINE" | grep -oP '\d+(?= /)' || echo "0")
    TOTAL_N=$(echo "$SCORE_LINE" | grep -oP '(?<= / )\d+' || echo "0")
    STOP_AFTER_COMMIT=0
    if [ "$CORRECT_N" -eq "$TARGET_CORRECT" ] && [ "$TOTAL_N" -eq "$TARGET_TOTAL" ]; then
        STOP_AFTER_COMMIT=1
        log "*** Target score reached: ${TARGET_CORRECT}/${TARGET_TOTAL}. Will stop after commit. ***"
    fi

    if [ "$CORRECT_N" -eq "$TOTAL_N" ] && [ "$TOTAL_N" -gt 0 ] && [ "$TASKS_PER_SESSION" -lt "$MAX_TASKS" ]; then
        TASKS_PER_SESSION=$((TASKS_PER_SESSION * 2))
        if [ "$TASKS_PER_SESSION" -gt "$MAX_TASKS" ]; then
            TASKS_PER_SESSION=$MAX_TASKS
        fi
        log "*** 100% score! Growing task pool to $TASKS_PER_SESSION ***"
    fi

    # ── 2. Claude Code improves the agent ────────────────────
    log "Claude Code improving agent..."

    claude -p "$(cat <<PROMPT
You are session ${SESSION} of the SOAR-ARC loop.

Read PROMPT.md for the mission. Read CLAUDE.md for architecture details.

Here are the agent's results from this session:

${LEARN_OUTPUT}

Your task:
1. Pick 1-3 INCORRECT tasks from above
2. Read their JSON from data/ARC_AGI/training/<hex>.json
3. Understand what transformation each task needs
4. PREFERRED: Create a concept JSON in procedural_memory/concepts/<name>.json
   - Compose primitives from procedural_memory/base_rules/_primitives.py
   - Use inference methods from procedural_memory/base_rules/_concept_engine.py
   - See existing concepts in procedural_memory/concepts/ for examples
   - Concept rules are parameterized and reusable across similar tasks
5. FALLBACK: If the transformation needs complex procedural logic (pathfinding, simulation),
   create a Python rule module in procedural_memory/base_rules/<category>/<name>.py
   and add its RULE_TYPE to WATERFALL_ORDER in agent/rule_engine.py
6. If you need a new primitive: add it to procedural_memory/base_rules/_primitives.py
7. If you need a new inference method: add it to procedural_memory/base_rules/_concept_engine.py
8. Verify: python run_task.py must output CORRECT
9. Verify: python run_learn.py --limit ${TASKS_PER_SESSION} --shuffle shows improvement
10. Append results to logs/session_log.md

Do NOT modify: data/, agent/cycle.py, agent/wm.py, agent/active_operators.py
Each strategy must handle a CATEGORY of tasks, not just one.
Do NOT hardcode task-specific colors or positions — use parameters.
PROMPT
)" \
        --permission-mode bypassPermissions \
        --output-format text \
        2>&1 | tee -a "$PIPELINE_LOG" | tee "$SESSION_LOG"

    log "Claude Code finished."

    # ── 3. Regression check ──────────────────────────────────
    if python run_task.py 2>&1 | grep -q "RESULT  : CORRECT"; then
        log "Regression: PASSED"
    else
        log "[!] Regression: FAILED"
    fi

    # ── 4. Git commit & push ─────────────────────────────────
    COMMIT_DONE=0
    git add -A
    if ! git diff --cached --quiet; then
        git commit -m "Session $SESSION: $SCORE_LINE ($TIMESTAMP)" 2>&1 | tee -a "$PIPELINE_LOG"
        COMMIT_DONE=1
        GIT_TERMINAL_PROMPT=0 git push origin "$BRANCH" 2>&1 | tee -a "$PIPELINE_LOG" && log "Pushed." || log "Push skipped (no credentials cached)."
    else
        log "No changes."
    fi

    if [ "$STOP_AFTER_COMMIT" -eq 1 ] && [ "$COMMIT_DONE" -eq 1 ]; then
        log "Target reached and commit created. Stopping loop."
        break
    elif [ "$STOP_AFTER_COMMIT" -eq 1 ]; then
        log "Target reached but no commit was created. Continuing loop."
    fi

    log "========== SESSION $SESSION done =========="
    sleep 3

done

log "Loop finished. Sessions: $SESSION"
