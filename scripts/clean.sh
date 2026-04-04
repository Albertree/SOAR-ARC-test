#!/bin/bash
# ============================================================
# SOAR-ARC Experiment Cleanup Script
#
# Resets all accumulated state so the agent starts from scratch.
# Keeps: architecture code, base infrastructure, research logs.
#
# Usage:
#   bash scripts/clean.sh          # interactive confirmation
#   bash scripts/clean.sh --force  # skip confirmation
# ============================================================

FORCE=false
[[ "$1" == "--force" ]] && FORCE=true

if [ "$FORCE" = false ]; then
    echo "This will remove:"
    echo "  - All concept JSONs          (procedural_memory/concepts/*.json)"
    echo "  - All accumulated rule JSONs  (procedural_memory/rule_*.json)"
    echo "  - All episodic memory         (episodic_memory/episode_*.json)"
    echo "  - All activation rules        (DSL_activation_rule/chunked_*.json)"
    echo "  - All semantic memory         (semantic_memory/ non-.gitkeep)"
    echo "  - Session-specific logs       (learn_*, session_*_*, trajectory_*, etc.)"
    echo "  - PLAYBOOK.json"
    echo ""
    echo "Will KEEP:"
    echo "  - logs/session_log.md, logs/loop.log (research logs)"
    echo "  - Base infrastructure (_primitives.py, _concept_engine.py, _helpers.py)"
    echo "  - All architecture code (agent/, scripts/, etc.)"
    echo ""
    read -p "Proceed? [y/N] " confirm
    [[ "$confirm" != "y" && "$confirm" != "Y" ]] && echo "Aborted." && exit 0
fi

echo "[clean] Removing concept JSONs..."
rm -f procedural_memory/concepts/*.json

echo "[clean] Removing accumulated rule JSONs..."
rm -f procedural_memory/rule_*.json

echo "[clean] Removing episodic memory..."
rm -f episodic_memory/episode_*.json

echo "[clean] Removing DSL activation rules..."
rm -f DSL_activation_rule/chunked_*.json

echo "[clean] Removing semantic memory..."
find semantic_memory -type f ! -name '.gitkeep' -delete 2>/dev/null
find semantic_memory -type d -empty ! -path 'semantic_memory' -delete 2>/dev/null

echo "[clean] Removing session-specific logs..."
rm -f logs/session_*_*.log
rm -f logs/learn_*.log
rm -f logs/trajectory_*.json
rm -f logs/reflections_*.json
rm -f logs/delta_*.json
rm -f logs/validation_*.json

echo "[clean] Removing PLAYBOOK.json..."
rm -f PLAYBOOK.json

echo "[clean] Removing any accumulated Python rule modules..."
# Only gravity_settle.py and similar -- never touch _primitives.py, _concept_engine.py, _helpers.py, __init__.py
find procedural_memory/base_rules -name '*.py' \
    ! -name '__init__.py' \
    ! -name '_primitives.py' \
    ! -name '_concept_engine.py' \
    ! -name '_helpers.py' \
    -delete 2>/dev/null

echo "[clean] Removing __pycache__..."
find . -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null

echo ""
echo "[clean] Done. Ready for a fresh experiment."
