"""
self_tile — the *applicability* matcher for the fractal self-tiling action
(BACKLOG_LOOP.md R6 "training escalation": a general mechanism applied to real
ARC-AGI-2 training tasks, not a per-task detector).

A family of ARC tasks expands a `H x W` grid into a `H*H x W*W` grid by *self
reference*: the output is laid out as `H x W` macro-blocks, and macro-block
`(r, c)` is a **copy of the whole input** when `input[r][c]` is a "live" cell, or
a block of the *empty* colour `e` when `input[r][c] == e`. (007bbfb7, 5b6cbef5 —
the canonical "fractal" tasks.) None of the existing families can express this:

  * `constant_output` needs identical example outputs;
  * `color_map` / `recolor_extreme` / `object_keyed_recolor` keep the grid shape;
  * `single_object_move_*` moves one object within a same-shape grid;
  * `integer_scale` enlarges by a constant factor but paints each cell as a
    *solid* block — a self-tile's blocks are *copies of the input*, not solids,
    so `integer_scale` declines on this family (its `out[R][C] == in[R//kh][C//kw]`
    check fails on every live block).

This is the first family whose output dimensions are *derived from the input
itself* (the factor is the grid's own `(H, W)`, an argument expression over the
test grid, §2.5-1) and whose block *content* is a copy of the input — a
self-referential composition new to the system, distinct from the constant-factor
enlargement of `integer_scale`.

The empty colour `e` is a comparison result (P3/P4), not a stored literal: for
each pair it is the colour present in the input for which every macro-block obeys
the self-tile law (`input[r][c]==e ⇒ block is all e`, else `block == input`).
When one such `e` is the *same* across every example pair (a COMM over the pairs)
the task is a self-tile; that single colour is re-derived from each task's own
examples at apply time, so one value-agnostic `self_tile` rule covers the whole
family rather than one detector per task (§2.5-3).

This is recognition-vocabulary growth (P5), the dimension CLAUDE.md §6.3
blesses; it introduces no new way of *doing* a transformation (the tiling is the
frozen `make_grid` canvas painted by the frozen `coloring` per live block).

Reads the `self_tile` signal `ExtractPatternOperator` surfaces:

    patterns["self_tile"] = {
        "consistent":     bool,      # one empty colour `e` makes every pair a
                                     #   H*H × W*W masked self-tile
        "empty":          int|None,  # the derived empty colour (None if not)
        "evidence_count": int,
    }

When the pairs disagree on the empty colour, are not `H*H × W*W`, or are not a
masked self-tile, the producer leaves `consistent` False, so this matcher returns
False and cannot misfire on the recolor / move / constant-output / integer-scale
families — it stays dormant there.
"""

from agent.conditions import register


@register("self_tile")
def self_tile(patterns: dict, params: dict | None = None) -> bool:
    """True iff every example pair is the same fractal self-tile of its input:
    an `H*H × W*W` layout of `H x W` macro-blocks where block `(r, c)` copies the
    whole input when `input[r][c]` is live, or is the empty colour `e` otherwise,
    for one `e` consistent across every pair.

    `params.min_evidence` (default 2) guards against firing on a single example —
    one pair cannot establish "the empty colour is always this" as a rule.
    """
    if not isinstance(patterns, dict):
        return False
    params = params or {}
    min_evidence = params.get("min_evidence", 2)

    sig = patterns.get("self_tile")
    if not isinstance(sig, dict):
        return False
    if sig.get("evidence_count", 0) < min_evidence:
        return False
    return bool(sig.get("consistent") and sig.get("empty") is not None)
