#!/bin/bash
# Force unbuffered Python output
export PYTHONUNBUFFERED=1

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
# Runs in background to avoid blocking on slow Windows I/O
# ============================================================
(
    rm -rf semantic_memory/N_T* 2>/dev/null
    rm -rf agent/__pycache__ procedural_memory/__pycache__ procedural_memory/base_rules/__pycache__ ARCKG/__pycache__ managers/__pycache__ 2>/dev/null
) &

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
    LEARN_LOG="${LOG_DIR}/learn_latest.log"
    python run_learn.py --limit "$TASKS_PER_SESSION" --shuffle 2>&1 | tee "$LEARN_LOG" | tee -a "$PIPELINE_LOG"
    LEARN_OUTPUT=$(cat "$LEARN_LOG")

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
    log "Claude Code improving agent (timeout 600s)..."

    # Select 3 most informative failing tasks:
    # Priority: tasks where a concept fired and produced wrong output
    # (validation failed) over tasks where all inference returned None.
    # These are closer to being solved and give better signal.
    FOCUS_TASKS=$(python -c "
import re, sys

log = open('logs/learn_latest.log').read()

# Find all task lines with FAIL
fail_lines = re.findall(r'\[.*?\] (\w+)\s+FAIL', log)

# For each failing task, check if it had a validation failure
# (concept fired but was wrong) vs all-None failures
partial_match = []
no_match = []

for hex_id in fail_lines:
    task_block = re.search(
        rf'\[.*?\] {hex_id}.*?(?=\[ *\d+/\d+\]|\Z)',
        log, re.DOTALL
    )
    if task_block:
        block = task_block.group()
        if 'validation failed' in block:
            partial_match.append(hex_id)
        else:
            no_match.append(hex_id)

# Prefer partial matches, deduplicate, take top 3
candidates = list(dict.fromkeys(partial_match + no_match))[:3]
print(' '.join(candidates))
" 2>/dev/null)

    if [ -z "$FOCUS_TASKS" ]; then
        FOCUS_TASKS=$(grep "FAIL" logs/learn_latest.log | head -3 | grep -oP '\] \K\w+(?=\s+FAIL)')
    fi

    CLAUDE_OUT="${LOG_DIR}/claude_latest.log"
    run_with_timeout 600 \
      claude -p "
You are doing one focused task: write concepts that solve specific
failing ARC tasks. You have 10 minutes. Do not explore beyond
what is needed for these tasks.

Read CLAUDE.md before starting to understand the architecture.

YOUR ONLY FOCUS THIS SESSION: $FOCUS_TASKS

For each task hex above, do exactly these steps in order:

STEP 1 — UNDERSTAND THE TASK
Read data/ARC_AGI/training/<hex>.json.
Look at the input and output grids for each example pair.
In one sentence, describe what transformation is happening.
Do not proceed to Step 2 until you can state the transformation
clearly in one sentence.

STEP 2 — UNDERSTAND WHY IT FAILED
From the learn log below, find the failure lines for this task.
There are two types of failures:
  Type A — 'validation failed on pair N — cell (r,c): predicted X, expected Y'
    This means a concept fired but produced wrong output.
    The concept structure is close. The problem is either:
      - wrong parameter inference, or
      - the primitive logic does not handle this variant
  Type B — 'param inference returned None'
    This means the concept could not detect a required feature.
    The task may genuinely not have that feature, or
    the inference method is too strict.
Identify which type of failure each concept had.
The most useful failures are Type A — focus on those first.

STEP 3 — CHECK EXISTING PRIMITIVES
Read procedural_memory/base_rules/_primitives.py.
Read procedural_memory/base_rules/_concept_engine.py.
Check if any existing primitive can produce the transformation
you described in Step 1, possibly with different parameters.
If yes: write a new concept JSON that uses that primitive.
If no: write a new primitive AND a new concept JSON.

STEP 4 — WRITE THE CONCEPT
The concept JSON goes in procedural_memory/concepts/.
The concept must:
  - Work on BOTH example pairs in the task, not just one
  - Use only inference methods that exist in _concept_engine.py
  - Use only primitives that exist in _primitives.py
    (or ones you just added in this session)
  - Not hardcode specific color values or grid dimensions
  - Have a signature that correctly describes what it requires

STEP 4b — CLASSIFY AND LOG WHAT YOU WROTE
After writing the concept, before testing it, write one entry
to logs/concept_origin_log.md in this exact format:

---
## <hex> — <concept_name> — Session ${SESSION}
**Classification:** GENERALIZED | NEW

If GENERALIZED:
**Parent concept:** <name of the existing concept this was derived from>
**What matched:** <what the parent concept got right on this task —
  be specific: 'the column-wise change pattern matched', 'the object
  detection fired correctly', '90% of cells were correct'>
**What was wrong:** <what the parent got wrong — be specific:
  'start_color was inferred as 2 but should be 1',
  'boundary stopped at row 4 but should continue to row 8',
  'sep_color inference returned None so the concept never fired'>
**What changed:** <exactly what you modified — parameter inference
  method, primitive logic, boundary condition, fallback chain>
**Generalization type:** PARAM_SUBSTITUTION | INFERENCE_FALLBACK |
  BOUNDARY_ADJUSTMENT | STRUCTURAL_EXTENSION | OTHER
**Could system do this automatically:** YES | NO | MAYBE
  YES = the change was a simple parameter shift or fallback that
        a rule-based system could detect and apply
  NO = the change required understanding the transformation
       semantics in a way that requires language reasoning
  MAYBE = borderline — the pattern is detectable but not obviously

If NEW:
**Why no existing concept applies:** <which concepts were tried,
  why the closest one was not generalizable — what structural
  property of this task is not covered by any existing concept>
**New primitive needed:** YES | NO
  If YES: what does the new primitive compute that no existing
  one can express?
**Category:** <one phrase describing the transformation category,
  e.g. 'self-referential tiling', 'gravity with obstacles',
  'color rank assignment'>
---

This log entry is mandatory. Do not skip it even if you are
short on time. It takes 2 minutes and produces data that will
be used to decide whether the system can automate this step.

STEP 5 — TEST
Run: python run_task.py --task <hex>
If RESULT: CORRECT — done for this task, move to next.
If RESULT: INCORRECT — read the output carefully.
  If the error is a wrong cell value: the primitive logic
  or parameter inference is wrong. Fix it.
  If the error is a size mismatch: the primitive output
  dimensions are wrong. Fix it.
  Retry once. If still wrong after one retry: stop for
  this task, document why, move to next task.
Do not retry more than once per task.

STEP 6 — REGRESSION
After finishing all tasks (or attempting all):
Run: python run_task.py
This must output RESULT: CORRECT.
If it does not: find what broke and fix it before stopping.

CONSTRAINTS — read these before writing anything:
  - Do NOT modify: data/, agent/cycle.py, agent/wm.py,
    agent/active_operators.py, agent/rule_engine.py
  - Do NOT modify existing concept JSONs
  - Do NOT look at other failing tasks beyond: $FOCUS_TASKS
  - Do NOT write more than one new primitive per task
  - Do NOT spend more than 3 minutes on any single task
  - If a task requires understanding more than one new
    primitive to solve: skip it and move to the next

OUTPUT when finished:
For each task attempted, write one line:
  <hex>: SOLVED / FAILED (<reason>)
Then write: python run_task.py → RESULT: CORRECT/INCORRECT

LEARN LOG (last 2000 chars for context):
${LEARN_OUTPUT: -2000}
" \
      --permission-mode bypassPermissions \
      --output-format text \
      --max-turns 20 \
      > "$CLAUDE_OUT" 2>&1
    CLAUDE_EXIT=$?

    echo "--- Claude output (last 30 lines) ---"
    tail -30 "$CLAUDE_OUT"
    echo "---"
    cat "$CLAUDE_OUT" >> "$PIPELINE_LOG"
    cp "$CLAUDE_OUT" "$SESSION_LOG"
    if [ $CLAUDE_EXIT -eq 124 ]; then
        log "[!] Claude Code timed out after 600s"
    else
        log "Claude Code finished (exit $CLAUDE_EXIT)."
    fi

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
