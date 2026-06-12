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

# ── Phase graduation (easy_a → madeup → training) ───────────
# The loop walks a three-phase development curriculum (PROMPT.md §2.1):
#
#   1. `easy_a`   — probe = ALL of data/ARC_easy_a/. Master the hand-supplied
#                   beginner suite the *intended* way (the four observation
#                   criteria, not score).
#   2. `madeup`   — probe = ALL of data/ARC_madeup/. The loop now AUTHORS its
#                   own beginner tasks isolating one concept at a time (object
#                   size≠1, object count≠1, multi-object selection, grid resize,
#                   unequal in/out sizes, size↔object-property, pairs≠2 …) and
#                   makes the *structure* solve them by expressing each task's
#                   specific rule — without expanding concepts, without Claude
#                   hand-coding. easy_a stays as a regression guard.
#   3. `training` — probe = real ARC-AGI-2 tasks (data/ARC_AGI/training/).
#                   easy_a + madeup stay as regression guards.
#
# Each switch is criteria-gated, logged, and recorded in PHASE_STATE — the
# F6-allowed exception, NOT a silent budget creep. See docs/INVARIANTS.md F6,
# PROMPT.md §2.1, CLAUDE.md "Loop phases".
GRADUATION_K=5            # consecutive 100% probes required to graduate a phase
MADEUP_MIN_TASKS=7       # min authored data/ARC_madeup/ tasks before madeup may graduate
TRAIN_PROBE_SIZE=3       # tasks sampled from training in the training phase
GRADUATION_ENABLED=1     # --no-graduation pins the loop to its current phase
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
        --madeup-min-tasks) MADEUP_MIN_TASKS="$2"; shift ;;
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
# State shape: {"phase": "easy_a"|"madeup"|"training", "clean_streak": int,
#               "graduated_at_iter": int|null}
# `clean_streak` is the consecutive-clean count for the CURRENT phase; it
# resets to 0 on every phase graduation.
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
               "clean_streak": int(streak),
               "graduated_at_iter": grad_v}, f, indent=2)
PY
}

# Count *.json tasks in a directory (0 if absent). Used for the madeup floor.
count_tasks() {  # $1 = dir
    if [ -d "$1" ]; then
        find "$1" -maxdepth 1 -name '*.json' 2>/dev/null | wc -l | tr -d ' '
    else
        echo 0
    fi
}

# Initialize phase state on first run.
if [ ! -f "$PHASE_STATE" ]; then
    phase_write "easy_a" 0 "null"
fi
PHASE=$(phase_read phase);            [ -z "$PHASE" ] && PHASE="easy_a"
# Migrate a legacy `easy` phase (pre-curriculum) to `easy_a`.
[ "$PHASE" = "easy" ] && PHASE="easy_a"
STREAK=$(phase_read clean_streak);   [ -z "$STREAK" ] && STREAK=0
GRAD_ITER=$(phase_read graduated_at_iter);   [ -z "$GRAD_ITER" ] && GRAD_ITER="null"

log "=========================================="
log "ARBOR Infinite Loop"
log "Branch: $BRANCH | probe-size: $PROBE_SIZE | probe-seed: $PROBE_SEED"
log "Phase: $PHASE | clean-streak: $STREAK/$GRADUATION_K | graduation: $([ "$GRADUATION_ENABLED" = 1 ] && echo on || echo off)"
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

    # ── 1. PROBE (phase-aware: easy_a → madeup → training) ──────
    # data/ARC_easy was retired (user-authored, partly ill-posed). The curriculum
    # is now: master easy_a → author+solve data/ARC_madeup/ beginner tasks → real
    # ARC training. easy_a is the regression guard in every phase; madeup is an
    # additional guard once graduated past it. (PROMPT.md §2.1)

    # easy_a probe — ALL of data/ARC_easy_a (no --limit). Phase-1 probe AND the
    # always-on regression guard.
    EASYA_SCORE="Correct: (no easy_a dir)"
    EASYA_CLEAN=1
    if [ -d "data/ARC_easy_a" ]; then
        log "easy_a probe: run_learn.py --task-dir data/ARC_easy_a --seed $PROBE_SEED"
        EASYA_OUTPUT=$(python run_learn.py --task-dir data/ARC_easy_a --no-root-log --seed "$PROBE_SEED" 2>&1 || true)
        echo "$EASYA_OUTPUT" >> "$PIPELINE_LOG"
        EASYA_SCORE=$(echo "$EASYA_OUTPUT" | grep -E "Correct:" | tail -1 || echo "Correct: ? / ?")
        EASYA_PCT=$(echo "$EASYA_SCORE" | grep -oE '[0-9.]+%' | tr -d '%' | tail -1)
        [ -z "$EASYA_PCT" ] && EASYA_PCT="0"
        EASYA_CLEAN=$(awk -v p="$EASYA_PCT" 'BEGIN{print (p+0>=100)?1:0}')
    fi

    # madeup probe — ALL of data/ARC_madeup (the loop's self-authored beginner
    # curriculum). Phase-2 probe AND a guard once graduated past it. Only run when
    # relevant (madeup or training phase) so the easy_a phase stays focused.
    MADEUP_SCORE="Correct: (not yet probed)"
    MADEUP_CLEAN=1
    MADEUP_COUNT=$(count_tasks "data/ARC_madeup")
    if [ "$PHASE" = "madeup" ] || [ "$PHASE" = "training" ]; then
        if [ "$MADEUP_COUNT" -gt 0 ]; then
            log "madeup probe: run_learn.py --task-dir data/ARC_madeup ($MADEUP_COUNT tasks)"
            MADEUP_OUTPUT=$(python run_learn.py --task-dir data/ARC_madeup --no-root-log --seed "$PROBE_SEED" 2>&1 || true)
            echo "$MADEUP_OUTPUT" >> "$PIPELINE_LOG"
            MADEUP_SCORE=$(echo "$MADEUP_OUTPUT" | grep -E "Correct:" | tail -1 || echo "Correct: ? / ?")
            MADEUP_PCT=$(echo "$MADEUP_SCORE" | grep -oE '[0-9.]+%' | tr -d '%' | tail -1)
            [ -z "$MADEUP_PCT" ] && MADEUP_PCT="0"
            MADEUP_CLEAN=$(awk -v p="$MADEUP_PCT" 'BEGIN{print (p+0>=100)?1:0}')
        else
            MADEUP_SCORE="Correct: 0 / 0 (no authored tasks yet)"
            MADEUP_CLEAN=0
        fi
    fi

    if [ "$PHASE" = "training" ]; then
        # Probe samples real ARC training tasks (deterministic via fixed seed).
        PROBE_CMD="run_learn.py --split training --limit $TRAIN_PROBE_SIZE --shuffle --seed $PROBE_SEED"
        log "Training probe: $PROBE_CMD"
        TRAIN_OUTPUT=$(python run_learn.py --split training --limit "$TRAIN_PROBE_SIZE" --shuffle --no-root-log --seed "$PROBE_SEED" 2>&1 || true)
        echo "$TRAIN_OUTPUT" >> "$PIPELINE_LOG"
        TRAIN_SCORE=$(echo "$TRAIN_OUTPUT" | grep -E "Correct:" | tail -1 || echo "Correct: ? / $TRAIN_PROBE_SIZE")
        PROBE_OUTPUT="[PHASE: training]
===== TRAINING PROBE ($PROBE_CMD) — primary microscope =====
$TRAIN_OUTPUT
===== REGRESSION GUARD (easy_a + madeup must stay 100%) =====
ARC_easy_a: $EASYA_SCORE
ARC_madeup: $MADEUP_SCORE
(if either dropped below 100%, fixing that regression IS this iter's gap.)
===== ESCALATION (PROMPT.md §2.2) =====
Do not emit a near-duplicate / cosmetic commit. If no real gap surfaces from the
sampled training tasks, ESCALATE: pick a training task the agent fails and close
the underlying capability gap, or author a new minimal task under
data/ARC_madeup/ (run it with: python run_learn.py --task-dir data/ARC_madeup/).
When you judge the
system sufficiently developed, end the loop honestly per §2.2 (write
logs/_LOOP_COMPLETE.md)."
        PROBE_SCORE="$TRAIN_SCORE"
        log "Training probe: $TRAIN_SCORE | guard easy_a=$EASYA_SCORE madeup=$MADEUP_SCORE"

    elif [ "$PHASE" = "madeup" ]; then
        # Phase-2 — author+solve beginner tasks the *intended* way. Mastery =
        # easy_a still clean AND madeup 100% AND ≥ MADEUP_MIN_TASKS authored
        # (so it cannot graduate on an empty/tiny set).
        if [ "$EASYA_CLEAN" = "1" ] && [ "$MADEUP_CLEAN" = "1" ] && [ "$MADEUP_COUNT" -ge "$MADEUP_MIN_TASKS" ]; then
            STREAK=$((STREAK + 1))
        else
            STREAK=0
        fi
        PROBE_OUTPUT="[PHASE: madeup | clean-streak: $STREAK/$GRADUATION_K | authored: $MADEUP_COUNT/$MADEUP_MIN_TASKS]
Curriculum (§2.1/§2.2): AUTHOR a beginner data/ARC_madeup/ task that isolates ONE
concept not yet handled — e.g. object size≠1, object count≠1, multi-object
selection (which object matters), grid resize, unequal in/out grid sizes, grid
size tied to an object property, or example pairs≠2 — then make the STRUCTURE
solve it by expressing that task's specific rule, WITHOUT expanding concepts and
WITHOUT hand-coding a detector (F2/F3). Graduate to training only when the
structure handles a reasonable spread of these unaided.
===== MADEUP PROBE (run_learn.py --task-dir data/ARC_madeup) =====
$MADEUP_SCORE
===== REGRESSION GUARD (easy_a must stay 100%) =====
ARC_easy_a: $EASYA_SCORE"
        PROBE_SCORE="madeup: $MADEUP_SCORE | easy_a: $EASYA_SCORE"
        log "madeup probe: $MADEUP_SCORE | easy_a: $EASYA_SCORE | authored: $MADEUP_COUNT | clean-streak: $STREAK/$GRADUATION_K"

        if [ "$GRADUATION_ENABLED" = "1" ] && [ "$STREAK" -ge "$GRADUATION_K" ]; then
            PHASE="training"
            GRAD_ITER="$ITER"
            STREAK=0
            phase_write "training" 0 "$ITER"
            log "*** PHASE GRADUATION: madeup → training at iter $ITER ***"
            {
                echo ""
                echo "> **PHASE GRADUATION** at iter $ITER — madeup → training."
                echo "> data/ARC_madeup/ ($MADEUP_COUNT tasks) + easy_a solved 100% for $GRADUATION_K consecutive iters (K=$GRADUATION_K)."
                echo "> The structure now expresses task-specific rules for beginner concepts unaided."
                echo "> Probe now samples data/ARC_AGI/training/ (ARC-AGI-2). easy_a + madeup kept as regression guard."
            } >> "${LOG_DIR}/session_log.md"
        else
            phase_write "madeup" "$STREAK" "null"
        fi

    else
        # Phase-1 — easy_a. Master the supplied beginner suite the intended way.
        if [ "$EASYA_CLEAN" = "1" ]; then
            STREAK=$((STREAK + 1))
        else
            STREAK=0
        fi
        PROBE_OUTPUT="[PHASE: easy_a | clean-streak: $STREAK/$GRADUATION_K]
Milestone (§2.1) = solve ALL of data/ARC_easy_a the intended way (the four
observation criteria, not score). On mastery the loop graduates to the `madeup`
phase, where it authors its own beginner tasks.
===== EASY_A PROBE (run_learn.py --task-dir data/ARC_easy_a) =====
$EASYA_SCORE"
        PROBE_SCORE="easy_a: $EASYA_SCORE"
        log "easy_a probe: $EASYA_SCORE | clean-streak: $STREAK/$GRADUATION_K"

        if [ "$GRADUATION_ENABLED" = "1" ] && [ "$STREAK" -ge "$GRADUATION_K" ]; then
            PHASE="madeup"
            STREAK=0
            phase_write "madeup" 0 "null"
            log "*** PHASE GRADUATION: easy_a → madeup at iter $ITER ***"
            {
                echo ""
                echo "> **PHASE GRADUATION** at iter $ITER — easy_a → madeup."
                echo "> All of data/ARC_easy_a solved 100% for $GRADUATION_K consecutive iters (K=$GRADUATION_K)."
                echo "> The loop now authors its own beginner tasks under data/ARC_madeup/ (§2.2)"
                echo "> and must solve them via the structure, unaided, before attempting ARC training."
            } >> "${LOG_DIR}/session_log.md"
        else
            phase_write "easy_a" "$STREAK" "null"
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
        phase_write "$PHASE" "$STREAK" "$GRAD_ITER"
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
