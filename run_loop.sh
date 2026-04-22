#!/bin/bash

# ============================================================
# SOAR-ARC Loop — ez-main experiment
#
# Each session:
#   1. Agent solves all tasks in data/ARC_easy/
#   2. Claude consolidates rules (always) + fixes failures (only if needed)
#   3. Regression check
#   4. Summary written to logs/summary.md
#   5. Git commit & push
#   6. Plateau check: stop if score unchanged 3 sessions AND rules not shrinking
#
# Usage:
#   bash run_loop.sh
#   bash run_loop.sh --max-sessions 10
# ============================================================

MAX_SESSIONS=999
MAX_DURATION=$((48 * 60 * 60))
TASKS_PER_SESSION=16
LOG_DIR="logs"
BRANCH=$(git rev-parse --abbrev-ref HEAD)

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --max-sessions) MAX_SESSIONS="$2"; shift ;;
        *) echo "Unknown: $1"; exit 1 ;;
    esac
    shift
done

mkdir -p "$LOG_DIR"
START_TIME=$(date +%s)
PIPELINE_LOG="${LOG_DIR}/loop.log"
SUMMARY_FILE="${LOG_DIR}/summary.md"

if [ ! -f "$SUMMARY_FILE" ]; then
    cat > "$SUMMARY_FILE" <<'HDR'
# SOAR-ARC ez-test1 — Session Summary

> Auto-generated. Each session appends one entry.

HDR
fi

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$PIPELINE_LOG"
}

# macOS-compatible number extractor: get Nth integer from a string
nth_int() {
    echo "$1" | grep -oE '[0-9]+' | sed -n "${2}p"
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
find episodic_memory  -type f ! -name '.gitkeep' -delete 2>/dev/null
find . -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null

SESSION=$(get_last_session)

log "=========================================="
log "SOAR-ARC Loop — branch: $BRANCH"
log "Tasks per session: $TASKS_PER_SESSION"
log "Max sessions: $MAX_SESSIONS"
log "=========================================="

# Plateau detection: track last 3 scores and rule counts
declare -a SCORE_HISTORY=()
declare -a RULE_HISTORY=()

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

    # ── 1. Agent solves tasks ────────────────────────────────
    log "Agent solving tasks..."
    LEARN_OUTPUT=$(python run_learn.py --limit "$TASKS_PER_SESSION" 2>&1)
    echo "$LEARN_OUTPUT" | tee -a "$PIPELINE_LOG"

    # Parse score — macOS-compatible (no grep -oP)
    # run_learn.py emits: "[HH:MM:SS] Correct:     N / M  (X.X%)"
    SCORE_LINE=$(echo "$LEARN_OUTPUT" | grep "Correct:" | tail -1)
    RULES_LINE=$(echo "$LEARN_OUTPUT" | grep "Rules:"   | tail -1)

    # Strip timestamp prefix then extract fields
    SCORE_CLEAN=$(echo "$SCORE_LINE" | sed 's/\[[0-9:]*\] *//')
    RULES_CLEAN=$(echo "$RULES_LINE" | sed 's/\[[0-9:]*\] *//')

    # "Correct:     16 / 16  (100.0%)" → fields after collapsing spaces
    CORRECT_N=$(echo "$SCORE_CLEAN" | tr -s ' ' | cut -d' ' -f2)
    TOTAL_N=$(echo "$SCORE_CLEAN"   | tr -s ' ' | cut -d' ' -f4)
    PCT=$(echo "$SCORE_CLEAN" | cut -d'(' -f2 | cut -d'%' -f1)

    # "Rules:       2 -> 5  (+3 learned)" → before/after counts
    RULES_BEFORE=$(echo "$RULES_CLEAN" | tr -s ' ' | cut -d' ' -f2)
    RULES_AFTER=$(echo "$RULES_CLEAN"  | tr -s ' ' | cut -d' ' -f4)

    # Current rule file count on disk
    RULE_COUNT=$(ls procedural_memory/rule_*.json 2>/dev/null | wc -l | tr -d ' ')
    RULE_COUNT=${RULE_COUNT:-0}

    log "Score: $CORRECT_N / $TOTAL_N  ($PCT%)"
    log "Rules: $RULES_BEFORE -> $RULES_AFTER  (on disk: $RULE_COUNT)"

    # ── 2. Claude improves / consolidates ───────────────────
    log "Claude working..."

    CLAUDE_PROMPT_FILE=$(mktemp)

    cat > "$CLAUDE_PROMPT_FILE" <<HEADER
You are running session ${SESSION} of the SOAR-ARC ez-test1 experiment.
Read CLAUDE.md for architecture details.

Current state:
  Score      : ${CORRECT_N} / ${TOTAL_N}  (${PCT}%)
  Rule files : ${RULE_COUNT}  (in procedural_memory/)

Agent results this session:
HEADER

    printf '%s\n' "$LEARN_OUTPUT" >> "$CLAUDE_PROMPT_FILE"

    # Phase 1: consolidation (always)
    cat >> "$CLAUDE_PROMPT_FILE" <<'PHASE1'

════════════════════════════════════════
PHASE 1 — CONSOLIDATE RULES (always do this first)
════════════════════════════════════════
Read every file in procedural_memory/.
Goal: FEWER, MORE GENERAL rules — not more specific ones.

Actions to take:
  A. Delete duplicate rules (same type + same parameters, different source task).
  B. Merge rules that are instances of the same concept:
       e.g. color_mapping {1→0} and color_mapping {2→0} both do "darken one color"
       → keep the more general one, update "covers" to list both tasks.
  C. Rename "concept" to a short, meaningful human-readable name.
  D. Remove rules with times_reused=0 that cover only one task,
     IF an existing broader rule can already solve that task.

Every rule file MUST follow this schema exactly:
{
  "id": <int>,
  "concept": "<short name, e.g. swap_two_colors>",
  "category": "<color_transform | spatial_transform | geometric_transform | fill_transform | other>",
  "rule": { <rule parameters> },
  "covers": ["<task_id>", ...],
  "source_task": "<first task that created this rule>",
  "created_at": "<ISO datetime>",
  "times_reused": <int>
}

After consolidation, there should be at most one rule file per distinct
transformation concept. Run python run_learn.py to verify score did NOT drop.
PHASE1

    # Phase 2: improvement (only if tasks are failing)
    if [ "${CORRECT_N}" != "${TOTAL_N}" ] || [ -z "$CORRECT_N" ]; then
        cat >> "$CLAUDE_PROMPT_FILE" <<'PHASE2'

════════════════════════════════════════
PHASE 2 — FIX FAILING TASKS (score < 100%)
════════════════════════════════════════
For each INCORRECT task above:
  1. Read data/ARC_easy/<name>.json
  2. Understand what transformation it needs
  3. Add _try_<name>(self, patterns) to GeneralizeOperator in agent/active_operators.py
  4. Add _apply_<name>(self, rule, input_grid) to PredictOperator
  5. Each strategy must handle a CATEGORY of tasks, not just one specific task.
  6. Run: python run_task.py  — must output CORRECT
  7. Run: python run_learn.py — score must improve

Do NOT modify: data/, agent/cycle.py, agent/wm.py
PHASE2
    else
        cat >> "$CLAUDE_PROMPT_FILE" <<'PHASE2_SKIP'

════════════════════════════════════════
PHASE 2 — SKIPPED (score is already 100%)
════════════════════════════════════════
All tasks pass. Do NOT add new strategies.
Focus only on Phase 1 consolidation.
PHASE2_SKIP
    fi

    cat >> "$CLAUDE_PROMPT_FILE" <<'PHASE3'

════════════════════════════════════════
PHASE 3 — VERIFY & LOG
════════════════════════════════════════
  1. Run: python run_learn.py — confirm score did not decrease
  2. Append a brief summary to logs/session_log.md:
       - How many rules before / after consolidation
       - Which tasks were fixed (if any)
       - What concepts are now in procedural_memory/
PHASE3

    claude -p "$(cat "$CLAUDE_PROMPT_FILE")" \
        --permission-mode bypassPermissions \
        --output-format stream-json \
        --verbose \
        2>&1 | tee -a "$PIPELINE_LOG" | tee "$SESSION_LOG"
    rm -f "$CLAUDE_PROMPT_FILE"

    log "Claude finished."

    # ── 3. Regression check ──────────────────────────────────
    REGRESSION="PASSED"
    if ! python run_task.py 2>&1 | grep -q "RESULT  : CORRECT"; then
        REGRESSION="FAILED"
        log "[!] Regression: FAILED"
    else
        log "Regression: PASSED"
    fi

    # ── 4. Session summary ───────────────────────────────────
    RULE_COUNT_AFTER=$(ls procedural_memory/rule_*.json 2>/dev/null | wc -l | tr -d ' ')
    RULE_COUNT_AFTER=${RULE_COUNT_AFTER:-0}

    {
        echo ""
        echo "---"
        echo "## Session $SESSION — $(date '+%Y-%m-%d %H:%M')"
        echo ""
        echo "| | |"
        echo "|---|---|"
        echo "| Score | **${CORRECT_N} / ${TOTAL_N}** (${PCT}%) |"
        echo "| Rules (start → end) | ${RULE_COUNT} → ${RULE_COUNT_AFTER} |"
        echo "| Regression | ${REGRESSION} |"
        echo ""
        echo "### Per-task results"
        echo ""
        echo "| Task | Result | Rule | Method |"
        echo "|------|--------|------|--------|"
        echo "$LEARN_OUTPUT" | grep -E '\[[0-9]+/[0-9]+\]' | while IFS= read -r line; do
            TASK=$(echo "$line" | awk '{print $2}')
            RES=$(echo "$line"  | grep -oE 'CORRECT|INCORRECT|ERROR' | head -1)
            RULE=$(echo "$line" | grep -oE 'rule=[^ ]+' | cut -d= -f2)
            VIA=$(echo "$line"  | grep -oE 'via=[^ ]+' | cut -d= -f2)
            ICON="✅"; [ "$RES" = "INCORRECT" ] && ICON="❌"; [ "$RES" = "ERROR" ] && ICON="⚠️"
            echo "| \`$TASK\` | $ICON $RES | \`${RULE:-?}\` | ${VIA:-?} |"
        done
        echo ""
    } >> "$SUMMARY_FILE"

    log "Summary → $SUMMARY_FILE"

    # ── 5. Plateau check ─────────────────────────────────────
    SCORE_HISTORY+=("${CORRECT_N:-0}")
    RULE_HISTORY+=("$RULE_COUNT_AFTER")
    # Keep only last 3
    if [ ${#SCORE_HISTORY[@]} -gt 3 ]; then
        SCORE_HISTORY=("${SCORE_HISTORY[@]:1}")
        RULE_HISTORY=("${RULE_HISTORY[@]:1}")
    fi

    if [ ${#SCORE_HISTORY[@]} -eq 3 ]; then
        S0=${SCORE_HISTORY[0]}; S1=${SCORE_HISTORY[1]}; S2=${SCORE_HISTORY[2]}
        R0=${RULE_HISTORY[0]};  R2=${RULE_HISTORY[2]}
        if [ "$S0" -eq "$S1" ] 2>/dev/null && [ "$S1" -eq "$S2" ] 2>/dev/null \
           && [ "$R2" -ge "$R0" ] 2>/dev/null; then
            log "*** PLATEAU: score $S2/$TOTAL_N unchanged for 3 sessions, rules $R0 -> $R2 (not shrinking). Stopping. ***"
            {
                echo ""
                echo "---"
                echo "## LOOP STOPPED — Plateau detected"
                echo "Score stuck at **$S2 / $TOTAL_N** for 3 sessions. Rules: $R0 → $R2."
                echo ""
            } >> "$SUMMARY_FILE"
            git add -A
            git diff --cached --quiet || git commit -m "PLATEAU: score $S2/$TOTAL_N, rules $R0->$R2, stopping" 2>&1 | tee -a "$PIPELINE_LOG"
            GIT_TERMINAL_PROMPT=0 git push origin "$BRANCH" 2>&1 | tee -a "$PIPELINE_LOG"
            break
        fi
    fi

    # ── 6. Git commit & push ─────────────────────────────────
    git add -A
    if ! git diff --cached --quiet; then
        git commit -m "Session $SESSION: ${CORRECT_N}/${TOTAL_N} tasks, ${RULE_COUNT_AFTER} rules ($TIMESTAMP)" \
            2>&1 | tee -a "$PIPELINE_LOG"
        GIT_TERMINAL_PROMPT=0 git push origin "$BRANCH" 2>&1 | tee -a "$PIPELINE_LOG" \
            && log "Pushed." || log "Push skipped."
    else
        log "No changes to commit."
    fi

    log "========== SESSION $SESSION done =========="
    sleep 3

done

log "Loop finished. Sessions: $SESSION"
