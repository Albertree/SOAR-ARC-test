"""
output_dimensions_multiple_of_input -- match tasks where every example
pair's output grid is an *integer multiple* of its input grid on both
axes, and the (k_h, k_w) scale factor is bit-identical across every
pair.

Recognition vocabulary axis: ``relational-dimensional`` (cross-pair
constancy of the output-vs-input scale ratio, on the integer-multiple
sub-spectrum). The iter-1 / 17 / 20 / 22 dimensional axes named the
ABSOLUTE-dimensional properties of a patterns dict ("input == output
per pair" / "at least one pair changed size" / "output dims constant
across pairs" / "input dims constant across pairs"); none of them
names the *relational* property "output is a fixed-integer scale of
input". Two tile-style tasks with different input sizes
(e.g. 2x2 -> 6x6 and 3x3 -> 9x9, both with scale factor 3) fire
``grid_size_changed`` (iter 17) but fail every cross-pair constancy
matcher on the absolute axis (``input_dimensions_constant``,
``output_dimensions_constant``) because the input AND output
dimensions differ across pairs. The scale RATIO is constant in this
case (3 on both axes); naming that precondition as recognition
vocabulary is the smallest defensible step on a NEW axis.

Why this matters for the schema:

  * The two probe tasks ``00576224`` (2x2 -> 6x6) and ``007bbfb7``
    (3x3 -> 9x9) fire this matcher with (k_h, k_w) = (3, 3) but do
    NOT fire ``input_dimensions_constant`` (iter 22 requires the
    same input dims on every pair) NOR
    ``output_dimensions_constant`` (iter 20 requires the same
    output dims on every pair). Without a relational-dimensional
    matcher, tile/scale tasks have no named recognition handle even
    though they are the simplest class of dimension-changing
    transforms.
  * A future emission iter that targets tile/scale rules (where the
    action is a *composition* of ``make_grid(k_h * in_h, k_w * in_w,
    background)`` and ``coloring`` over a derived selection -- the
    canonical bottom-up discovery target for the second hand-coded
    primitive) needs a recognition precondition that names "the
    scale factor is determinable from training data". This matcher
    provides that precondition. Recognition vocabulary ahead of
    rule emission, the iter
    1/8/10/13/17/18/19/20/22/23/24/26/28/30/32 pattern.
  * Per-attempt ``fired_conditions`` (written to
    ``episodic_memory/<task>/attempt_NNN/metadata.json`` since iter
    12) gains a directly inspectable signal for "this task's
    output-vs-input scale ratio is pinned across pairs" -- one more
    named axis the instrumentation surfaces without needing a
    translate_to_schema branch to consume it.

The relational-dimensional axis is orthogonal to:

  * The absolute-dimensional cross-pair constancy axis
    (``input_dimensions_constant``, ``output_dimensions_constant``)
    -- those inspect whether the input/output dims are themselves
    constant; this matcher inspects whether their RATIO is constant.
    Independent: a task can fire both (e.g. constant 3x3 inputs all
    scaled to constant 9x9 outputs -- (k_h, k_w) = (3, 3) constant,
    inputs and outputs both constant), this matcher alone
    (tile-style 2x2 -> 6x6 and 3x3 -> 9x9; constant ratio, varying
    inputs AND varying outputs), the absolute matchers alone
    (constant 3x3 inputs and constant 9x9 outputs with no integer-
    multiple relation -- impossible in this case because 9 is a
    multiple of 3; but in general the integer-multiple gate can
    fail while inputs and outputs are individually constant, e.g.
    constant 3x3 inputs all paired with constant 4x4 outputs, where
    4 % 3 != 0), OR neither (varying dims with no ratio
    relationship). The four-cell Venn diagram is non-degenerate.
  * The per-pair dimensional axis (``grid_size_preserved``,
    ``grid_size_changed``):
      - ``grid_size_preserved`` is the (k_h, k_w) == (1, 1) special
        case on the relational axis. When this matcher fires with
        (k_h, k_w) = (1, 1) (every pair's output dims equal its
        input dims), ``grid_size_preserved`` ALSO fires. This
        matcher explicitly EXCLUDES the (1, 1) case (see fail-
        closed clause below) to keep its territory disjoint from
        iter 1's identity-shape regime; ``grid_size_preserved`` is
        the canonical recognition handle there.
      - ``grid_size_changed`` is a weaker pre-precondition: it
        requires at least one pair to be dimension-changed; this
        matcher requires *every* pair to be dimension-changed (no
        non-trivial scale of (1, 1) preserves dims). When this
        matcher fires with (k_h, k_w) != (1, 1),
        ``grid_size_changed`` ALSO fires (every pair has
        in_dim != out_dim). The converse does NOT hold -- a task
        with mixed dim-changes that are not all the same integer
        scale (e.g. pair 0 of 2x2 -> 6x6, pair 1 of 2x2 -> 4x4)
        fires ``grid_size_changed`` but not this matcher.
  * The colour-content axis (``output_color_uniform`` /
    ``input_color_uniform`` / ``consistent_color_mapping`` /
    ``sequential_recoloring``) -- those inspect change-group colour
    structure, not grid shape. Orthogonal.
  * The group-count axis (``identity_transformation`` /
    ``single_change_group_per_pair`` / ``multi_group_per_pair``) --
    those inspect ``num_groups``, not grid shape. Orthogonal.
  * The cell-count sub-axis (``single_cell_change_per_pair`` /
    ``multi_cell_change_group_per_pair``) -- those inspect
    per-group ``cell_count`` under ``num_groups == 1``, not grid
    shape. Orthogonal.
  * The position-content axis
    (``change_positions_constant_across_pairs``) -- inspects coord
    SET equality, not grid shape. Orthogonal.
  * The cardinality axis
    (``change_count_constant_across_pairs``) -- inspects coord
    COUNT equality, not grid shape. Orthogonal.

Relation to existing dimensional matchers (mutual-exclusion /
refinement table):

  * ``grid_size_preserved`` (iter 1) -- when every pair has
    ``size_match`` True (in_dim == out_dim), the implied scale is
    (1, 1). This matcher EXPLICITLY REJECTS (1, 1) to keep its
    territory disjoint from the iter-1 regime. STRICTLY mutually
    exclusive: no patterns dict can fire both. (Identity tasks fire
    iter 1 + iter 13; tile tasks fire this matcher + iter 17.)
  * ``grid_size_changed`` (iter 17) -- weaker pre-precondition;
    this matcher implies it (when (k_h, k_w) != (1, 1) on EVERY
    pair, every pair has dimension change). CAN co-fire by
    construction. The converse does NOT hold: a task with mixed
    or non-integer dimension changes fires iter 17 but not this
    matcher.
  * ``output_dimensions_constant`` (iter 20) -- inspects whether
    output dims are constant across pairs; orthogonal to the scale
    ratio. CAN co-fire (constant-output tile task) or independently.
  * ``input_dimensions_constant`` (iter 22) -- inspects whether
    input dims are constant across pairs; orthogonal to the scale
    ratio. CAN co-fire (constant-input tile task) or independently.
    The interesting tile-style territory this matcher names
    EXCLUSIVELY is when inputs AND outputs both vary across pairs
    but their ratio is constant.
  * ``identity_transformation`` (iter 13) -- requires every pair's
    ``num_groups == 0`` AND every pair's ``size_match`` True
    (in_dim == out_dim). The dimensional precondition is (1, 1)
    scale, which this matcher REJECTS. STRICTLY mutually exclusive.

Params:
  (none) -- the matcher inspects
  ``patterns["pair_analyses"][i]["input_height"]``,
  ``["input_width"]``, ``["output_height"]``, and ``["output_width"]``
  -- the strict-positive-int per-pair dimensions emitted by
  ``_analyze_pair`` since iter 19. No reliance on ``size_match`` (a
  derived flag) -- the matcher reads the four scalar fields directly,
  mirroring iter 20 and iter 22's same posture.

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis carries strict-positive-int ``input_height``,
    ``input_width``, ``output_height``, ``output_width`` (bool
    rejected per ``validate_rule`` V1 posture, ``>= 1``), AND
  - for every analysis: ``output_height`` is a positive integer
    multiple of ``input_height`` AND ``output_width`` is a positive
    integer multiple of ``input_width`` (i.e.
    ``output_height % input_height == 0`` and the quotient is at
    least 1), AND
  - the per-pair scale ratio ``(k_h, k_w) = (output_height //
    input_height, output_width // input_width)`` is bit-identical
    across every pair, AND
  - the constant ratio is NOT (1, 1) -- the identity-shape case
    handled by ``grid_size_preserved``.

Why fail-closed on (k_h, k_w) == (1, 1): the (1, 1) case is the
identity-shape regime where every pair has ``size_match`` True. That
territory is named by ``grid_size_preserved`` (iter 1) and -- in the
zero-changes sub-case -- ``identity_transformation`` (iter 13).
Letting this matcher cover (1, 1) would double-cover those regimes
under a name that promises "the scale factor is non-trivial". The
strict refusal mirrors iter 30's empty-union rejection on the
position axis, iter 32's per-pair-total-zero rejection on the
cardinality axis, and iter 18 / 19's zero-group rejection on the
colour axis -- the matcher names a NON-TRIVIAL precondition.

Why strict positive-int (not bool, ``>= 1``): a missing or
non-positive grid dimension is upstream extractor breakage, not
evidence that the scale ratio is constant. Strict comparison
forecloses ``input_height = True`` (Python bool-is-int subclass) and
``input_height = 0`` (degenerate empty grid) false positives. The
bool-rejection is the same posture as
``agent/memory.py:validate_rule`` on integer fields (V1 explicitly
rejects ``isinstance(x, bool)``).

Why fail-closed on non-integer multiples: a task with output dims
that are not integer multiples of input dims (e.g. 3x3 -> 4x4) is
NOT a tile/scale pattern; the integer-multiple gate is the
defining property of the relational-dimensional axis this matcher
names. The fail-closed posture mirrors the iter-30 / 32 strict
rejection of cases that would dilute the matcher's territory.

Why per-pair ``input_height`` / ``input_width`` / ``output_height``
/ ``output_width`` rather than ``size_match``: same rationale as
iters 17 / 20 / 22 -- matchers should not piggyback on derived
top-level flags; reading from the per-pair fields keeps the
recognition layer's contract on the shape ``_analyze_pair`` emits,
not on a summary the slow path may forget to compute.

Why a self-contained predicate rather than a composition of
``grid_size_changed`` + a quotient check: matchers are independent
predicates in the registry (``docs/RULE_FORMAT.md`` section 4).
Composing them at use-site (via ``recognized_conditions`` and a
conjunction of names in a future composite-precondition step) is
the canonical pattern; inlining a per-pair ``size_match`` check
here would couple registry entries in a non-introspectable way.
The matcher implements its quotient check explicitly so
``CONDITION_REGISTRY["output_dimensions_multiple_of_input"]`` is
a single self-contained predicate, the same shape as every other
matcher.

No ``_analyze_pair`` change this iter: the per-pair dimension
fields have been emitted since iter 19 -- iter 33 is matcher-only
addition that uses an existing patterns-dict field on a new axis.
The companion-touch question under F8 is therefore inert -- this
iter has no ``agent/active_operators.py`` change at all.
"""

from __future__ import annotations

from agent.conditions import register


def _is_strict_positive_int(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool) and x >= 1


@register("output_dimensions_multiple_of_input")
def match(patterns: dict, params: dict) -> bool:
    if not isinstance(patterns, dict):
        return False
    pair_analyses = patterns.get("pair_analyses")
    if not isinstance(pair_analyses, list) or not pair_analyses:
        return False

    canonical_ratio: tuple[int, int] | None = None

    for analysis in pair_analyses:
        if not isinstance(analysis, dict):
            return False
        ih = analysis.get("input_height")
        iw = analysis.get("input_width")
        oh = analysis.get("output_height")
        ow = analysis.get("output_width")
        if not _is_strict_positive_int(ih):
            return False
        if not _is_strict_positive_int(iw):
            return False
        if not _is_strict_positive_int(oh):
            return False
        if not _is_strict_positive_int(ow):
            return False
        if oh % ih != 0:
            return False
        if ow % iw != 0:
            return False
        k_h = oh // ih
        k_w = ow // iw
        if k_h < 1 or k_w < 1:
            return False
        ratio = (k_h, k_w)
        if canonical_ratio is None:
            canonical_ratio = ratio
        elif canonical_ratio != ratio:
            return False

    if canonical_ratio is None:
        return False
    if canonical_ratio == (1, 1):
        return False
    return True
