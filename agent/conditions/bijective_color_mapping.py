"""
bijective_color_mapping -- match tasks where the accumulated changed-cell
colour relation across all example pairs is BOTH forward-function-shape
AND inverse-function-shape: every observed input colour has exactly one
output colour image AND every observed output colour has exactly one
input colour preimage. The named co-fire handle of (iter 8 AND iter 332)
on the changed-cell colour mapping, with the palette-equality clause of
iter 330 dropped.

Recognition vocabulary axis: the BIJECTION cell of the {forward,
inverse} function-shape cross-product on the changed-cell colour
mapping. The four cells of that 2x2 are already individually named --
iter 8 (forward only), iter 332 (inverse only), neither -- but the
forward-AND-inverse cell has no STANDALONE handle. Iter 330
(``output_palette_is_permutation_of_input_palette``) is the strict
refinement of this cell by additionally requiring whole-grid palette
equality (iter 185); this matcher is iter 330 with the palette-equality
clause dropped.

Iter 332's "Next gap" note named this candidate:

  > A third candidate is the CO-FIRE refinement matcher of (iter 8 AND
  > this iter 332) WITHOUT palette equality: bijection on the changed-
  > cell mapping across pairs, the strict relaxation of iter 330 by
  > dropping the palette-equality clause.

Why a distinct matcher rather than co-firing iter 8 AND iter 332
----------------------------------------------------------------

The matcher contract (docs/RULE_FORMAT.md section 4) is name-keyed:
the rule's stored ``condition.type`` is a single string -- the name of
ONE matcher in CONDITION_REGISTRY -- not a name+params tuple and not
a conjunction expression. A rule whose precondition is "forward AND
inverse function-shape without palette equality" needs a single named
handle to gate on; otherwise the rule would have to redundantly carry
both ``consistent_color_mapping`` and ``inverse_consistent_color_mapping``
in some external conjunction structure that the schema does not
support. Naming the bijection cell as a single matcher is the same
posture iter 213 / 214 / 215 / 217 / 218 / 220-228 took when naming
co-fire cells of finer-grained matchers.

Why this matters for ARBOR's intended ruleset
---------------------------------------------

The "recolour by either direction" rule family -- rules whose action
can be encoded with EITHER a forward (input -> output) table OR an
inverse (output -> input) table without ambiguity, both directions
being well-defined. The semantic value lies in *what choice the rule's
action data is free to make*:

  * Forward-only (iter 8): action must carry a forward table (input
    -> output); the inverse direction is ambiguous (some output has
    multiple preimages).
  * Inverse-only (iter 332): action must carry an inverse table
    (output -> input); the forward direction is ambiguous.
  * Both (THIS matcher): action can use EITHER direction, plus more
    expressive parameterisations are admissible (e.g., the action
    can swap colours without explicitly carrying both directions
    because either suffices to recover the other).
  * Iter 330's strict refinement: additionally requires palette
    equality, which means the bijection is a PERMUTATION of the
    pre-existing palette -- a stronger geometric precondition than
    mere bijection.

Anti-unification (CLAUDE.md section 8) would attach a bijection-
shape generalisation variable to this matcher's fired gate when the
per-pair programs encode the same forward (or inverse) table across
pairs.

Strict refinement / orthogonality summary (observed mapping universal
semantics on accumulated change-group observations):

  * Iter 8 (``consistent_color_mapping``) -- forward function-shape.
    STRICTLY IMPLIED BY this matcher (this matcher = iter 8 AND iter
    332; bijection implies forward). The converse fails: a forward-
    only mapping (e.g., 0 -> 3, 1 -> 3 -- forward function-shape,
    inverse collapse) fires iter 8 and rejects this matcher.
  * Iter 332 (``inverse_consistent_color_mapping``) -- inverse
    function-shape. STRICTLY IMPLIED BY this matcher (this matcher =
    iter 8 AND iter 332; bijection implies inverse). The converse
    fails: an inverse-only mapping (e.g., 0 -> {3, 4} -- forward
    expansion, inverse function-shape) fires iter 332 and rejects
    this matcher.
  * Iter 330 (``output_palette_is_permutation_of_input_palette``) --
    forward AND inverse function-shape AND whole-grid palette
    equality. STRICTLY IMPLIES this matcher (iter 330 = bijection
    AND palette equality; this matcher = bijection alone). The
    converse fails: a bijection with palette inequality (e.g., input
    palette {0, 1, 2}, output palette {3, 4, 5}, changes 0 -> 3,
    1 -> 4, 2 -> 5) fires this matcher and rejects iter 330.
  * Iter 13 (``identity_transformation``) -- zero changed cells.
    STRICTLY MUTUALLY EXCLUSIVE: identity has no observations, so
    the accumulated mapping is empty, so this matcher REJECTS
    (mirroring iter 8 / iter 332 empty-evidence rejection).
  * Iter 185 (``output_palette_equals_input``) -- whole-grid palette
    equality. INDEPENDENT of this matcher: bijection can fire with
    palette equality (iter 330 territory; co-fire with iter 185) or
    without (this matcher's strict relaxation of iter 330). Palette
    equality can fire without bijection (palette-preserving collapse:
    0 -> 1, 2 -> 1 with palette {0, 1, 2} on both sides -- iter 185
    fires, this matcher rejects).
  * Iter 213 (``consistent_color_mapping_per_group``) -- per-group
    forward function-shape. INDEPENDENT (different scope; per-group
    forward and whole-task bijection are not in a refinement relation
    in general).
  * Iter 214 (``input_color_uniform_per_group``) -- per-group inverse
    function-shape (equivalent to per-group |ic| == 1). INDEPENDENT
    in general for the same scope-vs-projection reason.
  * Iter 14 (``input_color_uniform``) / iter 18 (``output_color_uniform``)
    -- pin the changed-cell SIDES to a single colour (|observed_ic|
    == 1 / |observed_oc| == 1). On the iter 14 + iter 18 co-fire
    cell, the mapping is trivially a 1-to-1 between two singletons,
    so this matcher fires too. INDEPENDENT in general but co-fires
    on the {single ic, single oc} cell.

Mutual-exclusion witness with iter 8 (forward-only, inverse-collapse):

  * Pair groups: ``input_colors=[0], output_colors=[3]`` AND
    ``input_colors=[1], output_colors=[3]``. The forward dict
    becomes ``{0: {3}, 1: {3}}`` -- iter 8 FIRES (each input has a
    unique output). The inverse dict becomes ``{3: {0, 1}}`` -- iter
    332 REJECTS (output 3 has two preimages). THIS matcher REJECTS.

Mutual-exclusion witness with iter 332 (inverse-only, forward-expansion):

  * Pair groups: ``input_colors=[0], output_colors=[3, 4]``. The
    forward dict becomes ``{0: {3, 4}}`` -- iter 8 REJECTS. The
    inverse dict becomes ``{3: {0}, 4: {0}}`` -- iter 332 FIRES.
    THIS matcher REJECTS.

Mutual-exclusion witness with iter 330 (bijection with palette
inequality):

  * Same forward and inverse mapping as the iter-330 co-fire witness
    below (e.g., 0 -> 3, 1 -> 4) but with palette inequality on the
    whole-grid scope (input palette ``{0, 1, 2}``, output palette
    ``{2, 3, 4}``). Forward AND inverse function-shape on changes;
    iter 330 REJECTS (no palette equality); THIS matcher FIRES.

Co-fire witness with iter 330 (palette-permutation bijection):

  * A 2-cycle swapping ``red <-> blue`` per pair with palette equality
    maintained. Both iter 330 AND iter 8 AND iter 332 AND THIS
    matcher fire.

Why fail-closed on empty / malformed (mirroring iter 8 / iter 332):
a task with zero changed cells has no observed mapping, so both
forward and inverse accumulated dicts are empty. An empty mapping is
properly handled by iter 13 (identity), not by misreporting this one.
Iter 8 and iter 332 take the same posture (``if not color_map:
return False``).

Why strict-type-gate on per-group colour lists (mirroring iter 8 /
iter 14 / iter 18 / iter 184-212 / iter 330 / iter 332 strict 0..9
int gate on change-cell colours): per-group fields are extracted
from change-cell positions and should be in [0, 9]; bools are an int
subclass and must be rejected to keep the recognition layer from
accepting placeholder sentinels.

Params:
  (none) -- pure bijection check on the accumulated changed-cell
  colour mapping.

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis's ``groups`` field is a list, AND
  - every group is a dict, AND
  - every group has ``input_colors`` and ``output_colors`` that are
    non-empty lists of strict 0..9 ints (no bools, no out-of-range),
    AND
  - the accumulated ``input_color -> set(output_colors)`` forward
    relation across all change groups of all pairs is NON-EMPTY,
    AND
  - every observed input colour maps to EXACTLY ONE output colour
    across the union of all pairs' groups (forward function-shape),
    AND
  - every observed output colour maps from EXACTLY ONE input colour
    across the union of all pairs' groups (inverse function-shape).

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
    strict 0..9 ints (mirrors iter 8 / iter 330 / iter 332 strict-type
    posture; a change group with zero colours on either side is
    upstream breakage)."""
    if not isinstance(x, list) or len(x) < 1:
        return False
    for v in x:
        if not _is_strict_color(v):
            return False
    return True


@register("bijective_color_mapping")
def match(patterns: dict, params: dict) -> bool:
    if not isinstance(patterns, dict):
        return False
    pair_analyses = patterns.get("pair_analyses")
    if not isinstance(pair_analyses, list) or not pair_analyses:
        return False

    forward: dict = {}
    inverse: dict = {}

    for analysis in pair_analyses:
        if not isinstance(analysis, dict):
            return False
        groups = analysis.get("groups")
        if not isinstance(groups, list):
            return False
        for g in groups:
            if not isinstance(g, dict):
                return False
            input_colors = g.get("input_colors")
            output_colors = g.get("output_colors")
            if not _is_color_list(input_colors):
                return False
            if not _is_color_list(output_colors):
                return False
            for ic in input_colors:
                for oc in output_colors:
                    forward.setdefault(ic, set()).add(oc)
                    inverse.setdefault(oc, set()).add(ic)

    if not forward:
        return False
    if not all(len(v) == 1 for v in forward.values()):
        return False
    if not all(len(v) == 1 for v in inverse.values()):
        return False
    return True
