"""
input_output_dimensions_and_palette_equal_and_constant_across_pairs --
match tasks where there exists a single ``(H, W)`` tuple AND a single
colour set S such that EVERY training pair's input grid AND output grid
both have exactly those dimensions AND exactly that palette.

Recognition vocabulary axis: the conjunction-of-conjunctions handle
named in iter 992's "Next gap" log as candidate (a). It is the
conjunction of:

  * iter 991 ``input_output_palette_equal_and_constant_across_pairs``
    -- a single colour set S such that every pair's input AND output
    palette equals S.
  * iter 992 ``input_output_dimensions_equal_and_constant_across_pairs``
    -- a single ``(H, W)`` such that every pair's input AND output
    dimensions equal ``(H, W)``.

The two together pin a single shared ``(H, W, S)`` triple across the
entire task -- the strongest known cross-pair stability gate the
recognition vocabulary currently offers. Equivalently: every grid in
the task (every input grid AND every output grid of every training
pair) has the same shape ``(H, W)`` AND the same colour vocabulary S.

Why a separate conjunction-of-conjunctions matcher rather than
re-running two:

  * The matcher contract (``docs/RULE_FORMAT.md`` section 4) is
    name-keyed recognition vocabulary; a future ``translate_to_schema``
    emission branch (``agent/memory.py``) that needs the "shape AND
    colour vocabulary both task-invariant" precondition would
    otherwise have to encode the two-way AND inline in every gate.
    Naming the conjunction as a single registry entry lets the
    emission branch read a single ``condition.type`` and lets stored
    rules carry the tightest single-name precondition rather than a
    two-name conjunction the schema currently has no syntax to express
    (rule schema section 1 stores a single ``condition.type`` string).

  * This is the same conjunction-handle pattern iter 991 used to name
    the three-way palette conjunction, iter 992 used to name the
    three-way dimensions conjunction, and iter 333 used when naming
    ``bijective_color_mapping`` as the conjunction of iter 8 AND iter
    332. The conjunction has new semantic content -- "a single shape
    AND a single colour vocabulary together hold across every grid"
    -- that neither named conjunct asserts on its own (iter 991
    permits shape to vary across pairs; iter 992 permits palette to
    vary across pairs). Only the conjunction names the tightest
    single-name precondition under which a rule's stored coord-and-
    colour-literal args (e.g. ``coloring(selection=[(r0, c0)],
    color=K)``) are guaranteed both in-bounds AND in-vocabulary for
    the test input AND output.

Why this matters for ARBOR's intended ruleset:

  * Coord-and-colour-literal rules (the frozen ``coloring`` DSL
    primitive with literal coord lists AND literal colour) need a
    recognition gate that proves the rule's stored coords are valid
    for both the input and output grid of every training pair AND of
    any test input that satisfies the same gate AND that the rule's
    stored colour belongs to the shared vocabulary of every such
    grid. The two named conjuncts together provide that proof; any
    one alone would over-fire on tasks where the other axis varies.

  * Anti-unification across two pair-specific coord-and-colour-literal
    programs needs a recognition handle to gate the lifted rule on
    exactly the precondition that justifies it. The conjunction-of-
    conjunctions handle is the tightest single name for "(H, W, S)
    is task-invariant", which is the weakest precondition under
    which an abstract coord-and-colour-literal rule lifts safely.

  * For future emission branches in ``translate_to_schema``, the
    gate ``"input_output_dimensions_and_palette_equal_and_constant_across_pairs" in fired``
    is strictly tighter than either individual conjunction-handle
    (and the two-of-two conjunction inlined into a branch would be
    more fragile than a single name).

Mutual containment / co-fire table:

  * ``input_output_dimensions_equal_and_constant_across_pairs``
    (iter 992) -- strictly implied. The conjunction firing means
    every grid's dimensions equal a single ``(H, W)``, which is
    iter 992's claim. The converse does NOT hold: iter 992 fires on
    tasks with fixed shape but varying palette.

  * ``input_output_palette_equal_and_constant_across_pairs``
    (iter 991) -- strictly implied. Same logic on the palette axis.

  * Six-way transitive implication: this matcher strictly implies
    iter 1 (``grid_size_preserved``), iter 20
    (``output_dimensions_constant``), iter 22
    (``input_dimensions_constant``), iter 185
    (``output_palette_equals_input``), iter 989
    (``input_palette_constant_across_pairs``), and iter 990
    (``output_palette_constant_across_pairs``). Each of those six
    is in turn implied by either iter 991 or iter 992, both of which
    this matcher implies.

  * ``identity_transformation`` (iter 13) -- INDEPENDENT. Identity
    says every pair internally preserves; says nothing about cross-
    pair shape or palette equality. (a) Identity fires on per-pair
    varying shape (pair 0 identity on 3x3, pair 1 identity on 5x5)
    while this matcher rejects on cross-pair variation. (b) This
    matcher fires on per-pair-non-identity (a same-shape recolour
    on a fixed palette -- both grids share ``(H, W, S)`` but inner
    contents differ).

  * ``grid_size_changed`` (iter 17) -- MUTUALLY EXCLUSIVE on the
    dimensional half (inherited from iter 992's mutual exclusion).
    If any pair has size_match False, iter 992 rejects, so this
    matcher rejects; if every pair has size_match True, iter 17
    rejects.

  * ``output_palette_is_permutation_of_input_palette`` -- co-fires
    on permutation-on-fixed-palette tasks where shape is also
    constant (this matcher fires AND permutation fires); the
    permutation matcher fires on tasks with per-pair palette
    equality but cross-pair variation in either palette or shape
    (this matcher rejects those).

Params:
  (none) -- pure existence/uniqueness check on the conjunction of
  the two named conjunction-handles. Future params (e.g.
  min_dimension, min_palette_size) are deliberately deferred until
  an emission branch needs them.

Returns True iff:
  - ``input_output_dimensions_equal_and_constant_across_pairs``
    fires on ``patterns`` (which requires non-empty pair_analyses,
    each entry a dict with strict-positive-int dim fields, per-pair
    input-equals-output dims, and cross-pair dim constancy), AND
  - ``input_output_palette_equal_and_constant_across_pairs``
    fires on ``patterns`` (which requires the same fail-closed
    posture on palette fields and per-pair / cross-pair palette
    set equality).

Why dispatch to the two named conjuncts rather than re-derive: the
matcher's contract is name-keyed recognition vocabulary; the named
conjuncts ARE the named pieces of vocabulary. Re-deriving the
dimensional and palette checks inline would duplicate iter 991 / 992
implementation detail and could drift from those matchers' contracts
over time. Dispatch keeps the conjunction-of-conjunctions a true
conjunction in code, not just in intent. The dispatch is read-only
(matchers are deterministic and side-effect-free per docs/RULE_FORMAT.md
section 4), so the composition preserves all the fail-closed posture
the named conjuncts already enforce.

Why fail-closed on missing fields: inherited transitively from the
named conjuncts (which each fail closed on missing dim / palette
fields, non-list pair_analyses, empty pair_analyses, etc.).

No companion-touch required: iters 19 / 20 / 184 already emit
``input_height`` / ``input_width`` / ``output_height`` /
``output_width`` / ``input_palette`` / ``output_palette`` from
``_analyze_pair``. F8 inert (no ``agent/active_operators.py`` diff
in this iter).
"""

from __future__ import annotations

from agent.conditions import CONDITION_REGISTRY, register


_DIM_CONJUNCT = "input_output_dimensions_equal_and_constant_across_pairs"
_PAL_CONJUNCT = "input_output_palette_equal_and_constant_across_pairs"


@register("input_output_dimensions_and_palette_equal_and_constant_across_pairs")
def match(patterns: dict, params: dict) -> bool:
    dim_matcher = CONDITION_REGISTRY.get(_DIM_CONJUNCT)
    pal_matcher = CONDITION_REGISTRY.get(_PAL_CONJUNCT)
    if dim_matcher is None or pal_matcher is None:
        return False
    if dim_matcher(patterns, {}) is not True:
        return False
    if pal_matcher(patterns, {}) is not True:
        return False
    return True
