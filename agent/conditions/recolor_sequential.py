"""
condition matcher: recolor_sequential.

Recognizes that objects of one or more source colours are recoloured in a
deterministic *order* (sorted by `sort_key`) starting from `start_color`.
This is the recognition half of the legacy `recolor_sequential` action (whose
transformation is, again, a composition of `coloring` over each object's
cells).

Matcher contract (docs/RULE_FORMAT.md §4): deterministic, side-effect-free,
`match(patterns, params) -> bool`. Consulted by validate_rule (V2); fast-path
wiring is later work.
"""

from agent.conditions import register

_KNOWN_SORT_KEYS = {"top_row", "top_col"}


@register("recolor_sequential")
def match(patterns: dict, params: dict) -> bool:
    """Fire when `params` describe a valid sequential-recolour spec."""
    p = params or {}
    sort_key = p.get("sort_key")
    source_colors = p.get("source_colors")
    if sort_key is not None and sort_key not in _KNOWN_SORT_KEYS:
        return False
    if source_colors is not None and not isinstance(source_colors, (list, tuple, set)):
        return False
    # A bare recognition signal from the patterns dict is also accepted.
    if sort_key is None and source_colors is None:
        diff = (patterns or {}).get("diff_pattern") or {}
        return diff.get("kind") == "recolor_sequential"
    return True
