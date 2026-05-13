"""
input_dimensions_square -- match tasks where every example pair's input
grid is a SQUARE (height == width).

Recognition vocabulary axis: ``per-pair shape regularity`` -- the
intrinsic geometric property "input grid is N x N for some N". None of
the existing dimensional matchers names this property:

  * Iter 1 (``grid_size_preserved``) and iter 17 (``grid_size_changed``)
    inspect the relation between the input's shape and the output's
    shape (whether they match per pair), not whether either is square.
  * Iter 20 (``output_dimensions_constant``) and iter 22
    (``input_dimensions_constant``) inspect cross-pair constancy of the
    (H, W) tuple; orthogonal to whether H == W.
  * Iter 33 (``output_dimensions_multiple_of_input``) inspects the
    output:input scale ratio; orthogonal to whether either axis is
    square. (A non-square 2x3 input scaled by (3, 3) -> 6x9 output
    fires iter 33 but neither input nor output is square; a square
    2x2 -> 4x4 fires iter 33 AND this matcher.)
  * The cell-, group-, position-, and colour-axis matchers are all
    orthogonal to grid shape.

So square-ness on the per-pair input axis is a NEW axis. Two new
axiomatic slots in the recognition vocabulary live alongside this:
``input_dimensions_square`` (this iter) and a future
``output_dimensions_square`` (deferred -- smallest-step iter at a
time). Both name foundational shape-regularity preconditions for any
rule whose action is gated on rotational / reflectional symmetry
(transpose, flip-along-diagonal, dihedral operations -- all of which
require a square grid to be well-defined).

Why this matters for the schema:

  * The frozen ``coloring`` DSL primitive
    (``procedural_memory/DSL/coloring.py``) is dimension-agnostic, so
    a square-input precondition is not itself a coloring-args
    constraint. But a future bottom-up-discovered composition that
    realises a transpose or diagonal reflection (a sequence of
    ``coloring(grid, (r, c), grid[c][r])`` over the full coord set,
    for example) is only well-typed when input H == W. Naming the
    precondition makes that composition's eventual abstract rule
    representable: ``condition.type = "input_dimensions_square"`` is
    the recognition handle the rule's stored precondition would
    declare. Recognition vocabulary ahead of emission, the iter
    1/8/10/13/17/18/19/20/22/23/24/26/28/30/32/33/35/37 pattern.
  * Per-attempt ``fired_conditions`` (written to
    ``episodic_memory/<task>/attempt_NNN/metadata.json`` since iter
    12) gains one more named axis the instrumentation surfaces
    without needing a ``translate_to_schema`` branch to consume it
    yet. The two new positive signals iter 11 made directly visible
    are the live-applier output (already wired into
    ``last_solve_info``) and the same dict serialized to disk.

Relation to existing matchers (mutual exclusion / co-fire table):

  * ``grid_size_preserved`` (iter 1) -- per-pair size_match True
    (in_dim == out_dim) is orthogonal to whether the dims are
    square. CAN co-fire (every pair 3x3 -> 3x3), can fire alone
    (3x4 -> 3x4 -- preserved, not square), can fire orthogonally
    (3x3 -> 9x9 -- square inputs, not preserved per pair).
  * ``grid_size_changed`` (iter 17) -- analogous to above; the
    square axis is orthogonal to the per-pair change axis.
  * ``input_dimensions_constant`` (iter 22) -- cross-pair constancy
    of (H_in, W_in). CAN co-fire (every pair 3x3 input), can fire
    alone (every pair 3x4 input -- constant, not square), can fire
    orthogonally (mixed 2x2 / 3x3 / 4x4 inputs -- all square but
    not constant across pairs).
  * ``output_dimensions_constant`` (iter 20) -- output-side
    constancy; orthogonal to whether INPUT is square.
  * ``output_dimensions_multiple_of_input`` (iter 33) -- relational
    scale-ratio constancy; orthogonal to whether either axis is
    square (the scale axis cares about the ratio, not the shape).
  * The cell-/group-/position-/colour-axis matchers -- all
    orthogonal to grid shape.

So no co-fire is forced, no co-fire is forbidden -- this is a
strictly new axis whose membership is independent of every existing
matcher's gate.

Params:
  (none) -- the matcher's contract is "every pair's input is N x N
  for some pair-specific N". The matcher does NOT require a single N
  across pairs (that is iter 22's territory: ``input_dimensions_
  constant`` AND ``input_dimensions_square`` together pin (H, W) to a
  single square value across the entire training set, but those are
  two named preconditions composed by ``recognized_conditions``, not
  one matcher overreaching).

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis has an ``input_height`` value that is a strict
    positive integer (not bool, ``>= 1``), AND
  - every analysis has an ``input_width`` value with the same
    contract, AND
  - for every analysis: ``input_height == input_width``.

Why per-pair ``input_height`` / ``input_width`` rather than a derived
top-level flag: same rationale as iters 17 / 20 / 22 / 33 -- matchers
should not piggyback on derived top-level flags; reading the per-pair
scalar fields keeps the recognition layer's contract on the shape
``_analyze_pair`` emits, not on a summary the slow path may forget to
compute.

Why strict positive-int (not bool, ``>= 1``): a missing or
non-positive input dimension is upstream extractor breakage, not
evidence the input is square. Strict comparison forecloses
``input_height = True`` (Python bool-is-int subclass) and
``input_height = 0`` (degenerate empty grid) false positives,
mirroring iters 13 / 17 / 18 / 19 / 20 / 22 / 33. The bool-rejection
is the same posture as ``agent/memory.py:validate_rule`` on integer
fields (V1 explicitly rejects ``isinstance(x, bool)``).

Why fail-closed on a non-positive or missing dim: a single missing
or bool-typed dim is upstream extractor breakage. The matcher returns
False rather than raising -- consistent with the matcher contract
(deterministic, side-effect-free) and with how every other
dimensional matcher handles upstream breakage.

No ``agent/active_operators.py`` change this iter: the per-pair
``input_height`` / ``input_width`` fields have been emitted by
``_analyze_pair`` since iter 19. This iter is matcher-only addition
on a new axis using existing patterns-dict fields. The companion-
touch question under F8 is therefore inert -- no change to
``agent/active_operators.py`` at all.
"""

from __future__ import annotations

from agent.conditions import register


def _is_strict_positive_int(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool) and x >= 1


@register("input_dimensions_square")
def match(patterns: dict, params: dict) -> bool:
    if not isinstance(patterns, dict):
        return False
    pair_analyses = patterns.get("pair_analyses")
    if not isinstance(pair_analyses, list) or not pair_analyses:
        return False

    for analysis in pair_analyses:
        if not isinstance(analysis, dict):
            return False
        ih = analysis.get("input_height")
        iw = analysis.get("input_width")
        if not _is_strict_positive_int(ih):
            return False
        if not _is_strict_positive_int(iw):
            return False
        if ih != iw:
            return False
    return True
