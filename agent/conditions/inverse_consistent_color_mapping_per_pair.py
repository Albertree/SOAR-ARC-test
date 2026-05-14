"""
inverse_consistent_color_mapping_per_pair -- match tasks where EVERY
example pair satisfies, on its OWN per-pair accumulated changed-cell
INVERSE colour relation (unioned across all groups of that pair), the
inverse function-shape gate iter 332 (``inverse_consistent_color_mapping``)
pins globally: within each pair, the accumulated inverse
``output_color -> set(input_colors)`` relation has function-shape (every
key maps to a singleton-valued set), independent of any cross-pair
accumulation.

Recognition vocabulary axis: per-pair projection of the iter-332 INVERSE
function-shape sub-axis. Iter 332 unions the (ic, oc) cross-product
across ALL groups across ALL pairs into a global inverse dict and checks
it is function-shape. The per-group inverse function-shape -- on set-
level data equivalent to ``len(set(input_colors)) == 1`` per group -- is
already named under ``input_color_uniform_per_group`` (iter 214's docstring
explicitly identifies it as "the per-group projection of the inverse
function-shape sub-axis"). This matcher sits BETWEEN iter 332 and iter
214 on the scope axis: it rebuilds the inverse cross-product PER PAIR
(unioned across that pair's groups, not across pairs) and checks the
inverse function-shape gate PER PAIR.

Iter 335's "Next gap" note (quoted in iter 336's
``consistent_color_mapping_per_pair.py`` line 50) named this candidate:

  > iter 335 (per-pair forward AND inverse) STRICTLY IMPLIES this
  > matcher (per-pair forward) AND [the symmetric unnamed per-pair
  > inverse-only matcher]

THIS matcher fills that symmetric unnamed cell.

The natural scope chain on the inverse axis is therefore:

  iter 332 (whole-task)   STRICTLY IMPLIES  this matcher (per-pair)
  this matcher (per-pair) STRICTLY IMPLIES  iter 214 (per-group --
                                            ``input_color_uniform_per_group``)

Both implications are proper: iter 332 fires only when the union across
all pairs is inverse function-shape, which restricts to inverse function-
shape on each pair's subset (a subset of a function is a function); this
matcher fires per pair, so any per-pair inverse violation propagates
from a single group's cross-product within that pair, hence per-pair
inverse function-shape implies per-group inverse function-shape in every
group of every pair (set-level equivalent to per-group |ic| == 1).

The natural strict-relaxation chain on the inverse/bijection axis is:

  iter 333 (whole-task forward AND inverse)
        STRICTLY IMPLIES  iter 8 (whole-task forward) AND iter 332 (whole-task inverse)
  iter 332 (whole-task inverse)
        STRICTLY IMPLIES  this matcher (per-pair inverse)
  iter 335 (per-pair forward AND inverse)
        STRICTLY IMPLIES  iter 336 (per-pair forward) AND this matcher (per-pair inverse)
  this matcher (per-pair inverse)
        STRICTLY IMPLIES  iter 214 (per-group inverse)

Why a distinct matcher rather than parameterising iter 332 / 214 with a
scope flag, or co-firing iter 332 with universal-over-pairs semantics
------------------------------------------------------------

The matcher contract (docs/RULE_FORMAT.md section 4) is name-keyed:
the rule's stored ``condition.type`` is a single string -- the name of
ONE matcher in CONDITION_REGISTRY -- not a name+params tuple and not
a conjunction expression. A rule whose precondition is "per-pair
inverse function-shape" needs a single named handle to gate on;
otherwise the rule would have to redundantly carry
``inverse_consistent_color_mapping`` (whole-task scope) with an
externally-applied per-pair restriction the schema does not support.
Naming the per-pair inverse cell as a single matcher is the same
posture iter 213 took for the per-group forward cell, iter 332 took for
the whole-task inverse cell, iter 333 took for the whole-task bijection
cell, iter 334 took for the per-group bijection cell, iter 335 took for
the per-pair bijection cell, and iter 336 took for the per-pair forward
cell.

Why this matters for ARBOR's intended ruleset
---------------------------------------------

The "per-pair inverse recolour" rule family -- rules whose per-pair
action can be encoded with an INVERSE (output -> input) table without
ambiguity WITHIN each pair, even if the per-pair forward is ambiguous
or the per-pair inverse differs across pairs. The semantic value lies
in *what choice the rule's per-pair action data is free to make per pair*:

  * Per-pair inverse-only (THIS matcher): action must carry a per-pair
    inverse table; the per-pair forward may be ambiguous (multiple
    output colours sharing an input colour within a pair -- e.g.
    a one-to-many expansion that is still inverse-function-shape).
  * Per-pair bijection (iter 335): strict refinement of this matcher
    that additionally requires the per-pair forward to be well-defined.
  * Whole-task inverse (iter 332): strict refinement of this matcher
    that additionally requires a SINGLE global inverse table valid for
    all pairs.

Anti-unification (CLAUDE.md section 8) would attach a per-pair inverse-
table generalisation variable to this matcher's fired gate when the
per-pair programs encode possibly DIFFERENT per-pair inverse tables
across pairs (each pair having its own inverse recolouring map).

Strict refinement / orthogonality summary (universal-over-pairs
semantics, per-pair inverse scope):

  * Iter 332 (``inverse_consistent_color_mapping``) -- whole-task inverse
    function-shape. STRICTLY IMPLIES this matcher: a whole-task inverse
    function-shape means the global inverse dict is function-shape;
    the restriction to any single pair's subset of (oc, ic) bindings is
    therefore also function-shape (a subset of a function is a function).
    Converse fails on cross-pair drift: pair 0 has ic=[3]/oc=[0]; pair 1
    has ic=[4]/oc=[0]. Each pair has a per-pair inverse function-shape
    ({0: {3}} for pair 0; {0: {4}} for pair 1). Global inverse {0: {3, 4}}
    -- NOT function-shape; iter 332 REJECTS. THIS matcher FIRES.
  * Iter 214 (``input_color_uniform_per_group``) -- per-group inverse
    function-shape (set-level equivalent: |ic| == 1 per group). STRICTLY
    IMPLIED BY this matcher: per-pair inverse function-shape means the
    per-pair inverse dict is function-shape; any group within that pair
    contributes (ic, oc) bindings whose inverse image is a subset of the
    per-pair dict's image, hence singleton-valued -- per-group inverse
    function-shape holds in every group. Converse fails on intra-pair
    collapse: a pair with two groups ic=[0]/oc=[3] and ic=[1]/oc=[3].
    Per-group inverse function-shape holds in each (|ic| == 1 each).
    Per-pair inverse {3: {0, 1}} -- NOT function-shape; THIS matcher
    REJECTS. Iter 214 FIRES.
  * Iter 8 (``consistent_color_mapping``) -- whole-task forward
    function-shape. INDEPENDENT in general: this matcher is per-pair
    scope on the inverse axis; iter 8 is whole-task scope on the
    forward axis. The four cells of the {iter 8, this matcher} 2x2
    product are all realisable -- e.g., a one-to-many forward fixture
    fires this matcher (per-pair inverse function-shape) and rejects
    iter 8 (forward not function-shape); cross-pair forward drift fires
    iter 8 only on its non-restriction, etc.
  * Iter 333 (``bijective_color_mapping``) -- whole-task bijection.
    STRICTLY IMPLIES this matcher: whole-task inverse function-shape is
    a substring of the whole-task bijection clause; whole-task inverse
    implies per-pair inverse by the iter-332 implication chain.
    Converse fails on cross-pair drift (this matcher fires, iter 333
    rejects) OR on whole-task forward violation while preserving
    whole-task inverse (iter 333 rejects via its forward clause, this
    matcher inherits via iter 332 implication).
  * Iter 335 (``bijective_color_mapping_per_pair``) -- per-pair
    bijection. STRICTLY IMPLIES this matcher: per-pair forward AND
    inverse function-shape implies per-pair inverse function-shape.
    Converse fails on per-pair forward-only violation: a pair with two
    groups ic=[0]/oc=[3] and ic=[0]/oc=[4]. Per-pair inverse
    {3: {0}, 4: {0}} -- function-shape; THIS matcher FIRES. Per-pair
    forward {0: {3, 4}} -- NOT function-shape; iter 335 REJECTS.
  * Iter 336 (``consistent_color_mapping_per_pair``) -- per-pair forward
    function-shape. INDEPENDENT in general: forward and inverse per-pair
    function-shapes are orthogonal axes. Both cells of the 2x2 product
    are realisable -- e.g., per-pair forward-only fires iter 336 only
    (two groups ic=[0]/oc=[3] and ic=[1]/oc=[3]); per-pair inverse-only
    fires THIS matcher only (two groups ic=[0]/oc=[3] and ic=[0]/oc=[4]);
    per-pair bijection cell fires both (and additionally iter 335).
  * Iter 215 (``singleton_recolor_per_group``) -- per-group |ic| ==
    |oc| == 1. INDEPENDENT in general: a within-group ic=[0]/oc=[3, 4]
    has |oc|=2 (iter 215 rejects) but per-pair inverse {3:{0}, 4:{0}}
    function-shape (this matcher fires); a within-group ic=[0,1]/oc=[3]
    has |ic|=2 (iter 215 rejects) and per-pair inverse {3:{0,1}}
    non-function-shape (this matcher rejects); ic=[0]/oc=[3] singleton
    fires both; pair with two singleton groups ic=[0]/oc=[3] and
    ic=[1]/oc=[3] has per-group singletons (iter 215 fires) but per-
    pair inverse {3:{0,1}} non-function-shape (this matcher rejects).
  * Iter 13 (``identity_transformation``) -- zero change groups per
    pair. STRICT MUTUAL EXCLUSION (this matcher requires every pair
    to have at least one non-empty group to anchor a per-pair
    inverse accumulation).
  * Iter 14 (``input_color_uniform``) -- whole-task |ic_observed|
    == 1. STRICTLY IMPLIES this matcher: if every group's input_colors
    is a singleton with the same global C, the per-pair inverse dict
    only has bindings oc -> {C} for oc ranging over output colours of
    that pair -- function-shape. (Symmetric to iter 18's known set-
    level relation to forward function-shape.)
  * Iter 18 (``output_color_uniform``) -- whole-task |oc_observed|
    == 1. INDEPENDENT.
  * Iter 185 (``output_palette_equals_input``) -- whole-grid palette
    equality. INDEPENDENT: inverse scope and palette-relation scope
    are orthogonal axes.

Mutual-exclusion witness with iter 332 (per-pair inverse AND whole-task
non-inverse):

  * Pair 0 groups: ``ic=[3], oc=[0]``. Per-pair inverse {0: {3}} --
    function-shape. Per-pair inverse holds.
  * Pair 1 groups: ``ic=[4], oc=[0]``. Per-pair inverse {0: {4}} --
    function-shape. Per-pair inverse holds.
  * Global inverse {0: {3, 4}} -- NOT function-shape; iter 332
    REJECTS. THIS matcher FIRES.

Mutual-exclusion witness with iter 214 (per-group inverse AND per-pair
non-inverse):

  * One pair with two groups: ``ic=[0], oc=[3]`` and ``ic=[1], oc=[3]``.
    Per-group inverse function-shape in each (|ic| == 1 each).
    Per-pair inverse {3: {0, 1}} -- NOT function-shape; THIS matcher
    REJECTS. Iter 214 FIRES.

Mutual-exclusion witness with iter 335 (per-pair inverse AND per-pair
forward violation):

  * One pair with two groups: ``ic=[0], oc=[3]`` and ``ic=[0], oc=[4]``.
    Per-pair inverse {3: {0}, 4: {0}} -- function-shape; THIS matcher
    FIRES. Per-pair forward {0: {3, 4}} -- NOT function-shape; iter
    335 REJECTS.

Co-fire witness with iter 332 (whole-task inverse):

  * Pair groups: ``ic=[3], oc=[0]`` and ``ic=[4], oc=[1]`` and
    ``ic=[5], oc=[2]`` per pair across all pairs. Per-pair inverse
    and global inverse are both function-shape (the union is the same
    bindings). Both matchers fire.

Co-fire witness with iter 214 (per-group inverse):

  * Same canonical singleton-singleton fixture: every group has
    |ic| == 1; per-pair accumulation preserves inverse function-shape;
    per-group inverse holds. Both matchers fire.

Why fail-closed on empty / no-pair / no-group / malformed (same
posture as iter 213 / 214 / 215 / 333 / 334 / 335 / 336): a missing or
zero-group pair is upstream extractor breakage or identity territory;
a per-pair inverse function-shape claim with zero observations in a
pair is meaningless.

Why ``input_colors`` and ``output_colors`` both required non-empty
lists per group (``len >= 1``): same rationale as iter 213 / 214 /
215 / 333 / 334 / 335 / 336 -- a connected change group has at least
one cell; each cell has both an input and an output colour; a zero-
length per-group colour list is an extractor contract violation, not
a valid empty-set function-shape case.

Why strict per-colour validation (bool rejected, range checked):
same strict 0..9 int gate as iter 8 / 14 / 18 / 213 / 214 / 215 /
332 / 333 / 334 / 335 / 336; the recognition layer must reject
placeholder sentinels.

Params:
  (none) -- pure per-pair inverse function-shape check, universal
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
    332 / 333 / 334 / 335 / 336 strict-type posture), AND
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
    strict 0..9 ints (mirrors iter 213 / 214 / 215 / 333 / 334 / 335 /
    336 strict-type posture; a change group with zero colours on either
    side is upstream breakage)."""
    if not isinstance(x, list) or len(x) < 1:
        return False
    for v in x:
        if not _is_strict_color(v):
            return False
    return True


@register("inverse_consistent_color_mapping_per_pair")
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
                    inverse.setdefault(oc, set()).add(ic)

        if not inverse:
            return False
        if not all(len(v) == 1 for v in inverse.values()):
            return False
    return True
