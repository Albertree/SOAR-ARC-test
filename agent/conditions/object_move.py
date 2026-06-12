"""
object_move — the *umbrella* recognition matcher for the lifted place_object
family (R3, BACKLOG_LOOP §3 / CLAUDE.md §8).

Where ``object_constant_target`` and ``object_constant_offset`` each recognise
*one* reading of the move DIFF, this matcher recognises the **family** that
anti-unification lifts them into: a single foreground object moved (color/shape/
size preserved) whose target is fixed by *some* cross-pair COMM reading — the
absolute target *or* the relative displacement. It is the recognition counterpart
of the abstract ``place_object`` rule produced by ``program/anti_unification.unify``
(action.args.target.reading = a ``?vN`` variable ranging over those readings).

The variable is *resolved* at predict time from the actual task's comparison
results (constant_target if present, else constant_offset) — BACKLOG_LOOP §2.5-2b:
the abstract rule has a hole, and *which* reading fills it is decided from COMM/
DIFF, not invented (P3/P4). This matcher therefore fires when either reading is
constant, i.e. the lifted family applies.

Reads the `object_move` signal surfaced by ExtractPatternOperator (computed by
agent/dsl_expr/selection.analyze_object_move).
"""

from agent.conditions import register


@register("object_move")
def object_move(patterns: dict, params: dict | None = None) -> bool:
    """True iff every example is a single object moved (color+shape+size kept)
    whose target is fixed by *some* constant COMM reading — the lifted family.

    `params.min_evidence` (default 2) guards against firing on a single pair.
    """
    if not isinstance(patterns, dict):
        return False
    params = params or {}
    min_evidence = params.get("min_evidence", 2)

    move = patterns.get("object_move")
    if not isinstance(move, dict):
        return False
    if move.get("constant_target") is None and move.get("constant_offset") is None:
        return False
    if not (move.get("single_object_all")
            and move.get("color_preserved_all")
            and move.get("shape_preserved_all")
            and move.get("size_preserved_all")):
        return False
    return len(move.get("per_pair") or []) >= min_evidence
