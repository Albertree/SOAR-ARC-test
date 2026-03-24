#!/bin/bash

# ============================================================
# SOAR-ARC Inner Loop Pipeline
# Claude Code repeatedly runs run_task.py until "CORRECT" is achieved
#
# Usage:
#   ./run_pipeline.sh
#   ./run_pipeline.sh --max-sessions 20
# ============================================================

MAX_SESSIONS=999        # Maximum number of sessions (effectively unlimited)
MAX_DURATION=$((24 * 60 * 60))  # 24-hour upper limit
LOG_DIR="logs"
SESSION_LOG="${LOG_DIR}/session_log.md"
PIPELINE_LOG="${LOG_DIR}/pipeline.log"
GITHUB_REPO="https://github.com/Albertree/SOAR-ARC-test.git"
BRANCH=$(git rev-parse --abbrev-ref HEAD)

# Argument parsing
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --max-sessions) MAX_SESSIONS="$2"; shift ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
    shift
done

mkdir -p "$LOG_DIR"
START_TIME=$(date +%s)

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$PIPELINE_LOG"
}

get_last_session() {
    if [ -f "$SESSION_LOG" ]; then
        grep -o '## Session [0-9]*' "$SESSION_LOG" | tail -1 | grep -o '[0-9]*' || echo "0"
    else
        echo "0"
    fi
}

check_correct() {
    # Check whether run_task.py output contains CORRECT
    # return 0 = CORRECT, 1 = INCORRECT or ERROR
    local output
    output=$(python run_task.py 2>&1)
    echo "$output"
    if echo "$output" | grep -q "RESULT  : CORRECT"; then
        return 0
    else
        return 1
    fi
}

# ============================================================
# Pre-checks
# ============================================================
log "=========================================="
log "SOAR-ARC Inner Loop Pipeline started"
log "Goal: python run_task.py → CORRECT"
log "Max sessions: $MAX_SESSIONS"
log "Max time: 24 hours"
log "=========================================="

# Check git configuration
if ! git remote get-url origin &>/dev/null; then
    log "[!] git remote origin is not set. Please configure it and re-run."
    log "    git remote add origin $GITHUB_REPO"
    exit 1
fi

# Check current status
log "Checking current status..."
if check_correct > /tmp/initial_check.txt 2>&1; then
    log "Already CORRECT! Pipeline finished."
    cat /tmp/initial_check.txt
    exit 0
fi

SESSION=$(get_last_session)
log "Last session: $SESSION. Starting from Session $((SESSION+1))."

# ============================================================
# Main loop
# ============================================================
while true; do

    # Time check
    ELAPSED=$(( $(date +%s) - START_TIME ))
    if [ $ELAPSED -ge $MAX_DURATION ]; then
        log "========== 24-hour limit reached — loop terminated =========="
        break
    fi

    # Session count check
    SESSION=$((SESSION + 1))
    if [ $SESSION -gt $MAX_SESSIONS ]; then
        log "========== Max sessions ($MAX_SESSIONS) reached — loop terminated =========="
        break
    fi

    TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
    SESSION_DETAIL_LOG="${LOG_DIR}/session_${SESSION}_${TIMESTAMP}.log"

    log ""
    log "========== SESSION $SESSION started =========="
    log "Elapsed time: ${ELAPSED}s / ${MAX_DURATION}s"

    # --------------------------------------------------------
    # Run Claude Code
    # --------------------------------------------------------
    log "Running Claude Code..."

    claude -p "$(cat <<PROMPT
You are session ${SESSION} of the SOAR-ARC inner loop pipeline.

Step 1: Read PROMPT.md completely — it contains your mission and design principles.
Step 2: Read logs/session_log.md to see what previous sessions accomplished and where they stopped.
Step 3: Run python run_task.py and carefully analyze the output and any errors.
Step 4: Based on the error analysis and the priority list in PROMPT.md, implement or fix ONE operator or rule at a time.
Step 5: Run python run_task.py again to verify your change made progress.
Step 6: Repeat steps 4-5 if time allows and you see clear next steps.
Step 7: Append your session log to logs/session_log.md following the format specified in PROMPT.md.

IMPORTANT:
- Do NOT modify files in data/ or PROMPT.md.
- Do NOT undo or rewrite work from previous sessions unless it is clearly broken.
- Build incrementally on what exists.
PROMPT
)" \
        --permission-mode bypassPermissions \
        --output-format stream-json \
        --verbose \
        2>&1 | tee -a "$PIPELINE_LOG" | tee "$SESSION_DETAIL_LOG"

    log "Claude Code finished."

    # --------------------------------------------------------
    # Result evaluation
    # --------------------------------------------------------
    log "Running run_task.py..."
    RESULT_OUTPUT=$(python run_task.py 2>&1)
    echo "$RESULT_OUTPUT" | tee -a "$PIPELINE_LOG"

    if echo "$RESULT_OUTPUT" | grep -q "RESULT  : CORRECT"; then
        log ""
        log "=========================================="
        log "CORRECT achieved! Inner Loop complete."
        log "Session: $SESSION"
        log "Elapsed time: ${ELAPSED}s"
        log "=========================================="

        # Final log update
        {
            echo ""
            echo "---"
            echo "## 🎉 MISSION COMPLETE — Session $SESSION ($TIMESTAMP)"
            echo "CORRECT achieved. Inner Loop terminated."
        } >> "$SESSION_LOG"

        # Final push
        git add -A
        git commit -m "Session $SESSION: MISSION COMPLETE — CORRECT achieved"
        git push origin "$BRANCH"

        exit 0
    fi

    log "INCORRECT — continuing to next session."

    # --------------------------------------------------------
    # Git commit & push (at the end of each session)
    # --------------------------------------------------------
    git add -A

    # Only commit when there are changes
    if ! git diff --cached --quiet; then
        COMMIT_MSG="Session $SESSION: progress update ($TIMESTAMP)"
        git commit -m "$COMMIT_MSG" 2>&1 | tee -a "$PIPELINE_LOG"
        git push origin "$BRANCH" 2>&1 | tee -a "$PIPELINE_LOG"
        log "Git push complete: $COMMIT_MSG"
    else
        log "No changes — skipping commit"
    fi

    log "========== SESSION $SESSION finished =========="
    sleep 5

done

log ""
log "Pipeline terminated. Total sessions: $SESSION"
log "Terminated without achieving CORRECT."
exit 1
