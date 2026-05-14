"""
bijective_color_mapping_per_pair -- match tasks where EVERY example pair
satisfies, on its OWN per-pair accumulated changed-cell colour relation,
the bijection precondition iter 333 (``bijective_color_mapping``) pins
globally: within each pair, the accumulated forward
``input_color -> set(output_colors)`` and accumulated inverse
``output_color -> set(input_colors)`` relations (unioned across all
groups of that pair) are both function-shape (every key maps to a
singleton-valued set), independent of any cross-pair accumulation.

Recognition vocabulary axis: per-pair projection of the iter-333
bijection (forward-AND-inverse function-shape) sub-axis. Iter 333
unions the (ic, oc) cross-product across ALL groups across ALL pairs
into a global forward dict and a global inverse dict, then checks both
are function-shape. Iter 334 (``bijective_color_mapping_per_group``)
rebuilds the cross-product PER GROUP and checks both function-shape
gates PER GROUP, independent of any cross-group / cross-pair
consistency. This matcher sits BETWEEN the two on the scope axis: it
rebuilds the cross-product PER PAIR (unioned across that pair's
groups, not across pairs) and checks both function-shape gates PER
PAIR.

Iter 334's "Next gap" note named this candidate:

  > (b) a per-pair-rather-than-global bijection matcher -- iter 333's
  > contract restricted to within-pair-only accumulation (each pair's
  > accumulated forward and inverse dicts function-shape, no cross-
  > pair accumulation); a fresh per-pair scope between the per-group
  > scope of this iter [iter 334] and the global scope of iter 333.
  > The matcher would fire on per-pair-bijective tasks even when
  > cross-pair accumulation breaks global bijection (e.g., pair 0
  > has 0 -> 3, pair 1 has 0 -> 4 -- each pair is bijective, but the
  > global forward is {0: {3, 4}} non-function-shape).

The natural scope chain on the bijection axis is therefore:

  iter 333 (whole-task)  STRICTLY IMPLIES  this matcher (per-pair)
  this matcher (per-pair) STRICTLY IMPLIES  iter 334 (per-group)

Both implications are proper: iter 333 fires only when the union
across all pairs is function-shape, which restricts to function-shape
on each pair's subset; this matcher fires per pair, so any per-pair
violation propagates from a single group's cross-product within that
pair, hence per-pair bijection implies per-group bijection in every
group of every pair.

Why a distinct matcher rather than parameterising iter 333 / 334 with
a scope flag, or co-firing iter 8 AND iter 332 with universal-over-
pairs semantics
------------------------------------------------------------

The matcher contract (docs/RULE_FORMAT.md section 4) is name-keyed:
the rule's stored ``condition.type`` is a single string -- the name of
ONE matcher in CONDITION_REGISTRY -- not a name+params tuple and not
a conjunction expression. A rule whose precondition is "per-pair
forward AND per-pair inverse function-shape" needs a single named
handle to gate on; otherwise the rule would have to redundantly carry
both ``consistent_color_mapping`` (forward, whole-task scope) and
``inverse_consistent_color_mapping`` (inverse, whole-task scope) with
an externally-applied per-pair restriction the schema does not
support. Naming the per-pair bijection cell as a single matcher is
the same posture iter 333 took for the whole-task bijection cell and
iter 334 took for the per-group bijection cell.

Why this matters for ARBOR's intended ruleset
---------------------------------------------

The "per-pair recolour by either direction" rule family -- rules
whose per-pair action can be encoded with EITHER a forward (input ->
output) table OR an inverse (output -> input) table without
ambiguity WITHIN each pair, both per-pair directions being well-
defined. The semantic value lies in *what choice the rule's per-pair
action data is free to make per pair*:

  * Per-pair forward-only (iter 8 with per-pair gate): action must
    carry a per-pair forward table; the per-pair inverse is ambiguous.
  * Per-pair inverse-only (iter 332 with per-pair gate): action
    must carry a per-pair inverse table; the per-pair forward is
    ambiguous.
  * Both per-pair (THIS matcher): per-pair action can use EITHER
    direction within each pair, plus more expressive per-pair
    parameterisations are admissible (e.g., per-pair swap, per-pair
    permutation cycle) because each direction is well-defined.
  * Iter 333 (whole-task bijection): the strict refinement of this
    matcher requiring the bijection to hold ACROSS pairs as well --
    a stronger precondition that pins a single global table valid
    for all pairs.

Anti-unification (CLAUDE.md section 8) would attach a per-pair
bijection-shape generalisation variable to this matcher's fired gate
when the per-pair programs encode possibly DIFFERENT per-pair
forward/inverse tables across pairs (each pair having its own
bijective recolouring map).

Strict refinement / orthogonality summary (universal-over-pairs
semantics, per-pair bijection scope):

  * Iter 333 (``bijective_color_mapping``) -- whole-task bijection.
    STRICTLY IMPLIES this matcher: a whole-task forward function-
    shape means the global forward dict is function-shape; the
    restriction to any single pair's subset of (ic, oc) bindings is
    therefore also function-shape (a subset of a function is a
    function). Symmetrically for inverse. Converse fails on
    cross-pair drift: pair 0 has ic=[0]/oc=[3]; pair 1 has ic=[0]/
    oc=[4]. Each pair has a per-pair bijection (forward {0: {3}},
    inverse {3: {0}} for pair 0; forward {0: {4}}, inverse {4: {0}}
    for pair 1). Global forward {0: {3, 4}} -- NOT function-shape;
    iter 333 REJECTS. THIS matcher FIRES.
  * Iter 334 (``bijective_color_mapping_per_group``) -- per-group
    bijection. STRICTLY IMPLIED BY this matcher: per-pair bijection
    means the per-pair forward and inverse dicts are function-shape;
    any group within that pair contributes (ic, oc) bindings whose
    forward and inverse images are subsets of the per-pair dicts'
    images, hence singleton-valued -- per-group bijection holds in
    every group. Converse fails on intra-pair collapse: a pair with
    two groups ic=[0]/oc=[3] and ic=[1]/oc=[3]. Per-group bijection
    holds in each (|ic| == |oc| == 1 each). Per-pair inverse
    {3: {0, 1}} -- NOT function-shape; THIS matcher REJECTS. Iter
    334 FIRES.
  * Iter 8 (``consistent_color_mapping``) -- whole-task forward
    function-shape (no inverse clause, no per-pair restriction).
    STRICTLY IMPLIED BY iter 333 but INDEPENDENT of this matcher in
    general: iter 8 is whole-task scope; this matcher is per-pair
    scope. The four cells of the {iter 8, this matcher} 2x2 product
    are all realisable: both fire (per-pair bijection with consistent
    global forward, e.g., iter-10 canonical fixture); iter 8 only
    (whole-task forward function-shape on the {forward-collapse-
    within-pair} fixture -- but wait, that fails iter 8 too because
    iter 8 requires forward function-shape globally); the iter-8-
    only cell is the forward-only-no-inverse cell where per-pair
    inverse fails, e.g., pair 0 has ic=[0]/oc=[3], ic=[1]/oc=[3] --
    iter 8 fires (global forward {0: {3}, 1: {3}} function-shape);
    this matcher rejects (per-pair inverse {3: {0, 1}} fails); the
    this-matcher-only cell is the cross-pair-drift fixture above
    (each pair bijective, global forward not function-shape); the
    neither cell is the per-pair forward expansion (pair with
    ic=[0]/oc=[3, 4] -- both reject).
  * Iter 332 (``inverse_consistent_color_mapping``) -- whole-task
    inverse function-shape. INDEPENDENT in general (symmetric
    counterpart of iter 8).
  * Iter 185 (``output_palette_equals_input``) -- whole-grid palette
    equality. INDEPENDENT: bijection scope and palette-relation
    scope are orthogonal axes.
  * Iter 215 (``singleton_recolor_per_group``) -- per-group |ic| ==
    |oc| == 1. STRICTLY IMPLIED BY this matcher (per-pair bijection
    => per-group bijection => set-level per-group singleton).
    Converse fails on the intra-pair collapse fixture above (iter
    215 fires, this matcher rejects).
  * Iter 13 (``identity_transformation``) -- zero change groups per
    pair. STRICT MUTUAL EXCLUSION (this matcher requires every pair
    to have at least one non-empty group to anchor a per-pair
    accumulation).
  * Iter 14 (``input_color_uniform``) -- whole-task |ic_observed|
    == 1. INDEPENDENT.
  * Iter 18 (``output_color_uniform``) -- whole-task |oc_observed|
    == 1. INDEPENDENT.

Mutual-exclusion witness with iter 333 (per-pair bijection AND whole-
task non-bijection):

  * Pair 0 groups: ``ic=[0], oc=[3]``. Per-pair forward {0: {3}},
    inverse {3: {0}} -- function-shape. Per-pair bijection holds.
  * Pair 1 groups: ``ic=[0], oc=[4]``. Per-pair forward {0: {4}},
    inverse {4: {0}} -- function-shape. Per-pair bijection holds.
  * Global forward {0: {3, 4}} -- NOT function-shape; iter 333
    REJECTS. THIS matcher FIRES.

Mutual-exclusion witness with iter 334 (per-group bijection AND per-
pair non-bijection):

  * One pair with two groups: ``ic=[0], oc=[3]`` and ``ic=[1],
    oc=[3]``. Per-group bijection in each (|ic| == |oc| == 1 each).
    Per-pair forward {0: {3}, 1: {3}} -- function-shape. Per-pair
    inverse {3: {0, 1}} -- NOT function-shape; THIS matcher
    REJECTS. Iter 334 FIRES.

Co-fire witness with iter 333 (whole-task bijection):

  * Pair groups: ``ic=[0], oc=[3]`` and ``ic=[1], oc=[4]`` and
    ``ic=[2], oc=[5]`` per pair across all pairs. Per-pair forward
    and inverse are function-shape; global forward and inverse are
    also function-shape (the union is the same bindings). Both
    matchers fire. The iter-10 canonical fixture lands in this cell.

Co-fire witness with iter 334 (per-group bijection):

  * Same iter-10 canonical fixture: every group has |ic| == |oc|
    == 1; per-pair accumulation preserves function-shape; per-group
    bijection holds. Both matchers fire.

Why fail-closed on empty / no-pair / no-group / malformed (same
posture as iter 213 / 214 / 215 / 333 / 334): a missing or zero-
group pair is upstream extractor breakage or identity territory;
a per-pair bijection claim with zero observations in a pair is
meaningless.

Why ``input_colors`` and ``output_colors`` both required non-empty
lists per group (``len >= 1``): same rationale as iter 213 / 214 /
215 / 333 / 334 -- a connected change group has at least one cell;
each cell has both an input and an output colour; a zero-length
per-group colour list is an extractor contract violation, not a
valid empty-set bijection case.

Why strict per-colour validation (bool rejected, range checked):
same strict 0..9 int gate as iter 8 / 14 / 18 / 213 / 214 / 215 /
333 / 334; the recognition layer must reject placeholder sentinels.

Params:
  (none) -- pure per-pair bijection check, universal over pairs.

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis has a non-empty ``groups`` list (identity-territory
    rejection), AND
  - every group is a dict with list-typed ``input_colors`` and
    ``output_colors`` fields of length >= 1, AND
  - every entry of ``input_colors`` and ``output_colors`` is a strict
    int in ``range(10)`` (bool rejected per iter-213 / 214 / 215 /
    333 / 334 strict-type posture), AND
  - for every pair, the per-pair forward cross-product
    ``{ic: set(output_colors) for ic in input_colors}`` accumulated
    across all groups of THAT pair has function-shape (every
    binding's value is a singleton), AND
  - for every pair, the per-pair inverse cross-product
    ``{oc: set(input_colors) for oc in output_colors}`` accumulated
    across all groups of THAT pair has function-shape (every
    binding's value is a singleton).

No companion-touch required: ``input_colors`` / ``output_colors``
(iter 1 / 8) have been emitted from ``_analyze_pair`` since their
respective iters; this iter is a pure matcher addition with no
``agent/active_operators.py`` diff. F8 inert.
"""

from __future__ import annotations

from agent.conditions import register


def _is_strict_color(x) -> bool:
    return (
        isinstance(x, int)
        and not isinstance(x, bool)
        and 0 <= x <= 9
    )


def _is_color_list(x) -> bool:
    """A per-group change-cell colour list must be a non-empty list of
    strict 0..9 ints (mirrors iter 213 / 214 / 215 / 333 / 334 strict-
    type posture; a change group with zero colours on either side is
    upstream breakage)."""
    if not isinstance(x, list) or len(x) < 1:
        return False
    for v in x:
        if not _is_strict_color(v):
            return False
    return True


@register("bijective_color_mapping_per_pair")
def match(patterns: dict, params: dict) -> bool:
    if not isinstance(patterns, dict):
        return False
    pair_analyses = patterns.get("pair_analyses")
    if not isinstance(pair_analyses, list) or not pair_analyses:
        return False

    for analysis in pair_analyses:
        if not isinstance(analysis, dict):
            return False
        groups = analysis.get("groups")
        if not isinstance(groups, list) or not groups:
            return False

        forward: dict = {}
        inverse: dict = {}
        for group in groups:
            if not isinstance(group, dict):
                return False
            input_colors = group.get("input_colors")
            output_colors = group.get("output_colors")
            if not _is_color_list(input_colors):
                return False
            if not _is_color_list(output_colors):
                return False
            for ic in input_colors:
                for oc in output_colors:
                    forward.setdefault(ic, set()).add(oc)
                    inverse.setdefault(oc, set()).add(ic)

        if not forward or not inverse:
            return False
        if not all(len(v) == 1 for v in forward.values()):
            return False
        if not all(len(v) == 1 for v in inverse.values()):
            return False
    return True
