"""
rule_engine — Concept-only rule matching engine.

All transformation knowledge lives as parameterized concepts (JSON) in
procedural_memory/concepts/. The concept engine matches tasks using ARCKG
COMM/DIFF structures, infers parameters, and applies primitive compositions.

Claude Code extends the system by adding:
  - New concept JSONs to procedural_memory/concepts/
  - New inference methods to procedural_memory/base_rules/_concept_engine.py
  NOTE: _primitives.py is FROZEN. Do not add new primitives.
"""

import os
import sys

_loaded = False


def _ensure_loaded():
    """Ensure project root is on sys.path for imports."""
    global _loaded
    if _loaded:
        return
    project_root = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    _loaded = True


def try_all(patterns, task):
    """Match concepts against task. Returns first matching rule dict or None."""
    _ensure_loaded()
    try:
        from procedural_memory.base_rules._concept_engine import try_concepts
        result = try_concepts(patterns, task)
        if result is not None:
            return result
    except Exception:
        pass
    return None


def apply(rule_type, rule, input_grid):
    """Apply a concept rule to input grid. Returns grid (list-of-lists) or None."""
    _ensure_loaded()
    if rule_type.startswith("concept:"):
        try:
            from procedural_memory.base_rules._concept_engine import apply_concept
            return apply_concept(rule, input_grid)
        except Exception:
            return None
    return None


def registered_types():
    """Return set of all loaded concept IDs."""
    _ensure_loaded()
    try:
        from procedural_memory.base_rules._concept_engine import _ensure_loaded as cl, _concepts
        cl()
        return {c["concept_id"] for c in _concepts}
    except Exception:
        return set()


def registered_count():
    """Return number of loaded concepts."""
    return len(registered_types())
