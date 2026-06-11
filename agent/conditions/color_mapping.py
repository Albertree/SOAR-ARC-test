"""
condition matcher: color_mapping.

Recognizes that a *global per-color substitution* explains the observed
transformation — i.e. every cell of source colour s becomes colour
`mapping[s]`, independent of position. This is the recognition half of the
legacy `color_mapping` action (the transformation itself is a composition of
`coloring` calls over the cells of each source colour).

Matcher contract (docs/RULE_FORMAT.md §4): deterministic, side-effect-free,
`match(patterns, params) -> bool`. It is consulted by validate_rule (V2) so a
`color_mapping` rule has a registered condition.type; wiring it into the
fast-path proposer is later work.
"""

from agent.conditions import register


@register("color_mapping")
def match(patterns: dict, params: dict) -> bool:
    """
    Fire when `params` carries a well-formed colour map and the observed
    patterns (if any) do not contradict it.

    A well-formed map is a non-empty dict whose keys and values are colour
    indices (0-9). With no params we cannot assert applicability, so we look
    for a `color_mapping` signal in `patterns` instead.
    """
    mapping = (params or {}).get("mapping")
    if isinstance(mapping, dict) and mapping:
        return all(_is_color(k) and _is_color(v) for k, v in mapping.items())

    # No explicit map: fall back to a recognition signal in the patterns dict.
    diff = (patterns or {}).get("diff_pattern") or {}
    return diff.get("kind") == "color_mapping"


def _is_color(x) -> bool:
    try:
        return 0 <= int(x) <= 9
    except (TypeError, ValueError):
        return False
