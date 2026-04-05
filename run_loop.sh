#!/bin/bash

# Windows PATH fix — detect WSL vs Git Bash
if [ -d "/mnt/c" ]; then
    PRE="/mnt/c"
else
    PRE="/c"
fi
export PATH="${PRE}/Users/ds-lab/anaconda3:${PRE}/Users/ds-lab/anaconda3/Scripts:${PRE}/Program Files/nodejs:${PRE}/Users/ds-lab/AppData/Roaming/npm:${PRE}/Users/ds-lab/AppData/Local/Microsoft/WindowsApps:$PATH"

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
CLAUDE_TIMEOUT=600
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
mkdir -p "procedural_memory/concepts"
START_TIME=$(date +%s)
PIPELINE_LOG="${LOG_DIR}/loop.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$PIPELINE_LOG"
}

# Cross-platform timeout: works on Windows Git Bash, WSL, and Linux
# (Windows timeout.exe is "sleep N", NOT GNU timeout that kills processes)
run_with_timeout() {
    local secs="$1"; shift
    "$@" &
    local pid=$!
    (
        sleep "$secs"
        kill $pid 2>/dev/null
        sleep 2
        kill -9 $pid 2>/dev/null
    ) &
    local watchdog=$!
    wait $pid 2>/dev/null
    local ret=$?
    kill $watchdog 2>/dev/null
    wait $watchdog 2>/dev/null
    if [ $ret -gt 128 ]; then
        return 124
    fi
    return $ret
}

get_last_session() {
    if [ -f "${LOG_DIR}/session_log.md" ]; then
        grep -o 'Session [0-9]*' "${LOG_DIR}/session_log.md" | tail -1 | grep -o '[0-9]*' || echo "0"
    else
        echo "0"
    fi
}

# ============================================================
# Startup cleanup: only transient caches, NEVER learned rules
# ============================================================
find semantic_memory -type f ! -name '.gitkeep' -delete 2>/dev/null
find semantic_memory -type d -empty ! -path 'semantic_memory' -delete 2>/dev/null
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
    if [ "$CORRECT_N" -eq "$TOTAL_N" ] && [ "$TOTAL_N" -gt 0 ] && [ "$TASKS_PER_SESSION" -lt "$MAX_TASKS" ]; then
        TASKS_PER_SESSION=$((TASKS_PER_SESSION * 2))
        if [ "$TASKS_PER_SESSION" -gt "$MAX_TASKS" ]; then
            TASKS_PER_SESSION=$MAX_TASKS
        fi
        log "*** 100% score! Growing task pool to $TASKS_PER_SESSION ***"
    fi

    # ── 1b. Reflect on trajectory + curate playbook ────────
    LATEST_TRAJ=$(ls -t logs/trajectory_*.json 2>/dev/null | head -1)
    if [ -n "$LATEST_TRAJ" ]; then
        log "Reflecting on trajectory..."
        python scripts/reflect.py "$LATEST_TRAJ" 2>&1 | tee -a "$PIPELINE_LOG"
        LATEST_REFL=$(ls -t logs/reflections_*.json 2>/dev/null | head -1)
        if [ -n "$LATEST_REFL" ]; then
            python scripts/curate.py "$LATEST_REFL" 2>&1 | tee -a "$PIPELINE_LOG"
        fi
    fi

    # ── 2. Claude Code improves the agent ────────────────────
    log "Claude Code improving agent (timeout ${CLAUDE_TIMEOUT}s)..."

    claude -p "$(cat PROMPT.md)

The learn output from this session was:
${LEARN_OUTPUT: -3000}

Pick 2-3 failing tasks from the log above.
Read their JSON from data/ARC_AGI/training/<hex>.json
Write new concept JSONs in procedural_memory/concepts/
Run python run_task.py to verify regression passes.
" \
      --permission-mode bypassPermissions \
      --output-format text \
      2>&1 | tee -a "$PIPELINE_LOG" | tee "$SESSION_LOG"

    log "Claude Code finished (exit $?)."

    # ── 3. Validation + regression check ─────────────────────
    if python scripts/validate_patch.py 2>&1 | tee -a "$PIPELINE_LOG"; then
        log "Patch validation: PASSED"
    else
        log "[!] Patch validation: FAILED"
    fi

    if python run_task.py 2>&1 | grep -q "RESULT  : CORRECT"; then
        log "Regression: PASSED"
    else
        log "[!] Regression: FAILED"
    fi

    # ── 4. Git commit & push ─────────────────────────────────
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
