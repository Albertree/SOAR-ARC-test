"""
grid_size_preserved — match tasks where every example pair has matching
input/output grid dimensions.

This is the foundational precondition for any "same-grid" transformation
(color remap, recolor-by-position, in-place fill, etc.). Distinguishes
recolor-style tasks from resize / tile / crop-style tasks before any rule
fires.

Params:
  (none)

Returns True iff:
  - `patterns["grid_size_preserved"]` is True, AND
  - every entry in `patterns["pair_analyses"]` reports `size_match` True.

The redundant per-pair check guards against an upstream extractor that
forgot to flip the top-level flag.
"""

from agent.conditions import register


@register("grid_size_preserved")
def match(patterns: dict, params: dict) -> bool:
    if not isinstance(patterns, dict):
        return False
    if not patterns.get("grid_size_preserved", False):
        return False
    pair_analyses = patterns.get("pair_analyses") or []
    if not pair_analyses:
        return False
    return all(bool(pa.get("size_match", False)) for pa in pair_analyses)
