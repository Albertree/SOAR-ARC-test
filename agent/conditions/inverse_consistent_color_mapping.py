"""
inverse_consistent_color_mapping -- match tasks where every changed
cell's OUTPUT colour maps from a single, unambiguous INPUT colour
across all example pairs. The strict symmetric dual of iter 8
(``consistent_color_mapping``): iter 8 pins forward-function shape
(every observed input colour has exactly one output colour image);
THIS matcher pins inverse-function shape (every observed output
colour has exactly one input colour preimage).

Recognition vocabulary axis: the INVERSE-function-shape axis of the
changed-cell colour mapping. Iter 330 already pins the conjunction of
forward function-shape AND inverse function-shape AND whole-grid
palette equality (palette permutation). Iter 8 already pins the
forward function-shape alone. The inverse function-shape axis ALONE
-- without palette equality and without forward function-shape -- has
no existing named handle. This matcher names that cell.

Iter 331's "Next gap" note named this candidate:

  > the SURJECTIVITY matcher -- the dual of iter 330's INJECTIVITY
  > check (every input colour has at least one output preimage in the
  > changed-cell colour mapping; rejects "fresh-recolour-only" tasks
  > where no output colour was previously in the input).

In iter 330's implementation, "injectivity" is checked by accumulating
the inverse dict ``inverse: output_color -> set(input_colors)`` and
requiring every entry is a singleton. That same check, applied alone
without the forward-function or palette-equality clauses, is THIS
matcher.

Why this matters for ARBOR's intended ruleset
---------------------------------------------

The "inverse-function-shape" rule family -- rules whose mapping
admits a deterministic INVERSE table (every output colour can be
traced back to a unique input colour). The semantic value lies in
*what the rule's action data must carry*: a forward-function-shape
mapping (iter 8) lets a rule encode ``input_color -> output_color``
as a flat dict; an inverse-function-shape mapping lets a rule encode
``output_color -> input_color`` as a flat dict. The two are
independent on the cross-product of {forward-function, inverse-
function}, and each picks out a different rule shape:

  * Forward-function (iter 8): a "recolour by input" rule -- the
    action looks up the input colour in a forward table and writes
    the corresponding output colour.
  * Inverse-function (THIS matcher): a "recolour by target" rule --
    the action knows the desired output colour and can recover the
    source colour. Useful for rules whose action is parameterised
    by the output side (e.g., "every cell that becomes blue used to
    be red; every cell that becomes green used to be yellow"); also
    a structural precondition for rules whose forward mapping is
    one-to-many (a single input colour expanding to multiple output
    colours that each have a unique input source).
  * Both (forward AND inverse): the bijection cell -- the iter-330
    permutation precondition's strict superset (it does not require
    iter 185 palette equality).

Anti-unification (CLAUDE.md section 8) would attach an inverse-
function-shape generalisation variable to this matcher's fired gate
when the per-pair programs encode the same ``output_color ->
input_color`` table across pairs.

Why a distinct matcher rather than co-firing iter 8 with iter 330
-----------------------------------------------------------------

The (iter 8 AND iter 330) co-fire set is STRICTLY SMALLER than this
matcher's territory: iter 330 requires both palette equality AND
forward function-shape AND inverse function-shape. This matcher
requires ONLY inverse function-shape.

Specifically:

  * A task whose forward mapping is one-to-many (one input colour
    expands to multiple output colours, with each output colour
    having a unique input preimage) fires THIS matcher but REJECTS
    iter 8.
  * A task with palette inequality but inverse function-shape fires
    THIS matcher but REJECTS iter 330.
  * The bijection-with-palette-equality cell fires all three (iter
    8 AND iter 330 AND this matcher).

Why a distinct matcher rather than parameterising iter 8 with a
``direction: "inverse"`` flag: the matcher contract
(docs/RULE_FORMAT.md section 4) is name-keyed recognition
vocabulary; the rule's stored ``condition.type`` is the recognition
handle's name, not a name+params tuple. The two function-shape
directions name distinct preconditions for distinct rule shapes
(forward-table-keyed rules vs inverse-table-keyed rules); keeping
them in separate registry slots lets anti-unification attach the
right gate per rule family.

Strict refinement / orthogonality summary (observed-output-colour
universal semantics on accumulated change-group observations):

  * Iter 8 (``consistent_color_mapping``) -- forward function-shape.
    INDEPENDENT in general. Co-fires on the bijection cell;
    inverse-function-only fires this matcher and rejects iter 8;
    forward-function-only fires iter 8 and rejects this matcher.
  * Iter 330 (``output_palette_is_permutation_of_input_palette``) --
    forward ^ inverse function-shape ^ palette equality. STRICTLY
    IMPLIES this matcher (inverse function-shape is a clause of
    iter 330). The converse does NOT hold: a task with palette
    inequality but inverse function-shape fires THIS matcher and
    rejects iter 330.
  * Iter 13 (``identity_transformation``) -- zero changed cells.
    STRICTLY MUTUALLY EXCLUSIVE: identity has no observations, so
    the accumulated mapping is empty, so this matcher REJECTS
    (mirroring iter 8's empty-evidence rejection).
  * Iter 185 (``output_palette_equals_input``) -- whole-grid palette
    equality. INDEPENDENT of this matcher: inverse function-shape
    can fire on tasks with palette inequality (collapse / expansion
    cells); palette equality can fire without inverse function-shape
    (a task with palette-preserving merge -- two input colours both
    mapping to one output -- fires iter 185 and rejects this
    matcher because the inverse mapping has two preimages for that
    output).
  * Iter 14 (``input_color_uniform``) / iter 15
    (``output_color_uniform``) -- pin changed-cell sides to a single
    colour. INDEPENDENT in general.
  * Iter 213 (``consistent_color_mapping_per_group``) -- per-group
    forward function-shape. INDEPENDENT of the whole-task inverse-
    function axis (different scope AND different direction).
  * Iter 329 (``change_palette_intersection_nonempty_per_group``) --
    per-group anchor preservation. INDEPENDENT.
  * Iter 331 (``input_palette_intersects_output_palette``) -- whole-
    grid anchor preservation. INDEPENDENT.
  * Every cell- / position- / dimension-axis matcher (iters 1 / 17 /
    19 / 20 / 22 / 23 / 24 / 28 / 33 / 38 / 39 / 40 / 41 / 42 / 182
    / 183) -- orthogonal to the colour-mapping-direction axis.

Mutual-exclusion witness with iter 8 (forward) -- a one-to-many
forward mapping that is inverse-function-shape:

  * Pair groups: ``input_colors=[0], output_colors=[3, 4]`` AND
    ``input_colors=[0], output_colors=[3, 4]`` (same C ic across
    two groups, with the same two oc's expanded). The forward dict
    becomes ``{0: {3, 4}}`` -- iter 8 rejects (forward not function-
    shaped). The inverse dict becomes ``{3: {0}, 4: {0}}`` -- every
    output has a unique input preimage. THIS matcher FIRES.

Co-fire witness with iter 8 (bijection cell):

  * ``input_colors=[0], output_colors=[3]`` AND ``input_colors=[1],
    output_colors=[4]``. Forward ``{0: {3}, 1: {4}}``, inverse
    ``{3: {0}, 4: {1}}``. Both function-shape directions; both
    matchers fire. Iter 330 ALSO fires if palette equality holds.

Mutual-exclusion witness with iter 330 (palette inequality plus
inverse function-shape):

  * Same as the iter-8 co-fire witness above, but with palette
    inequality on the whole-grid scope (e.g., input palette
    ``{0, 1, 2}``, output palette ``{2, 3, 4}``). Inverse mapping is
    still function-shape across the two changes; iter 8 fires; THIS
    matcher fires; iter 330 REJECTS (no palette equality).

Strict-implication witness from iter 330:

  * A palette-permutation task -- e.g., a 2-cycle swapping red <->
    blue per pair, with palette equality maintained. Both iter 330
    AND iter 8 AND THIS matcher fire.

Why fail-closed on empty / malformed (mirroring iter 8's empty-
evidence rejection): a task with zero changed cells has no observed
output colours, so the accumulated inverse dict is empty. An empty
inverse mapping is properly handled by iter 13 (identity), not by
misreporting this one. Iter 8 takes the same posture
(``if not color_map: return False``).

Why strict-type-gate on per-group colour lists (mirroring iter 330's
strict 0..9 int gate on change-cell colours): per-group fields are
extracted from change-cell positions and should be in [0, 9]; bools
are an int subclass and must be rejected to keep the recognition
layer from accepting placeholder sentinels.

Params:
  (none) -- pure inverse-function-shape check on the accumulated
  changed-cell colour mapping.

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis's ``groups`` field is a list, AND
  - every group is a dict, AND
  - every group has ``input_colors`` and ``output_colors`` that are
    non-empty lists of strict 0..9 ints (no bools, no out-of-range),
    AND
  - the accumulated ``output_color -> set(input_colors)`` relation
    across all change groups of all pairs is NON-EMPTY (empty-
    evidence rejection -- iter 8 posture), AND
  - every observed output colour maps from EXACTLY ONE input colour
    across the union of all pairs' groups.

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
    strict 0..9 ints (mirrors iter 330's strict-type posture; a change
    group with zero colours on either side is upstream breakage)."""
    if not isinstance(x, list) or len(x) < 1:
        return False
    for v in x:
        if not _is_strict_color(v):
            return False
    return True


@register("inverse_consistent_color_mapping")
def match(patterns: dict, params: dict) -> bool:
    if not isinstance(patterns, dict):
        return False
    pair_analyses = patterns.get("pair_analyses")
    if not isinstance(pair_analyses, list) or not pair_analyses:
        return False

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
                    inverse.setdefault(oc, set()).add(ic)

    if not inverse:
        return False
    return all(len(v) == 1 for v in inverse.values())
