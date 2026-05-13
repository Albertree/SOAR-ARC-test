"""
single_cell_change_per_pair -- match tasks where every example pair has
EXACTLY ONE connected change group AND that group has EXACTLY ONE
changed cell (a point edit).

Recognition vocabulary axis: ``selection-shape`` (cell-count refinement
of group-count). Strict refinement of iter 23's
``single_change_group_per_pair``: adds the requirement that the single
group is a single-cell group, not an arbitrary connected blob.

Why this matters for the schema (the next emission step iter 23 named):

  * The frozen ``coloring`` DSL primitive
    (``procedural_memory/DSL/coloring.py``) takes a literal selection
    (a coord or list of coords). For a single-CELL change, the coord
    is already on disk in the patterns dict: ``_analyze_pair`` emits
    ``top_row`` and ``top_col`` for every group, and for a single-cell
    group those two integers ARE the cell's position (the group's
    bounding box collapses to a 1x1 square). No ``_analyze_pair``
    extension is required to mint a ``coloring`` rule with
    ``args.selection = [(top_row, top_col)]`` -- only this matcher's
    precondition needs to fire. This avoids the
    ``active_operators.py`` edit that the more-general single-blob
    coloring emission would require.
  * Together with ``output_color_uniform`` (iter 18) the rule shape
    "paint a single cell at (r, c) with colour K" has its cell count
    pinned by this matcher, its cell coord readable from
    ``(top_row, top_col)``, and its colour pinned by iter 18. All
    three components of ``coloring(grid, [(r, c)], K)`` are fixed by
    named recognition vocabulary -- the simplest possible non-identity
    coloring rule shape becomes mintable without anti-unification or
    polymorphic args.
  * Together with ``input_dimensions_constant`` (iter 22) the literal
    coord is safe to store: the test input's dimensions match the
    training input's dimensions, so a stored coord like ``(0, 0)`` is
    in-bounds for any test input the rule will be tried on. The iter
    22 docstring explicitly named this as the literal-coord precondition.

Relation to existing matchers:

  * ``single_change_group_per_pair`` (iter 23) -- strict refinement:
    iter 23 requires ``num_groups == 1`` per pair; this matcher
    additionally requires the single group's ``cell_count == 1``.
    Every pair that fires this matcher also fires iter 23, but not
    vice versa (a single 4-cell blob fires iter 23 but not this).
    Not strictly mutually exclusive -- they co-fire on the
    single-cell case.
  * ``identity_transformation`` (iter 13) -- requires every pair's
    ``num_groups == 0``; this matcher requires ``num_groups == 1``
    AND ``cell_count == 1``. STRICTLY mutually exclusive (cardinality
    0 vs cardinality 1).
  * ``output_color_uniform`` (iter 18) -- inspects change-group
    colour content. CAN co-fire when the single cell's
    ``output_colors == [K]`` (which it always does for a single
    cell, since the cell has exactly one output colour). The
    iter-18 + this conjunction names the simplest non-identity
    coloring rule shape's full precondition.
  * ``input_color_uniform`` (iter 19) -- inspects change-group
    input colours. CAN co-fire when the single cell's
    ``input_colors == [C]`` (which it always does for a single
    cell). Names the input-side selection predicate.
  * ``consistent_color_mapping`` (iter 8) -- inspects (in, out)
    colour pairs across all groups. CAN co-fire on single-cell
    pairs (one input colour -> one output colour is trivially a
    1:1 mapping).
  * ``sequential_recoloring`` (iter 10) -- requires the per-pair
    output colours form a contiguous integer range. CAN co-fire at
    N == 1 (a one-element range is trivially contiguous). The two
    matchers are NOT in a refinement relation -- iter 10 may fire
    at N >= 2 where this matcher does not, and this matcher may
    fire at N == 1 with output colours that iter 10 also accepts
    as a one-element contiguous range.
  * ``grid_size_preserved`` / ``grid_size_changed`` /
    ``output_dimensions_constant`` / ``input_dimensions_constant``
    -- dimensional axis, orthogonal to cell-count.

Params:
  (none) -- the matcher is a pure cardinality check on two
  scalar fields. The chosen cell coord (``(top_row, top_col)``) is
  data the rule's ``action.args`` will carry, not a matcher parameter.

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis carries a strict-positive-int ``num_groups``
    (not bool) with value == 1, AND
  - every analysis's ``groups`` is a non-empty list whose first
    element is a dict carrying a strict-positive-int ``cell_count``
    (not bool) with value == 1.

Why strict ``cell_count == 1`` (not ``>= 1``): the matcher names
a SPECIFIC selection-shape -- "exactly one changed cell per pair"
-- not a generic "at least one." A multi-cell single-blob pair is
the next-larger selection territory (handled by a future iter that
extends ``_analyze_pair`` to expose positions, or by an
anti-unification-discovered selection abstraction). Iter-23's
docstring distinguished single-blob from multi-blob as separate
axes; this matcher sits on the single-cell sub-axis of the
single-blob axis.

Why strict bool-subclass rejection: ``num_groups`` and
``cell_count`` are semantically integer counts, not Booleans.
Strict comparison forecloses ``num_groups = True`` /
``cell_count = True`` false positives, mirroring iters 13 / 17 /
18 / 19 / 20 / 22 / 23's strict-type postures and ``validate_rule``
V1's ``isinstance(x, bool)`` rejection on integer fields.

Why fail-closed on missing ``num_groups`` / ``cell_count`` / empty
``groups``: the matcher's contract is ``deterministic and
side-effect-free`` (docs/RULE_FORMAT.md section 4); missing
upstream fields are extractor breakage, not evidence the
precondition holds. ``ExtractPatternOperator._analyze_pair`` has
emitted ``num_groups`` since iter 1 and ``cell_count`` per group
since iter 1, so any current patterns dict will carry both; the
fail-closed posture preserves backwards compatibility with any
cached or partially-constructed patterns dict the recognizer may
be asked to evaluate.

Why a strict layered check on iter 23's matcher rather than a
direct call to it: matchers are independent predicates in the
registry. Composing them at use-site (via ``recognized_conditions``
and a conjunction of names in a rule's ``condition.type`` -- the
future composite-precondition step) is the canonical pattern;
inlining iter 23's check here would couple two registry entries
in a non-introspectable way. The matcher implements the conjunction
explicitly so that ``CONDITION_REGISTRY["single_cell_change_per_pair"]``
is a single self-contained predicate, the same shape as every
other matcher.
"""

from __future__ import annotations

from agent.conditions import register


@register("single_cell_change_per_pair")
def match(patterns: dict, params: dict) -> bool:
    if not isinstance(patterns, dict):
        return False
    pair_analyses = patterns.get("pair_analyses")
    if not isinstance(pair_analyses, list) or not pair_analyses:
        return False

    for analysis in pair_analyses:
        if not isinstance(analysis, dict):
            return False
        n = analysis.get("num_groups")
        if not isinstance(n, int) or isinstance(n, bool):
            return False
        if n != 1:
            return False
        groups = analysis.get("groups")
        if not isinstance(groups, list) or len(groups) != 1:
            return False
        group = groups[0]
        if not isinstance(group, dict):
            return False
        cell_count = group.get("cell_count")
        if not isinstance(cell_count, int) or isinstance(cell_count, bool):
            return False
        if cell_count != 1:
            return False
    return True
