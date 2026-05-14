"""
bijective_color_mapping_per_group -- match tasks where EVERY change
group of EVERY example pair satisfies, on its OWN per-group palettes,
the bijection precondition iter 333 (``bijective_color_mapping``)
pins globally: within each group, every observed input colour maps to
exactly one observed output colour AND every observed output colour
maps from exactly one observed input colour.

Recognition vocabulary axis: per-group projection of the iter-333
bijection (forward-AND-inverse function-shape) sub-axis. Iter 333
unions the (ic, oc) cross-product across ALL groups across ALL pairs
into a global forward dict and a global inverse dict, then checks both
are function-shape. This matcher rebuilds the cross-product PER GROUP
and checks both function-shape gates PER GROUP, independent of any
cross-group / cross-pair consistency. The named co-fire handle of
(iter 213 AND iter 214) on the per-group scope -- iter 213 pins per-
group forward function-shape, iter 214 pins per-group inverse
function-shape (equivalently, per-group |ic| == 1); this matcher pins
their conjunction.

On set-level data (the per-group ``input_colors`` / ``output_colors``
fields, both ordered-unique-int lists), the per-group bijection gate
reduces to a tight set-level claim: for every group,
``len(set(input_colors)) == 1`` AND ``len(set(output_colors)) == 1``.
The per-group forward cross-product ``{ic: set(output_colors) for ic
in input_colors}`` is function-shaped iff each ``ic`` is bound to a
singleton ``oc`` set -- which on set-level data happens exactly when
the group's ``output_colors`` set has cardinality 1. By symmetric
duality, the per-group inverse cross-product ``{oc: set(input_colors)
for oc in output_colors}`` is function-shaped iff the group's
``input_colors`` set has cardinality 1. Empty per-group ``input_colors``
or ``output_colors`` is rejected as an extractor contract violation
(mirroring iter 14 / 18 / 213 / 214 strict-type posture).

Iter 333's "Next gap" note named this candidate:

  > (a) per-group ``bijective_color_mapping_per_group`` -- the per-
  > group projection of this iter's matcher [...]; genuinely new on
  > the cross-group-consistency sub-axis of iter 215's territory.

The pure per-group projection without any added cross-group clause is
the smallest defensible variant: mirroring iter 215 (which is the per-
group projection of iter 8 with no added cross-pair clause) on the
bijection scope. Adding a global cross-group constraint would conflate
two axes (per-group + cross-group) -- the natural scope-mirror of iter
333 onto the per-group projection drops the global accumulator and
applies the bijection check group-by-group only.

Why a distinct matcher rather than parameterising iter 215 with an
``inverse: True`` flag, or co-firing iter 213 AND iter 214
------------------------------------------------------------

The matcher contract (docs/RULE_FORMAT.md section 4) is name-keyed:
the rule's stored ``condition.type`` is a single string -- the name of
ONE matcher in CONDITION_REGISTRY -- not a name+params tuple and not
a conjunction expression. A rule whose precondition is "per-group
forward AND per-group inverse function-shape" needs a single named
handle to gate on; otherwise the rule would have to redundantly carry
both ``consistent_color_mapping_per_group`` and
``input_color_uniform_per_group`` in some external conjunction
structure the schema does not support. Naming the per-group bijection
cell as a single matcher is the same posture iter 333 took for the
whole-task bijection cell, iter 215 took for the per-group function-
shape cell, and iters 213 / 214 / 215 / 217 / 218 / 220-228 took when
naming co-fire cells of finer-grained matchers.

Why this matters for ARBOR's intended ruleset
---------------------------------------------

The "per-group recolour by either direction" rule family -- rules
whose per-group action can be encoded with EITHER a forward (input ->
output) table OR an inverse (output -> input) table without ambiguity
WITHIN each group, both per-group directions being well-defined. The
semantic value lies in *what choice the rule's per-group action data
is free to make per group*:

  * Per-group forward-only (iter 215 alone): action must carry a
    per-group forward table {c_g -> k_g}; the per-group inverse is
    ambiguous (some k_g has multiple c_g preimages within the group).
  * Per-group inverse-only (iter 214 alone): action must carry a
    per-group inverse table {k_g -> c_g}; the per-group forward is
    ambiguous (some c_g expands to multiple k_g within the group).
  * Both per-group (THIS matcher): per-group action can use EITHER
    direction within each group, plus more expressive per-group
    parameterisations are admissible (e.g., per-group swap, per-group
    permutation cycle) because each direction is well-defined.

Anti-unification (CLAUDE.md section 8) would attach a per-group
bijection-shape generalisation variable to this matcher's fired gate
when the per-pair programs encode the same per-group (c_g, k_g)
bijection across pairs.

Strict refinement / orthogonality summary (universal-over-groups-and-
pairs semantics, per-group bijection scope):

  * Iter 333 (``bijective_color_mapping``) -- whole-task bijection.
    STRICTLY IMPLIES this matcher: a whole-task bijection means the
    global forward and inverse dicts are function-shape, so the
    restriction to any single group's domain is also function-shape.
    Converse fails: per-group bijection on groups with overlapping
    input or output palettes across groups can produce a global non-
    function-shape (e.g. group 1 ic=[0]/oc=[3], group 2 ic=[0]/oc=[4]
    -- per-group bijection holds in each, but global forward {0: {3, 4}}
    is not function-shape).
  * Iter 213 (``consistent_color_mapping_per_group``) -- per-group
    forward function-shape (per-group |oc| == 1). STRICTLY IMPLIED BY
    this matcher (this matcher = iter 213 AND iter 214; per-group
    bijection implies per-group forward). Converse fails on a group
    with ic=[0, 1]/oc=[3] -- per-group forward function-shape (both
    inputs map to 3), per-group inverse non-function-shape (3 maps
    from {0, 1}); iter 213 fires, this matcher rejects.
  * Iter 214 (``input_color_uniform_per_group``) -- per-group |ic|
    == 1 (equivalent to per-group inverse function-shape on set-level
    data). STRICTLY IMPLIED BY this matcher (this matcher = iter 213
    AND iter 214; per-group bijection implies per-group inverse).
    Converse fails on a group with ic=[0]/oc=[3, 4] -- per-group
    |ic| == 1 (iter 214 fires), per-group forward non-function-shape
    (0 expands to {3, 4}; this matcher rejects).
  * Iter 215 (``singleton_recolor_per_group``) -- per-group |ic| ==
    |oc| == 1 (the iter-213 AND iter-214 co-fire cell). BIT-IDENTICAL
    to this matcher on set-level data: per-group bijection on set-
    level data IS |ic| == |oc| == 1 per group, which is exactly iter
    215's contract. Defended as a distinct registry slot only by
    semantic intent: iter 215 names the singleton-recolour
    precondition (each group recolours one input colour to one output
    colour); this matcher names the per-group bijection precondition
    (the per-group recolouring is bijective). The two contracts pin
    the same set of patterns on the current set-level data
    representation but name different rule-family preconditions.
    NOTE: this set-level equivalence is recorded explicitly here so
    future iters that broaden the per-group representation (e.g.,
    multiset / multiplicity-aware per-group colours) can re-examine
    whether the contracts genuinely diverge. If the per-group fields
    ever carry duplicate colours, iter 215's |set| == 1 contract and
    this matcher's per-group bijection-on-cross-product contract will
    name distinct cells; on the current strict set-level lists the
    two contracts coincide.
  * Iter 8 (``consistent_color_mapping``) -- whole-task forward
    function-shape. INDEPENDENT in general (different scope; per-group
    bijection and whole-task forward function-shape are not in a
    refinement relation in general -- iter 333 explicitly named this
    relation as "INDEPENDENT" for the per-group / whole-task pair).
    Co-fires when both fire on the iter-10 canonical fixture
    (per-group bijection + global function-shape coincide).
  * Iter 332 (``inverse_consistent_color_mapping``) -- whole-task
    inverse function-shape. INDEPENDENT in general (different scope).
  * Iter 13 (``identity_transformation``) -- zero change groups per
    pair. STRICT MUTUAL EXCLUSION (this matcher requires every pair
    to have at least one non-empty group).
  * Iter 14 (``input_color_uniform``) -- whole-task |ic_observed|
    == 1. INDEPENDENT in general: per-group |ic| == 1 does not require
    the per-group singletons to be cross-group identical; iter 14
    requires the cross-group identity but only on the input side and
    only at the whole-task scope.
  * Iter 18 (``output_color_uniform``) -- whole-task |oc_observed|
    == 1. INDEPENDENT in general for the same reason on the output
    side.
  * Every cell- / position- / dimension-axis matcher (iters 1 / 17 /
    19 / 20 / 22 / 23 / 24 / 26 / 28 / 32 / 33 / 38 / 39 / 40 / 41 /
    42 / 182 / 183 / 184 / 185 / 186 / 187 / 188 / 189 / 190 / 191 /
    210 / 211 / 212) -- orthogonal to per-group bijection.

Mutual-exclusion witness with iter 213 (per-group forward function-
shape but per-group inverse non-function-shape):

  * Pair groups: one group with ``input_colors=[0, 1]``,
    ``output_colors=[3]``. Per-group forward cross-product:
    ``{0: {3}, 1: {3}}`` -- function-shape (iter 213 fires). Per-
    group inverse cross-product: ``{3: {0, 1}}`` -- NON-function-
    shape. THIS matcher REJECTS (per-group inverse fails).

Mutual-exclusion witness with iter 214 (per-group inverse function-
shape but per-group forward non-function-shape):

  * Pair groups: one group with ``input_colors=[0]``,
    ``output_colors=[3, 4]``. Per-group |ic| == 1 (iter 214 fires).
    Per-group forward cross-product: ``{0: {3, 4}}`` -- NON-function-
    shape. THIS matcher REJECTS (per-group forward fails).

Co-fire witness with iter 333 (whole-task bijection AND per-group
bijection):

  * Pair groups: one group with ic=[0]/oc=[3]; another group with
    ic=[1]/oc=[4]; another group with ic=[2]/oc=[5]. Per-group
    bijection holds in every group (|ic| == |oc| == 1 each). Global
    forward {0: {3}, 1: {4}, 2: {5}} -- function-shape (iter 333
    fires). Both fire.

Mutual-exclusion witness with iter 333 (per-group bijection AND whole-
task non-bijection):

  * Pair groups: group 1 with ic=[0]/oc=[3]; group 2 with ic=[0]/
    oc=[4]. Per-group bijection holds (each group has |ic| == |oc|
    == 1). Global forward dict {0: {3, 4}} -- NOT function-shape; iter
    333 REJECTS. THIS matcher FIRES. Independence witness.

Why fail-closed on empty / no-group / malformed (same posture as iter
213 / 214 / 215 / 333): a missing or zero-group pair is upstream
extractor breakage or identity-territory; a per-group bijection claim
with zero observations is meaningless.

Why ``input_colors`` and ``output_colors`` both required non-empty
lists per group (``len >= 1``): same rationale as iter 213 / 214 /
215 / 333 -- a connected change group has at least one cell; each
cell has both an input and an output colour; a zero-length per-group
colour list is an extractor contract violation, not a valid empty-
set bijection case.

Why strict per-colour validation (bool rejected, range checked): same
strict 0..9 int gate as iter 8 / 14 / 18 / 213 / 214 / 215 / 333; the
recognition layer must reject placeholder sentinels.

Params:
  (none) -- pure per-group bijection check, universal over groups
  and pairs.

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
    333 strict-type posture), AND
  - for every group, the per-group forward cross-product
    ``{ic: set(output_colors) for ic in input_colors}`` has function-
    shape (every binding's value is a singleton), AND
  - for every group, the per-group inverse cross-product
    ``{oc: set(input_colors) for oc in output_colors}`` has function-
    shape (every binding's value is a singleton).

No companion-touch required: ``input_colors`` / ``output_colors`` (iter
1 / 8) have been emitted from ``_analyze_pair`` since their respective
iters; this iter is a pure matcher addition with no
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
    strict 0..9 ints (mirrors iter 213 / 214 / 215 / 333 strict-type
    posture; a change group with zero colours on either side is
    upstream breakage)."""
    if not isinstance(x, list) or len(x) < 1:
        return False
    for v in x:
        if not _is_strict_color(v):
            return False
    return True


@register("bijective_color_mapping_per_group")
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
        for group in groups:
            if not isinstance(group, dict):
                return False
            input_colors = group.get("input_colors")
            output_colors = group.get("output_colors")
            if not _is_color_list(input_colors):
                return False
            if not _is_color_list(output_colors):
                return False

            forward: dict = {}
            inverse: dict = {}
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
