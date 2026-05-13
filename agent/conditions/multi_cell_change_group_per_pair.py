"""
multi_cell_change_group_per_pair -- match tasks where every example pair
has EXACTLY ONE connected change group AND that single group has STRICTLY
MORE THAN ONE changed cell (i.e. a connected blob of 2+ cells).

Recognition vocabulary axis: ``selection-shape`` (cell-count sub-axis of
group-count). Strict disjoint PARTNER of iter 24's
``single_cell_change_per_pair`` -- together the two matchers partition
iter 23's ``single_change_group_per_pair`` on the cell-count axis:

  * ``num_groups == 1`` AND ``cell_count == 1``  -> iter 24
    (``single_cell_change_per_pair``)
  * ``num_groups == 1`` AND ``cell_count >= 2``  -> THIS iter
    (``multi_cell_change_group_per_pair``)

Every patterns dict that fires THIS matcher also fires iter 23, but no
patterns dict fires BOTH this matcher and iter 24 (strict mutual
exclusion on ``cell_count == 1`` vs ``cell_count >= 2``).

Why this matters for the schema (the next emission step iter 25 named):

  * Iter 25's "Next gap" log explicitly named the multi-cell single-blob
    coloring emission as Option 2 -- gated on
    ``single_change_group_per_pair`` (iter 23, num_groups == 1) +
    ``output_color_uniform`` (iter 18) + ``input_dimensions_constant``
    (iter 22) + ``grid_size_preserved`` (iter 1), painting every cell of
    the blob with K. THIS matcher is the natural strict refinement of
    iter 23 that distinguishes the multi-cell case from the iter-25-
    already-handled single-cell case, so a future emission iter can gate
    the multi-cell branch on THIS matcher (rather than iter 23 + an
    explicit NOT of iter 24, which would not be expressible in a single
    ``condition.type`` string).
  * The action shape on that future branch is
    ``coloring(grid, [(r1,c1), (r2,c2), ..., (rN,cN)], K)`` where the
    coord LIST is the blob's full positions. Iter 25 already proved the
    selection-arg-as-literal-coord-list shape on the cardinality-1 case;
    extending it to cardinality N requires ``_analyze_pair`` to expose
    each group's full ``positions`` list (currently only ``top_row`` /
    ``top_col`` are emitted). That ``active_operators.py`` extension is
    deferred to the emission iter; THIS iter is recognition vocabulary
    only, using the already-emitted ``cell_count`` scalar.
  * Together with ``output_color_uniform`` (iter 18) the rule shape
    "paint every cell of a single blob with colour K" has both its
    selection cardinality range (multi-cell) and its colour pinned by
    named recognition vocabulary. The blob's per-cell coords still need
    the ``_analyze_pair`` ``positions`` extension or an
    anti-unification-discovered selection abstraction; the
    cardinality-range side is now named.

Relation to existing matchers:

  * ``single_change_group_per_pair`` (iter 23) -- strict refinement:
    iter 23 requires ``num_groups == 1`` per pair; this matcher
    additionally requires the single group's ``cell_count >= 2``.
    Every patterns dict firing this matcher also fires iter 23, but not
    the converse (a single 1-cell group fires iter 23 but not this --
    that case is iter 24's territory).
  * ``single_cell_change_per_pair`` (iter 24) -- STRICTLY mutually
    exclusive: iter 24 requires ``cell_count == 1``; this matcher
    requires ``cell_count >= 2``. The two together partition iter 23's
    territory on the cell-count axis with no overlap. Every multi-cell
    single-blob patterns dict fires this matcher and NOT iter 24; every
    single-cell single-group patterns dict fires iter 24 and NOT this.
  * ``identity_transformation`` (iter 13) -- requires every pair's
    ``num_groups == 0``; this matcher requires ``num_groups == 1``
    AND ``cell_count >= 2``. STRICTLY mutually exclusive (cardinality 0
    vs cardinality >= 2).
  * ``output_color_uniform`` (iter 18) -- inspects change-group
    output colour content. CAN co-fire when the multi-cell blob's
    ``output_colors == [K]`` (a single-colour repaint of the blob).
    The iter-18 + this conjunction names the "paint a single blob with
    K" rule shape's full recognition precondition modulo the
    coord-list emission gap.
  * ``input_color_uniform`` (iter 19) -- inspects change-group
    input colours. CAN co-fire when the blob's
    ``input_colors == [C]`` (a single-colour blob).
  * ``consistent_color_mapping`` (iter 8) -- inspects (in, out)
    colour pairs across all groups. CAN co-fire on multi-cell single-
    blob pairs (one input colour -> one output colour is trivially a
    1:1 mapping when both colour sets are size-1).
  * ``sequential_recoloring`` (iter 10) -- requires the per-pair
    output colours form a contiguous integer range across MULTIPLE
    groups; this matcher requires exactly ONE group per pair. They CAN
    co-fire only at N == 1 (a one-element contiguous range), but iter
    10's interesting territory is N >= 2 across groups, so co-firing
    is incidental.
  * ``grid_size_preserved`` / ``grid_size_changed`` /
    ``output_dimensions_constant`` / ``input_dimensions_constant``
    -- dimensional axis, orthogonal to cell-count.

Params:
  (none) -- the matcher is a pure cardinality range check on two
  scalar fields. The chosen selection (the multi-cell blob's full
  coord list) is data the rule's ``action.args`` will carry once
  ``_analyze_pair`` is extended to expose positions, not a matcher
  parameter.

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis carries a strict-positive-int ``num_groups``
    (not bool) with value == 1, AND
  - every analysis's ``groups`` is a non-empty list whose first
    element is a dict carrying a strict-positive-int ``cell_count``
    (not bool) with value >= 2.

Why strict ``cell_count >= 2`` (not ``> 1`` open-ended): the matcher
names a SPECIFIC selection-shape sub-axis -- "exactly one connected
group of two-or-more cells per pair" -- as the strict disjoint
partner of iter 24's "exactly one connected group of exactly one
cell." Strict-positive-int (not bool) on ``cell_count`` mirrors
iter 24's strict-type posture; the lower bound 2 (not 1) is what
makes this matcher disjoint from iter 24.

Why strict bool-subclass rejection: ``num_groups`` and
``cell_count`` are semantically integer counts, not Booleans.
Strict comparison forecloses ``num_groups = True`` /
``cell_count = True`` false positives, mirroring iters 13 / 17 /
18 / 19 / 20 / 22 / 23 / 24's strict-type postures and
``validate_rule`` V1's ``isinstance(x, bool)`` rejection on
integer fields.

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

Why a self-contained predicate rather than a refinement-by-call of
iter 23 + iter 24's negation: matchers are independent predicates
in the registry (docs/RULE_FORMAT.md section 4). Composing them at
use-site (via ``recognized_conditions`` and a conjunction of names
in a future composite-precondition step) is the canonical pattern;
inlining iter 23's check OR iter 24's negation here would couple
registry entries in a non-introspectable way. The matcher
implements its cardinality range check explicitly so that
``CONDITION_REGISTRY["multi_cell_change_group_per_pair"]`` is a
single self-contained predicate, the same shape as every other
matcher.
"""

from __future__ import annotations

from agent.conditions import register


@register("multi_cell_change_group_per_pair")
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
        if cell_count < 2:
            return False
    return True
