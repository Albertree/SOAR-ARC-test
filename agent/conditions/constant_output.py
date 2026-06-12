"""
constant_output — R0's recognition matcher (BACKLOG_LOOP.md R0).

Fires when every example output grid (the role==G1 grids) is identical. This is
the symbolic COMM relation across all example outputs: "all G1 are the same."
When it holds, the answer for the test pair is value-agnostic — it is simply
that common output grid (the COMM-copy prediction path R0 builds toward), with
no per-task literal or hand-coded detector involved.

This recognizes the constant-output family value-agnostically: easy0001 (a 2 at
(5,5) regardless of input), easy000a/000b, easy0005/0009/0013 — all are "every
training output is the same grid." A single matcher covers them all; the design
intent (P2 of the 7 principles, arbor-flow prose easy000a) is that one module
handles a whole family rather than one detector per task.

Reads the `output_invariant` signal surfaced by ExtractPatternOperator:
    patterns["output_invariant"] = {
        "all_equal":      bool,          # are all example outputs identical?
        "evidence_count": int,           # how many example outputs were compared
        "common_output":  grid | None,   # the shared grid when all_equal
    }
"""

from agent.conditions import register


@register("constant_output")
def constant_output(patterns: dict, params: dict | None = None) -> bool:
    """True iff all example outputs are identical and there is enough evidence.

    `params.min_evidence` (default 2) guards against firing on a single example —
    one pair is not enough to claim "the output is always this grid."
    """
    if not isinstance(patterns, dict):
        return False
    params = params or {}
    min_evidence = params.get("min_evidence", 2)

    invariant = patterns.get("output_invariant")
    if not isinstance(invariant, dict):
        return False
    if not invariant.get("all_equal"):
        return False
    return invariant.get("evidence_count", 0) >= min_evidence
