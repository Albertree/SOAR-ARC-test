"""
output_dimensions_square -- match tasks where every example pair's output
grid is a SQUARE (height == width).

Symmetric dual of iter-182's ``input_dimensions_square``. The per-pair
shape-regularity axis is bipartite: the property "grid is N x N for some
N" can hold on the INPUT side, on the OUTPUT side, or both. Iter 182
named the input side; this iter (iter 183) names the output side and
closes the axis on the matcher-only diff. The two preconditions compose:
``input_dimensions_square`` AND ``output_dimensions_square`` together
declare "every pair has a square input AND a square output" -- the
shape precondition for any rotational / reflectional / dihedral
abstract rule whose action is well-typed only on a square output.
Naming each half independently keeps a rule's stored
``condition.type`` capable of declaring exactly the half it relies on
without overreaching.

Recognition vocabulary axis: ``per-pair shape regularity`` (output
side). None of the existing dimensional matchers names this property:

  * Iter 1 (``grid_size_preserved``) and iter 17 (``grid_size_changed``)
    inspect the relation between the input's shape and the output's
    shape (whether they match per pair), not whether either is square.
  * Iter 20 (``output_dimensions_constant``) inspects cross-pair
    constancy of the output (H, W) tuple; orthogonal to whether
    H == W.
  * Iter 22 (``input_dimensions_constant``) is the input-side
    counterpart; orthogonal to whether the output axis is square.
  * Iter 33 (``output_dimensions_multiple_of_input``) inspects the
    output:input scale ratio; orthogonal to whether either axis is
    square. (A non-square 2x3 input scaled by (3, 3) -> 6x9 output
    fires iter 33 but neither input nor output is square; a square
    2x2 -> 4x4 fires iter 33 AND ``input_dimensions_square`` AND
    this matcher.)
  * Iter 182 (``input_dimensions_square``) is the input-side dual of
    this matcher; orthogonal to whether the output is square. (A
    tile-style 3x3 -> 5x4 task fires iter 182's input matcher but
    NOT this one; a 2x3 -> 4x4 task fires this matcher but NOT iter
    182's.)
  * The cell-, group-, position-, and colour-axis matchers are all
    orthogonal to grid shape.

So square-ness on the per-pair output axis is a strictly new axis whose
membership is independent of every existing matcher's gate.

Why this matters for the schema:

  * The frozen ``coloring`` DSL primitive
    (``procedural_memory/DSL/coloring.py``) is dimension-agnostic, so
    a square-output precondition is not itself a coloring-args
    constraint. But a future bottom-up-discovered composition that
    realises a transpose, diagonal reflection, or any other dihedral
    operation on the OUTPUT canvas (a sequence of
    ``coloring(grid, (r, c), grid[c][r])`` over the full output coord
    set, say) is only well-typed when output H == W. Likewise, an
    abstract rule whose ``action`` is a ``make_grid(N, N, color)`` +
    ``coloring`` composition that emits a square canvas declares its
    output-side shape precondition through this matcher's name.
    Recognition vocabulary ahead of emission, the iter 1/8/10/13/17/
    18/19/20/22/23/24/26/28/30/32/33/35/37/38/.../182 pattern.
  * Per-attempt ``fired_conditions`` (written to
    ``episodic_memory/<task>/attempt_NNN/metadata.json`` since iter
    12) gains one more named axis the instrumentation surfaces
    without needing a ``translate_to_schema`` branch to consume it
    yet.

Relation to existing matchers (mutual exclusion / co-fire table):

  * ``grid_size_preserved`` (iter 1) -- per-pair size_match True
    (in_dim == out_dim) is orthogonal to whether the output dims are
    square. CAN co-fire (every pair 3x3 -> 3x3), can fire alone
    (3x4 -> 3x4 -- preserved, not square), can fire orthogonally
    (3x4 -> 5x5 -- not preserved per pair but every output is
    square).
  * ``grid_size_changed`` (iter 17) -- analogous to above; the
    output-square axis is orthogonal to the per-pair change axis.
  * ``output_dimensions_constant`` (iter 20) -- cross-pair constancy
    of (H_out, W_out). CAN co-fire (every pair output 3x3), can fire
    alone (every pair output 3x4 -- constant, not square), can fire
    orthogonally (mixed 2x2 / 3x3 / 4x4 outputs -- all square but
    not constant across pairs).
  * ``input_dimensions_constant`` (iter 22) -- input-side constancy;
    orthogonal to whether OUTPUT is square.
  * ``output_dimensions_multiple_of_input`` (iter 33) -- relational
    scale-ratio constancy; orthogonal to whether either axis is
    square (the scale axis cares about the ratio, not the shape).
  * ``input_dimensions_square`` (iter 182) -- input-side dual;
    orthogonal to whether the output is square. CAN co-fire (every
    pair 3x3 -> 4x4 has square inputs AND square outputs), can fire
    alone (every pair 3x4 -> 5x5 has non-square inputs but square
    outputs), can fire orthogonally (every pair 3x3 -> 5x4 has
    square inputs but non-square outputs).
  * The cell-/group-/position-/colour-axis matchers -- all
    orthogonal to grid shape.

So no co-fire is forced, no co-fire is forbidden -- this is a
strictly new axis whose membership is independent of every existing
matcher's gate.

Params:
  (none) -- the matcher's contract is "every pair's output is N x N
  for some pair-specific N". The matcher does NOT require a single N
  across pairs (that is iter 20's territory: ``output_dimensions_
  constant`` AND ``output_dimensions_square`` together pin (H, W) to
  a single square value across the entire training set, but those
  are two named preconditions composed by ``recognized_conditions``,
  not one matcher overreaching).

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis has an ``output_height`` value that is a strict
    positive integer (not bool, ``>= 1``), AND
  - every analysis has an ``output_width`` value with the same
    contract, AND
  - for every analysis: ``output_height == output_width``.

Why per-pair ``output_height`` / ``output_width`` rather than a
derived top-level flag: same rationale as iters 17 / 20 / 22 / 33 /
182 -- matchers should not piggyback on derived top-level flags;
reading the per-pair scalar fields keeps the recognition layer's
contract on the shape ``_analyze_pair`` emits, not on a summary the
slow path may forget to compute. (``_analyze_pair`` has emitted
``output_height`` and ``output_width`` since iter 19, the same point
at which the input-side scalars landed -- so this iter is matcher-
only addition on a new axis using existing patterns-dict fields.)

Why strict positive-int (not bool, ``>= 1``): a missing or
non-positive output dimension is upstream extractor breakage, not
evidence the output is square. Strict comparison forecloses
``output_height = True`` (Python bool-is-int subclass) and
``output_height = 0`` (degenerate empty grid) false positives,
mirroring iters 13 / 17 / 18 / 19 / 20 / 22 / 33 / 182. The bool-
rejection is the same posture as ``agent/memory.py:validate_rule``
on integer fields (V1 explicitly rejects ``isinstance(x, bool)``).

Why fail-closed on a non-positive or missing dim: a single missing
or bool-typed dim is upstream extractor breakage. The matcher returns
False rather than raising -- consistent with the matcher contract
(deterministic, side-effect-free) and with how every other
dimensional matcher handles upstream breakage.

No ``agent/active_operators.py`` change this iter: the per-pair
``output_height`` / ``output_width`` fields have been emitted by
``_analyze_pair`` since iter 19. This iter is matcher-only addition
on a new axis using existing patterns-dict fields. The companion-
touch question under F8 is therefore inert -- no change to
``agent/active_operators.py`` at all.
"""

from __future__ import annotations

from agent.conditions import register


def _is_strict_positive_int(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool) and x >= 1


@register("output_dimensions_square")
def match(patterns: dict, params: dict) -> bool:
    if not isinstance(patterns, dict):
        return False
    pair_analyses = patterns.get("pair_analyses")
    if not isinstance(pair_analyses, list) or not pair_analyses:
        return False

    for analysis in pair_analyses:
        if not isinstance(analysis, dict):
            return False
        oh = analysis.get("output_height")
        ow = analysis.get("output_width")
        if not _is_strict_positive_int(oh):
            return False
        if not _is_strict_positive_int(ow):
            return False
        if oh != ow:
            return False
    return True
