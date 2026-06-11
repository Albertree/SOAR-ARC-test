"""
condition matcher: constant_output.

Recognizes the easy000a mechanism (slice doc §3): every example's output grid
(role==G1) is *identical*, so the test output is that one common grid —
regardless of the input. The recognition is value-agnostic: it fires on the
*shape* of the comparison evidence (all Inter-Grid role==G1 comparisons COMM),
not on any particular colour or coordinate, so it never hard-codes a task's
answer (slice doc §9 guardrail).

The transformation half is a `make_grid` + `coloring` composition that
re-creates the common output; this matcher is only the recognition half, and
wiring it into the predict/submit path is a later step.

Matcher contract (docs/RULE_FORMAT.md §4): deterministic, side-effect-free,
`match(patterns, params) -> bool`. `patterns["inter_output"]` is produced by
ExtractPatternOperator from the comparison receipts (P4: the verdict is a
comparison result, never a re-read of the grids).
"""

from agent.conditions import register


@register("constant_output")
def match(patterns: dict, params: dict) -> bool:
    """
    Fire when there is at least one Inter-Grid (role==G1) comparison and every
    one of them is COMM — i.e. all example outputs are the same grid.
    """
    info = (patterns or {}).get("inter_output") or {}
    return bool(info.get("count", 0) >= 1 and info.get("all_comm") is True)
