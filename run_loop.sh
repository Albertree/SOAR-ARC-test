#!/bin/bash

# Windows PATH fix — detect WSL vs Git Bash
if [ -d "/mnt/c" ]; then
    PRE="/mnt/c"
else
    PRE="/c"
fi
export PATH="${PRE}/Users/Sir_K/anaconda3:${PRE}/Users/Sir_K/anaconda3/Scripts:${PRE}/Program Files/nodejs:${PRE}/Users/Sir_K/AppData/Roaming/npm:${PRE}/Users/Sir_K/AppData/Local/Microsoft/WindowsApps:$PATH"

# ============================================================
# ARBOR Infinite Loop  (post-test20 redesign)
#
# Single ultimate goal: develop an agent whose knowledge grows and whose
# problems get solved in the way the user intends. ARC score is a *probe*,
# not the reward. The reward function lives in docs/INVARIANTS.md.
#
# Each iteration:
#   1. PROBE     — run a small fixed-seed task set, save its output.
#   2. SNAPSHOT  — capture baseline metrics + HEAD hash.
#   3. CLAUDE    — invoke Claude with PROMPT.md + probe output.
#                  Claude self-diagnoses the smallest gap and fills it.
#   4. VERIFY    — scripts/check_invariants.sh evaluates the diff.
#                    exit 0 → CLEAN     (commit + push)
#                    exit 1 → VIOLATION (git revert HEAD, no push)
#                    exit 2 → NEUTRAL   (commit anyway, count toward
#                                        stagnation tally)
#   5. LOG       — append result to logs/session_log.md.
#   6. REPEAT
#
# Usage:
#   ./run_loop.sh
#   ./run_loop.sh --max-sessions 10
#   ./run_loop.sh --probe-size 3
#   ./run_loop.sh --probe-seed 42
#
# Notes:
# - Task budget (--probe-size) does NOT auto-grow. Reproducibility over
#   score chasing.  See docs/INVARIANTS.md F6.
# - Stagnation: 3 consecutive NEUTRAL iters → loud notice to session_log.
#   Loop continues; this is information for the user, not auto-stop.
# ============================================================

MAX_SESSIONS=999
MAX_DURATION=$((48 * 60 * 60))
PROBE_SIZE=3
PROBE_SEED=42
LOG_DIR="logs"
BRANCH=$(git rev-parse --abbrev-ref HEAD)
SNAPSHOT_PATH="${LOG_DIR}/_invariant_snapshot.json"

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --max-sessions) MAX_SESSIONS="$2"; shift ;;
        --probe-size)   PROBE_SIZE="$2";   shift ;;
        --probe-seed)   PROBE_SEED="$2";   shift ;;
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

get_last_iter() {
    if [ -f "${LOG_DIR}/session_log.md" ]; then
        grep -oE 'Iter [0-9]+' "${LOG_DIR}/session_log.md" | tail -1 | grep -oE '[0-9]+' || echo "0"
    else
        echo "0"
    fi
}

ITER=$(get_last_iter)
NEUTRAL_STREAK=0

log "=========================================="
log "ARBOR Infinite Loop"
log "Branch: $BRANCH | probe-size: $PROBE_SIZE | probe-seed: $PROBE_SEED"
log "Reward function: docs/INVARIANTS.md"
log "=========================================="

while true; do

    ELAPSED=$(( $(date +%s) - START_TIME ))
    if [ "$ELAPSED" -ge "$MAX_DURATION" ]; then
        log "Time limit reached."
        break
    fi

    ITER=$((ITER + 1))
    if [ "$ITER" -gt "$MAX_SESSIONS" ]; then
        log "Max sessions reached."
        break
    fi

    TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
    ITER_LOG="${LOG_DIR}/iter_${ITER}_${TIMESTAMP}.log"

    log ""
    log "========== ITER $ITER =========="

    # ── 1. PROBE ────────────────────────────────────────────
    log "Probe: run_learn.py --limit $PROBE_SIZE --seed $PROBE_SEED"
    PROBE_OUTPUT=$(python run_learn.py --limit "$PROBE_SIZE" --seed "$PROBE_SEED" 2>&1 || true)
    echo "$PROBE_OUTPUT" >> "$PIPELINE_LOG"
    PROBE_SCORE=$(echo "$PROBE_OUTPUT" | grep -E "Correct:" | tail -1 || echo "Correct: ? / $PROBE_SIZE")
    log "Probe score (microscope, NOT reward): $PROBE_SCORE"

    # ── 2. SNAPSHOT ─────────────────────────────────────────
    ./scripts/check_invariants.sh --snapshot "$SNAPSHOT_PATH" \
        2>&1 | tee -a "$PIPELINE_LOG"

    # ── 3. CLAUDE ───────────────────────────────────────────
    log "Invoking Claude with PROMPT.md..."

    claude -p "$(cat <<PROMPT
You are iter ${ITER} of the ARBOR infinite loop on branch ${BRANCH}.

Your authoritative input is PROMPT.md. Read it now and execute it.

CONTEXT FROM THE LOOP (not part of PROMPT.md, just situational):

  - The probe (run_learn.py --limit ${PROBE_SIZE} --seed ${PROBE_SEED}) has
    already been run for you. Its output:

    ===== PROBE OUTPUT =====
${PROBE_OUTPUT}
    ===== END PROBE =====

  - The baseline metric snapshot is at ${SNAPSHOT_PATH} — your post-iter
    verification (scripts/check_invariants.sh --check) will diff against
    this.

  - Forbidden signals are listed in docs/INVARIANTS.md §1. Tripping any of
    them causes the loop to auto-revert your commit. The list includes:
    frozen-file edits, new _try_* / _apply_* methods, hand-coded DSL
    primitives other than coloring/make_grid, rules without a condition
    key, TF_GRID under semantic_memory/, auto-grown task budgets,
    swallowed RuleSchemaError, and unaccompanied edits to
    agent/active_operators.py.

  - Positive signals (P1–P6 in §2) are how the loop measures progress.
    Improving even one is "real work" for this iter.

Now execute PROMPT.md. Do not solve ARC tasks for the score; treat the probe
output as a microscope showing where the system is blind.
PROMPT
)" \
        --permission-mode bypassPermissions \
        --output-format stream-json \
        --verbose \
        2>&1 | tee -a "$PIPELINE_LOG" | tee "$ITER_LOG"

    log "Claude finished."

    # ── 4. VERIFY ───────────────────────────────────────────
    log "Verifying invariants..."
    ./scripts/check_invariants.sh --check "$SNAPSHOT_PATH" 2>&1 | tee -a "$PIPELINE_LOG"
    CHECK_RC=${PIPESTATUS[0]}

    VERDICT=""
    case "$CHECK_RC" in
        0) VERDICT="CLEAN"    ; NEUTRAL_STREAK=0 ;;
        1) VERDICT="VIOLATION"; NEUTRAL_STREAK=0 ;;
        2) VERDICT="NEUTRAL"  ; NEUTRAL_STREAK=$((NEUTRAL_STREAK + 1)) ;;
        *) VERDICT="ERROR_$CHECK_RC" ;;
    esac
    log "Verdict: $VERDICT (rc=$CHECK_RC)"

    # ── 5. COMMIT / REVERT / LOG ────────────────────────────
    if [ "$VERDICT" = "VIOLATION" ]; then
        log "Reverting current iter — forbidden signal tripped."
        git reset --hard HEAD 2>&1 | tee -a "$PIPELINE_LOG"
        # If Claude already committed, undo that too.
        if git log -1 --format=%s | grep -q "^Iter $ITER"; then
            git revert --no-edit HEAD 2>&1 | tee -a "$PIPELINE_LOG" || true
        fi
    else
        # CLEAN or NEUTRAL — accept the work.
        git add -A
        if ! git diff --cached --quiet; then
            COMMIT_MSG="Iter $ITER [$VERDICT]: $PROBE_SCORE ($TIMESTAMP)"
            git commit -m "$COMMIT_MSG" 2>&1 | tee -a "$PIPELINE_LOG"
            GIT_TERMINAL_PROMPT=0 git push origin "$BRANCH" \
                2>&1 | tee -a "$PIPELINE_LOG" \
                && log "Pushed." \
                || log "Push skipped (no credentials cached)."
        else
            log "Claude produced no changes — no-op iter."
        fi
    fi

    # ── stagnation surface ──
    if [ "$NEUTRAL_STREAK" -ge 3 ]; then
        log "*** STAGNATION: $NEUTRAL_STREAK consecutive NEUTRAL iters ***"
        echo "" >> "${LOG_DIR}/session_log.md"
        echo "> STAGNATION at iter $ITER — $NEUTRAL_STREAK consecutive neutral iters." \
            >> "${LOG_DIR}/session_log.md"
    fi

    log "========== ITER $ITER done ($VERDICT) =========="
    sleep 3

done

log "Loop finished. Iters: $ITER"
