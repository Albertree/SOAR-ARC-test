"""
rule_engine — Dynamic loader and registry for base rules.

Scans procedural_memory/base_rules/ at first use, imports all rule modules,
and provides try_all() / apply() as the sole interface for GeneralizeOperator
and PredictOperator.

All rules are treated as data (standalone modules) not hardcoded logic.
New rules can be added by dropping a .py file into the appropriate category
directory — they will be auto-discovered on next load.
"""

import importlib
import os
import sys

_registry = {}       # rule_type -> module
_try_order = []      # list of modules in priority order
_loaded = False

# Priority order for rule evaluation — first match wins.
# The engine auto-discovers all .py modules in base_rules/ categories.
# Rules listed here are tried in this order; any newly added rules
# not in this list are appended at the end automatically.
WATERFALL_ORDER = [
    "fill_rect_by_size",
    "scale_up",
    "mirror_vertical_append",
    "recolor_sequential",
    "color_mapping",
]


def _ensure_loaded():
    """Lazy-load all rule modules on first call."""
    global _loaded
    if _loaded:
        return

    # Add project root to sys.path so procedural_memory is importable
    project_root = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    base_dir = os.path.join(project_root, "procedural_memory", "base_rules")
    if not os.path.isdir(base_dir):
        _loaded = True
        return

    for category in sorted(os.listdir(base_dir)):
        cat_path = os.path.join(base_dir, category)
        if not os.path.isdir(cat_path) or category.startswith("_"):
            continue
        for fname in sorted(os.listdir(cat_path)):
            if not fname.endswith(".py") or fname.startswith("_"):
                continue
            module_name = fname[:-3]
            full_module = f"procedural_memory.base_rules.{category}.{module_name}"
            try:
                mod = importlib.import_module(full_module)
                rule_type = getattr(mod, "RULE_TYPE", None)
                if rule_type:
                    _registry[rule_type] = mod
            except Exception as e:
                # Log but don't crash — a broken rule shouldn't kill the pipeline
                print(f"[rule_engine] WARNING: failed to load {full_module}: {e}")

    # Build priority order from WATERFALL_ORDER
    for rule_type in WATERFALL_ORDER:
        if rule_type in _registry:
            _try_order.append(_registry[rule_type])

    # Append any newly added rules not in WATERFALL_ORDER
    for rule_type, mod in _registry.items():
        if mod not in _try_order:
            _try_order.append(mod)

    _loaded = True


def try_all(patterns, task):
    """Try each rule in priority order. Returns first matching rule dict, or None."""
    _ensure_loaded()
    for mod in _try_order:
        try:
            result = mod.try_rule(patterns, task)
            if result is not None:
                return result
        except Exception:
            continue
    return None


def apply(rule_type, rule, input_grid):
    """Apply a specific rule by type. Returns grid (list-of-lists) or None."""
    _ensure_loaded()
    mod = _registry.get(rule_type)
    if mod is None:
        return None
    try:
        return mod.apply_rule(rule, input_grid)
    except Exception:
        return None


def registered_types():
    """Return set of all registered rule types (for diagnostics)."""
    _ensure_loaded()
    return set(_registry.keys())


def registered_count():
    """Return number of registered rules."""
    _ensure_loaded()
    return len(_registry)
