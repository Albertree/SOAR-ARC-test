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

    PLAYBOOK=$(python -c "
import sys; sys.path.insert(0, '.')
from agent.playbook import load_playbook, render_for_prompt
import os
if os.path.exists('PLAYBOOK.json'):
    print(render_for_prompt(load_playbook()))
else:
    print('No playbook yet.')
" 2>/dev/null || echo "Playbook unavailable.")

    REFLECTIONS=$(cat $(ls -t logs/reflections_*.json 2>/dev/null | head -1) 2>/dev/null || echo "none")

    timeout "$CLAUDE_TIMEOUT" claude -p "$(cat <<PROMPT
You are session ${SESSION} of the SOAR-ARC improvement loop.

CONTEXT:
Read CLAUDE.md for architecture. The playbook below is your primary reference.

CURRENT PLAYBOOK:
${PLAYBOOK}

LEARN OUTPUT FROM THIS SESSION:
${LEARN_OUTPUT}

REFLECTIONS (generated by scripts/reflect.py):
${REFLECTIONS}

YOUR TASK THIS SESSION:

Step 1 — FAILURE ANALYSIS
Pick 1-3 INCORRECT tasks from the learn output above.
For each, read its JSON from data/ARC_AGI/training/<hex>.json.

Step 2 — STRATEGY SYNTHESIS
Group failures that share the same comparison topology.
For each group, propose ONE strategy (max 2 strategies per session).

Step 3 — IMPLEMENTATION
For each strategy, create a concept JSON in procedural_memory/concepts/<name>.json.

Available primitives (FROZEN — 24 functions): scale, flip_vertical, flip_horizontal,
rotate_cw, transpose, gravity, concat_vertical, concat_horizontal, overlay, recolor,
fill_region, mask_keep, extract_subgrid, extract_column, extract_row, extract_objects,
make_uniform, place_column, place_row, find_bg_color, grid_dimensions,
find_separator_lines, count_color, unique_colors

Available inference methods: bg_color, ratio_hw, color_map_from_arckg, non_bg_single,
column_index_from_arckg, from_examples, separator_color, color_added_in_output,
source_color_from_arckg, start_color_from_arckg

Concept JSON format:
{
  "concept_id": "<name>",
  "version": 1,
  "description": "One-line description",
  "signature": {"grid_size_preserved": true/false},
  "parameters": {"param": {"type": "int|color|color_map", "infer": "method_name"}},
  "steps": [{"id": "s1", "primitive": "fn", "args": {"grid": "\$input"}, "output": "result"}],
  "result": "\$result"
}

Step 4 — QUICK VALIDATION
Run: python run_task.py
Check for [CONCEPT] log lines — they show exactly why a concept failed.

Step 5 — SESSION LOG
Append results to logs/session_log.md.

CRITICAL RULES:
- Do NOT create Python rule modules. ALL rules must be concept JSONs.
- Do NOT modify: data/, agent/cycle.py, agent/wm.py, _primitives.py
- Do NOT hardcode task-specific colors or positions — use parameterized inference.
- Each concept must handle a CATEGORY of tasks, not just one.
- If a concept fails, READ the [CONCEPT] log lines to understand WHY, then fix it.
PROMPT
)" \
        --permission-mode bypassPermissions \
        --output-format stream-json \
        --verbose \
        2>&1 | tee -a "$PIPELINE_LOG" | tee "$SESSION_LOG"

    CLAUDE_EXIT=$?
    if [ $CLAUDE_EXIT -eq 124 ]; then
        log "[!] Claude Code timed out after ${CLAUDE_TIMEOUT}s"
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
