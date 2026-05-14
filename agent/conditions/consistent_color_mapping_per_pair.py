"""
consistent_color_mapping_per_pair -- match tasks where EVERY example pair
satisfies, on its OWN per-pair accumulated changed-cell forward colour
relation (unioned across all groups of that pair), the function-shape
gate iter 8 (``consistent_color_mapping``) pins globally: within each
pair, the accumulated forward ``input_color -> set(output_colors)``
relation has function-shape (every key maps to a singleton-valued set),
independent of any cross-pair accumulation.

Recognition vocabulary axis: per-pair projection of the iter-8 forward
function-shape sub-axis. Iter 8 unions the (ic, oc) cross-product across
ALL groups across ALL pairs into a global forward dict and checks it is
function-shape. Iter 213 (``consistent_color_mapping_per_group``)
rebuilds the cross-product PER GROUP and checks function-shape PER
GROUP, independent of any cross-group / cross-pair consistency. This
matcher sits BETWEEN the two on the scope axis: it rebuilds the cross-
product PER PAIR (unioned across that pair's groups, not across pairs)
and checks the function-shape gate PER PAIR.

Iter 335's "Next gap" note named this candidate:

  > A second candidate is the symmetric per-pair forward-only matcher
  > -- iter 8's whole-task forward function-shape projected onto the
  > per-pair scope (each pair's accumulated forward dict is function-
  > shape, without inverse clause); the per-pair analogue of iter 213
  > (per-group forward) and the strict relaxation of [iter 335] by
  > dropping the per-pair inverse clause.

The natural scope chain on the forward axis is therefore:

  iter 8 (whole-task)     STRICTLY IMPLIES  this matcher (per-pair)
  this matcher (per-pair) STRICTLY IMPLIES  iter 213 (per-group)

Both implications are proper: iter 8 fires only when the union across
all pairs is function-shape, which restricts to function-shape on each
pair's subset (a subset of a function is a function); this matcher
fires per pair, so any per-pair violation propagates from a single
group's cross-product within that pair, hence per-pair forward
function-shape implies per-group forward function-shape in every group
of every pair.

The natural strict-relaxation chain on the forward/bijection axis is:

  iter 333 (whole-task forward AND inverse)
        STRICTLY IMPLIES  iter 8 (whole-task forward) AND iter 332 (whole-task inverse)
  iter 8 (whole-task forward)
        STRICTLY IMPLIES  this matcher (per-pair forward)
  iter 335 (per-pair forward AND inverse)
        STRICTLY IMPLIES  this matcher (per-pair forward) AND
                          [the symmetric unnamed per-pair inverse-only matcher]
  this matcher (per-pair forward)
        STRICTLY IMPLIES  iter 213 (per-group forward)

Why a distinct matcher rather than parameterising iter 8 / 213 with a
scope flag, or co-firing iter 8 with universal-over-pairs semantics
------------------------------------------------------------

The matcher contract (docs/RULE_FORMAT.md section 4) is name-keyed:
the rule's stored ``condition.type`` is a single string -- the name of
ONE matcher in CONDITION_REGISTRY -- not a name+params tuple and not
a conjunction expression. A rule whose precondition is "per-pair
forward function-shape" needs a single named handle to gate on;
otherwise the rule would have to redundantly carry
``consistent_color_mapping`` (whole-task scope) with an externally-
applied per-pair restriction the schema does not support. Naming the
per-pair forward cell as a single matcher is the same posture iter 213
took for the per-group forward cell, iter 332 took for the whole-task
inverse cell, iter 333 took for the whole-task bijection cell, iter 334
took for the per-group bijection cell, and iter 335 took for the per-
pair bijection cell.

Why this matters for ARBOR's intended ruleset
---------------------------------------------

The "per-pair forward recolour" rule family -- rules whose per-pair
action can be encoded with a FORWARD (input -> output) table without
ambiguity WITHIN each pair, even if the per-pair inverse is ambiguous
or differs across pairs. The semantic value lies in *what choice the
rule's per-pair action data is free to make per pair*:

  * Per-pair forward-only (THIS matcher): action must carry a per-pair
    forward table; the per-pair inverse may be ambiguous (multiple
    input colours mapping to the same output within a pair).
  * Per-pair bijection (iter 335): strict refinement of this matcher
    that additionally requires the per-pair inverse to be well-defined.
  * Whole-task forward (iter 8): strict refinement of this matcher
    that additionally requires a SINGLE global forward table valid for
    all pairs.

Anti-unification (CLAUDE.md section 8) would attach a per-pair forward-
table generalisation variable to this matcher's fired gate when the
per-pair programs encode possibly DIFFERENT per-pair forward tables
across pairs (each pair having its own forward recolouring map).

Strict refinement / orthogonality summary (universal-over-pairs
semantics, per-pair forward scope):

  * Iter 8 (``consistent_color_mapping``) -- whole-task forward
    function-shape. STRICTLY IMPLIES this matcher: a whole-task forward
    function-shape means the global forward dict is function-shape;
    the restriction to any single pair's subset of (ic, oc) bindings
    is therefore also function-shape (a subset of a function is a
    function). Converse fails on cross-pair drift: pair 0 has
    ic=[0]/oc=[3]; pair 1 has ic=[0]/oc=[4]. Each pair has a per-pair
    forward function-shape ({0: {3}} for pair 0; {0: {4}} for pair 1).
    Global forward {0: {3, 4}} -- NOT function-shape; iter 8 REJECTS.
    THIS matcher FIRES.
  * Iter 213 (``consistent_color_mapping_per_group``) -- per-group
    forward function-shape. STRICTLY IMPLIED BY this matcher: per-pair
    forward function-shape means the per-pair forward dict is function-
    shape; any group within that pair contributes (ic, oc) bindings
    whose forward image is a subset of the per-pair dict's image,
    hence singleton-valued -- per-group forward function-shape holds
    in every group. Converse fails on intra-pair collapse: a pair with
    two groups ic=[0]/oc=[3] and ic=[0]/oc=[4]. Per-group function-
    shape holds in each (|oc| == 1 each). Per-pair forward {0: {3, 4}}
    -- NOT function-shape; THIS matcher REJECTS. Iter 213 FIRES.
  * Iter 332 (``inverse_consistent_color_mapping``) -- whole-task
    inverse function-shape. INDEPENDENT in general: this matcher is
    per-pair scope on the forward axis; iter 332 is whole-task scope
    on the inverse axis. The four cells of the {iter 332, this matcher}
    2x2 product are all realisable -- e.g., iter-10 canonical fixture
    fires both; pair with two groups ic=[0]/oc=[3] and ic=[1]/oc=[3]
    fires iter 332 (global inverse {3: {0, 1}} non-function-shape --
    wait, iter 332 requires INVERSE function-shape, so this fixture
    rejects iter 332; correctly, the iter-332-only cell is two groups
    ic=[0]/oc=[3] and ic=[0]/oc=[4] -- global inverse {3: {0}, 4: {0}}
    function-shape; per-pair forward {0: {3, 4}} not function-shape;
    iter 332 fires, this matcher rejects); the this-matcher-only cell
    is cross-pair drift (each pair forward bijective, global inverse
    e.g. {3: {0, 1}} non-function-shape); the neither cell is per-pair
    forward expansion (this matcher rejects) plus inverse violation
    (iter 332 rejects).
  * Iter 333 (``bijective_color_mapping``) -- whole-task bijection.
    STRICTLY IMPLIES this matcher: whole-task forward function-shape
    is a substring of the whole-task bijection clause; whole-task
    forward implies per-pair forward by the iter-8 implication chain.
    Converse fails on cross-pair drift (this matcher fires, iter 333
    rejects) OR on whole-task inverse violation while preserving
    whole-task forward (iter 333 rejects, this matcher inherits via
    iter 8 implication so a stronger witness is per-pair forward AND
    whole-task forward fail-cell, e.g., two-pair fixture with global
    forward non-function-shape; that fixture also rejects this matcher
    via the universal-over-pairs gate -- not the strict-relaxation cell.
    The clean cell is: pair has two groups ic=[0]/oc=[3] and ic=[1]/
    oc=[3] -- per-pair forward {0: {3}, 1: {3}} function-shape (this
    matcher fires); per-pair inverse {3: {0, 1}} non-function-shape
    (iter 333 rejects via its inverse clause)).
  * Iter 335 (``bijective_color_mapping_per_pair``) -- per-pair
    bijection. STRICTLY IMPLIES this matcher: per-pair forward AND
    inverse function-shape implies per-pair forward function-shape.
    Converse fails on per-pair inverse-only violation: a pair with
    two groups ic=[0]/oc=[3] and ic=[1]/oc=[3]. Per-pair forward
    {0: {3}, 1: {3}} -- function-shape; THIS matcher FIRES. Per-pair
    inverse {3: {0, 1}} -- NOT function-shape; iter 335 REJECTS.
  * Iter 215 (``singleton_recolor_per_group``) -- per-group |ic| ==
    |oc| == 1. INDEPENDENT in general: a within-group ic=[0,1]/oc=[3]
    has |ic|=2 (iter 215 rejects) but per-pair forward {0:{3}, 1:{3}}
    function-shape (this matcher fires); a within-group ic=[0]/oc=[3,4]
    has |oc|=2 (iter 215 rejects) and per-pair forward {0:{3,4}}
    non-function-shape (this matcher rejects); ic=[0]/oc=[3] singleton
    fires both; pair with two singleton groups ic=[0]/oc=[3] and
    ic=[0]/oc=[4] has per-group singletons (iter 215 fires) but per-
    pair forward {0:{3,4}} non-function-shape (this matcher rejects).
  * Iter 13 (``identity_transformation``) -- zero change groups per
    pair. STRICT MUTUAL EXCLUSION (this matcher requires every pair
    to have at least one non-empty group to anchor a per-pair
    forward accumulation).
  * Iter 14 (``input_color_uniform``) -- whole-task |ic_observed|
    == 1. INDEPENDENT.
  * Iter 18 (``output_color_uniform``) -- whole-task |oc_observed|
    == 1. STRICTLY IMPLIES this matcher: if every group's output_colors
    is a singleton with the same global K, the per-pair forward dict
    only has bindings ic -> {K} for ic ranging over input colours of
    that pair -- function-shape. (The implication is reflected in iter
    18's known set-level relation to forward function-shape, used in
    iter-21 / iter-25 emission gates.)
  * Iter 185 (``output_palette_equals_input``) -- whole-grid palette
    equality. INDEPENDENT: forward scope and palette-relation scope
    are orthogonal axes.

Mutual-exclusion witness with iter 8 (per-pair forward AND whole-task
non-forward):

  * Pair 0 groups: ``ic=[0], oc=[3]``. Per-pair forward {0: {3}} --
    function-shape. Per-pair forward holds.
  * Pair 1 groups: ``ic=[0], oc=[4]``. Per-pair forward {0: {4}} --
    function-shape. Per-pair forward holds.
  * Global forward {0: {3, 4}} -- NOT function-shape; iter 8
    REJECTS. THIS matcher FIRES.

Mutual-exclusion witness with iter 213 (per-group forward AND per-pair
non-forward):

  * One pair with two groups: ``ic=[0], oc=[3]`` and ``ic=[0], oc=[4]``.
    Per-group forward function-shape in each (|oc| == 1 each).
    Per-pair forward {0: {3, 4}} -- NOT function-shape; THIS matcher
    REJECTS. Iter 213 FIRES.

Mutual-exclusion witness with iter 335 (per-pair forward AND per-pair
inverse violation):

  * One pair with two groups: ``ic=[0], oc=[3]`` and ``ic=[1], oc=[3]``.
    Per-pair forward {0: {3}, 1: {3}} -- function-shape; THIS matcher
    FIRES. Per-pair inverse {3: {0, 1}} -- NOT function-shape; iter
    335 REJECTS.

Co-fire witness with iter 8 (whole-task forward):

  * Pair groups: ``ic=[0], oc=[3]`` and ``ic=[1], oc=[4]`` and
    ``ic=[2], oc=[5]`` per pair across all pairs. Per-pair forward
    and global forward are both function-shape (the union is the same
    bindings). Both matchers fire. The iter-10 canonical fixture lands
    in this cell.

Co-fire witness with iter 213 (per-group forward):

  * Same iter-10 canonical fixture: every group has |oc| == 1; per-
    pair accumulation preserves function-shape; per-group forward
    holds. Both matchers fire.

Why fail-closed on empty / no-pair / no-group / malformed (same
posture as iter 213 / 214 / 215 / 333 / 334 / 335): a missing or zero-
group pair is upstream extractor breakage or identity territory;
a per-pair forward function-shape claim with zero observations in a
pair is meaningless.

Why ``input_colors`` and ``output_colors`` both required non-empty
lists per group (``len >= 1``): same rationale as iter 213 / 214 /
215 / 333 / 334 / 335 -- a connected change group has at least one
cell; each cell has both an input and an output colour; a zero-length
per-group colour list is an extractor contract violation, not a
valid empty-set function-shape case.

Why strict per-colour validation (bool rejected, range checked):
same strict 0..9 int gate as iter 8 / 14 / 18 / 213 / 214 / 215 /
333 / 334 / 335; the recognition layer must reject placeholder
sentinels.

Params:
  (none) -- pure per-pair forward function-shape check, universal
  over pairs.

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
    333 / 334 / 335 strict-type posture), AND
  - for every pair, the per-pair forward cross-product
    ``{ic: set(output_colors) for ic in input_colors}`` accumulated
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
    strict 0..9 ints (mirrors iter 213 / 214 / 215 / 333 / 334 / 335
    strict-type posture; a change group with zero colours on either
    side is upstream breakage)."""
    if not isinstance(x, list) or len(x) < 1:
        return False
    for v in x:
        if not _is_strict_color(v):
            return False
    return True


@register("consistent_color_mapping_per_pair")
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

        if not forward:
            return False
        if not all(len(v) == 1 for v in forward.values()):
            return False
    return True
