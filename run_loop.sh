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

# ── Phase graduation (easy → training) ──────────────────────
# The loop starts in the `easy` phase (probe = controlled slice tasks under
# data/ARC_easy*/). When the easy probe is solved 100% for GRADUATION_K
# consecutive iters, the loop graduates to the `training` phase (probe samples
# real ARC tasks under data/ARC_AGI/training/). The switch is criteria-gated,
# logged, and recorded in PHASE_STATE — the F6-allowed exception, NOT a silent
# budget creep. See docs/INVARIANTS.md F6, PROMPT.md §2.1, CLAUDE.md "Loop phases".
GRADUATION_K=5            # consecutive 100% easy probes required to graduate
TRAIN_PROBE_SIZE=3       # tasks sampled from training in the training phase
GRADUATION_ENABLED=1     # --no-graduation pins the loop to the easy phase
PHASE_STATE="${LOG_DIR}/_phase_state.json"
# Honest self-termination: when Claude judges the system sufficiently developed
# it writes this sentinel (PROMPT.md §2.2). The loop finishes the current iter,
# then stops. Delete the file to resume a stopped loop.
DONE_SENTINEL="${LOG_DIR}/_LOOP_COMPLETE.md"

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --max-sessions)     MAX_SESSIONS="$2"; shift ;;
        --probe-size)       PROBE_SIZE="$2";   shift ;;
        --probe-seed)       PROBE_SEED="$2";   shift ;;
        --graduation-k)     GRADUATION_K="$2"; shift ;;
        --train-probe-size) TRAIN_PROBE_SIZE="$2"; shift ;;
        --no-graduation)    GRADUATION_ENABLED=0 ;;
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

# ── Phase state helpers (JSON via python for cross-platform portability) ──
# State shape: {"phase": "easy"|"training", "easy_clean_streak": int,
#               "graduated_at_iter": int|null}
phase_read() {  # $1 = key  → prints value (empty if missing/unreadable)
    python - "$PHASE_STATE" "$1" <<'PY' 2>/dev/null || true
import json, sys
try:
    with open(sys.argv[1]) as f:
        d = json.load(f)
    v = d.get(sys.argv[2])
    print("" if v is None else v)
except Exception:
    print("")
PY
}

phase_write() {  # $1 = phase  $2 = streak  $3 = graduated_at_iter (or "null")
    python - "$PHASE_STATE" "$1" "$2" "$3" <<'PY' 2>/dev/null || true
import json, sys
path, phase, streak, grad = sys.argv[1:5]
grad_v = None if grad in ("", "null") else int(grad)
with open(path, "w") as f:
    json.dump({"phase": phase,
               "easy_clean_streak": int(streak),
               "graduated_at_iter": grad_v}, f, indent=2)
PY
}

# Initialize phase state on first run.
if [ ! -f "$PHASE_STATE" ]; then
    phase_write "easy" 0 "null"
fi
PHASE=$(phase_read phase);            [ -z "$PHASE" ] && PHASE="easy"
EASY_STREAK=$(phase_read easy_clean_streak); [ -z "$EASY_STREAK" ] && EASY_STREAK=0
GRAD_ITER=$(phase_read graduated_at_iter);   [ -z "$GRAD_ITER" ] && GRAD_ITER="null"

log "=========================================="
log "ARBOR Infinite Loop"
log "Branch: $BRANCH | probe-size: $PROBE_SIZE | probe-seed: $PROBE_SEED"
log "Phase: $PHASE | easy-streak: $EASY_STREAK/$GRADUATION_K | graduation: $([ "$GRADUATION_ENABLED" = 1 ] && echo on || echo off)"
log "Reward function: docs/INVARIANTS.md"
log "=========================================="

while true; do

    # Honest self-termination — a previous iter judged the system done (§2.2).
    if [ -f "$DONE_SENTINEL" ]; then
        log "*** LOOP COMPLETE — $DONE_SENTINEL present. ARBOR judged sufficiently developed. ***"
        log "    (delete $DONE_SENTINEL to resume the loop.)"
        {
            echo ""
            echo "> **LOOP COMPLETE** after iter $ITER — sentinel $DONE_SENTINEL present."
            echo "> The loop stopped itself; see that file for the justification."
        } >> "${LOG_DIR}/session_log.md"
        break
    fi

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

    # ── 1. PROBE (phase-aware) ──────────────────────────────
    # Always run the easy probe (ARC_easy) + the easy_a milestone probe (all of
    # data/ARC_easy_a). In `easy` phase they ARE the probe and gate graduation;
    # in `training` phase they are the regression guard (PROMPT.md §2.1/§2.2).
    log "Easy probe: run_learn.py --limit $PROBE_SIZE --seed $PROBE_SEED"
    EASY_OUTPUT=$(python run_learn.py --limit "$PROBE_SIZE" --seed "$PROBE_SEED" 2>&1 || true)
    echo "$EASY_OUTPUT" >> "$PIPELINE_LOG"
    EASY_SCORE=$(echo "$EASY_OUTPUT" | grep -E "Correct:" | tail -1 || echo "Correct: ? / $PROBE_SIZE")
    EASY_PCT=$(echo "$EASY_SCORE" | grep -oE '[0-9.]+%' | tr -d '%' | tail -1)
    [ -z "$EASY_PCT" ] && EASY_PCT="0"
    EASY_CLEAN=$(awk -v p="$EASY_PCT" 'BEGIN{print (p+0>=100)?1:0}')

    # easy_a milestone probe — ALL of data/ARC_easy_a (no --limit). The user's
    # gating milestone is "solve all of easy_a" before moving on (§2.2).
    EASYA_SCORE="Correct: (no easy_a dir)"
    EASYA_CLEAN=1
    if [ -d "data/ARC_easy_a" ]; then
        EASYA_OUTPUT=$(python run_learn.py --task-dir data/ARC_easy_a --seed "$PROBE_SEED" 2>&1 || true)
        echo "$EASYA_OUTPUT" >> "$PIPELINE_LOG"
        EASYA_SCORE=$(echo "$EASYA_OUTPUT" | grep -E "Correct:" | tail -1 || echo "Correct: ? / ?")
        EASYA_PCT=$(echo "$EASYA_SCORE" | grep -oE '[0-9.]+%' | tr -d '%' | tail -1)
        [ -z "$EASYA_PCT" ] && EASYA_PCT="0"
        EASYA_CLEAN=$(awk -v p="$EASYA_PCT" 'BEGIN{print (p+0>=100)?1:0}')
    fi

    # easy mastery = ARC_easy clean AND all of easy_a clean.
    if [ "$EASY_CLEAN" = "1" ] && [ "$EASYA_CLEAN" = "1" ]; then
        MASTERY_CLEAN=1
    else
        MASTERY_CLEAN=0
    fi

    if [ "$PHASE" = "training" ]; then
        # Probe samples real ARC training tasks (deterministic via fixed seed).
        PROBE_CMD="run_learn.py --split training --limit $TRAIN_PROBE_SIZE --shuffle --seed $PROBE_SEED"
        log "Training probe: $PROBE_CMD"
        TRAIN_OUTPUT=$(python run_learn.py --split training --limit "$TRAIN_PROBE_SIZE" --shuffle --seed "$PROBE_SEED" 2>&1 || true)
        echo "$TRAIN_OUTPUT" >> "$PIPELINE_LOG"
        TRAIN_SCORE=$(echo "$TRAIN_OUTPUT" | grep -E "Correct:" | tail -1 || echo "Correct: ? / $TRAIN_PROBE_SIZE")
        PROBE_OUTPUT="[PHASE: training]
===== TRAINING PROBE ($PROBE_CMD) — primary microscope =====
$TRAIN_OUTPUT
===== REGRESSION GUARD (easy + easy_a must stay 100%) =====
ARC_easy : $EASY_SCORE
ARC_easy_a: $EASYA_SCORE
(if either dropped below 100%, fixing that regression IS this iter's gap.)
===== ESCALATION (PROMPT.md §2.2) =====
Do not emit a near-duplicate / cosmetic commit. If no real gap surfaces from the
sampled training tasks, ESCALATE: pick a training task the agent fails and close
the underlying capability gap, or author a new minimal task under challenges/
(run it with: python run_learn.py --task-dir challenges/). When you judge the
system sufficiently developed, end the loop honestly per §2.2 (write
logs/_LOOP_COMPLETE.md)."
        PROBE_SCORE="$TRAIN_SCORE"
        log "Training probe: $TRAIN_SCORE | guard easy=$EASY_SCORE easy_a=$EASYA_SCORE"
    else
        # easy phase — graduation accounting on the easy_a mastery milestone.
        if [ "$MASTERY_CLEAN" = "1" ]; then
            EASY_STREAK=$((EASY_STREAK + 1))
        else
            EASY_STREAK=0
        fi
        PROBE_OUTPUT="[PHASE: easy | mastery-streak: $EASY_STREAK/$GRADUATION_K]
Mastery milestone = solve the easy slice AND all of easy_a (§2.2).
===== EASY PROBE (run_learn.py --limit $PROBE_SIZE --seed $PROBE_SEED) =====
$EASY_OUTPUT
===== EASY_A MILESTONE PROBE (run_learn.py --task-dir data/ARC_easy_a) =====
$EASYA_SCORE"
        PROBE_SCORE="$EASY_SCORE | easy_a: $EASYA_SCORE"
        log "Easy probe: $EASY_SCORE | easy_a: $EASYA_SCORE | mastery-streak: $EASY_STREAK/$GRADUATION_K"

        # Graduate once the easy_a mastery milestone holds for K consecutive iters.
        if [ "$GRADUATION_ENABLED" = "1" ] && [ "$EASY_STREAK" -ge "$GRADUATION_K" ]; then
            PHASE="training"
            GRAD_ITER="$ITER"
            phase_write "training" "$EASY_STREAK" "$ITER"
            log "*** PHASE GRADUATION: easy → training at iter $ITER ($EASY_STREAK consecutive mastery iters) ***"
            {
                echo ""
                echo "> **PHASE GRADUATION** at iter $ITER — easy → training."
                echo "> Easy slice + all of easy_a solved 100% for $EASY_STREAK consecutive iters (K=$GRADUATION_K)."
                echo "> Probe now samples data/ARC_AGI/training/ (ARC-AGI-2). easy + easy_a kept as regression guard."
                echo "> Per PROMPT.md §2.2 the loop may now also author challenges/ and will end itself when sufficiently developed."
            } >> "${LOG_DIR}/session_log.md"
        else
            phase_write "easy" "$EASY_STREAK" "null"
        fi
    fi

    # ── 2. SNAPSHOT ─────────────────────────────────────────
    ./scripts/check_invariants.sh --snapshot "$SNAPSHOT_PATH" \
        2>&1 | tee -a "$PIPELINE_LOG"

    # ── 3. CLAUDE ───────────────────────────────────────────
    log "Invoking Claude with PROMPT.md..."

    claude -p "$(cat <<PROMPT
You are iter ${ITER} of the ARBOR infinite loop on branch ${BRANCH}.

Your authoritative input is PROMPT.md. Read it now and execute it.

CONTEXT FROM THE LOOP (not part of PROMPT.md, just situational):

  - The loop is in the **${PHASE}** phase (see PROMPT.md §2.1). The probe has
    already been run for you; its output below states the phase and the exact
    command. In the training phase it samples real ARC tasks and also carries a
    one-line easy regression guard. The probe is a microscope, not a target.

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
        # The hard reset also discarded this iter's phase-state write; restore it
        # from the in-memory phase so the file stays in sync across a restart.
        phase_write "$PHASE" "$EASY_STREAK" "$GRAD_ITER"
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
