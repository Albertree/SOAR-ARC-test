"""
input_palette_constant_across_pairs -- match tasks where every example
pair has the SAME set of distinct input-grid colours.

Recognition vocabulary axis: the palette-axis dual of
``input_dimensions_constant`` (iter 22). Where iter 22 names the
precondition under which the test input's *dimensions* are pinned by
training (every training pair shares the same ``(input_height,
input_width)``), this matcher names the precondition under which the
test input's *palette* is pinned by training (every training pair
shares the same ``set(input_palette)``). Together they cover the two
foundational input-side cross-pair-constancy preconditions on the
``(dimensional, palette)`` quadrant of the input axis.

Why a separate matcher rather than parameterising an existing one:

  * The matcher contract (``docs/RULE_FORMAT.md`` §4) is name-keyed
    recognition vocabulary; the rule's stored ``condition.type`` is
    the recognition handle's name, not a name+params tuple. The
    iter 22 / 20 / 17 dimensional axis, the iter 184/185/186/187/188/
    189/190 palette set-relation axis, and the iter 191/195 palette
    -size-equality axis all live as separate named slots — each cell
    deserves its own handle. The cross-pair-constant-input-palette
    cell has had no named handle since iter 184 introduced the
    ``input_palette`` field; this matcher names it.

  * Existing ``constant_across_pairs`` matchers all target derived
    aggregates (intersection size, union size, symmetric-difference
    size, shift offset). None of them assert SET equality of the
    raw whole-grid input palette across pairs. The intersection-count
    matcher is the closest neighbour; it co-fires whenever this
    matcher fires (a constant palette has constant intersection
    cardinality), but the converse fails: two pairs with palettes
    {0,1,2} and {0,1,3} share intersection count 3 yet have
    different palettes — iter ``palette_intersection_count_constant_
    across_pairs`` would fire, this matcher rejects.

Why this matters for ARBOR's intended ruleset:

  * Palette-coded tasks where the input always uses a fixed colour
    vocabulary (e.g. "0 background, 1 frame, 2 highlight" across all
    pairs) need a recognition gate that distinguishes them from
    tasks whose colour vocabulary varies per pair. A future emission
    branch that stores a fixed-vocabulary substitution table as
    ``action.args`` needs this precondition to safely generalise.

  * For an abstract rule whose ``action`` references a literal colour
    constant from training (e.g. ``coloring(..., color=K)`` where K
    is one of the input palette colours), this matcher is the
    minimal precondition under which K is even meaningful for the
    test input.

  * Co-firing with ``input_dimensions_constant`` (iter 22) is the
    symmetric "all training inputs are isomorphic in size and
    colour vocabulary" gate — the tightest input-side stability
    a recognition rule can declare before lifting via
    anti-unification. The conjunction is currently emission-less but
    is the right precondition stack for future input-anchored rules.

Mutual containment / co-fire table (universal-over-pairs semantics):

  * ``identity_transformation`` (iter 13) — zero changes per pair AND
    every pair's ``size_match: True``. Identity has output palette
    equal to input palette per pair, but says nothing about whether
    input palettes match ACROSS pairs. INDEPENDENT: an identity task
    can have ``[0,1]`` in pair 0 and ``[2,3]`` in pair 1 (each pair
    is internally identity) and this matcher rejects.

  * ``input_dimensions_constant`` (iter 22) — same-axis dual on the
    dimensional concern. INDEPENDENT: a task can have constant input
    dimensions with varying input palettes (a 3x3 task where pair 0
    uses {0,1} and pair 1 uses {2,3}), or varying input dimensions
    with constant input palette (a square-then-rectangular task
    that uses only ``{0, 1}`` on both shapes). They co-fire on the
    tightest input-side stability gate.

  * ``output_palette_equals_input`` (iter 185) — per-pair set equality
    INPUT==OUTPUT, not cross-pair input==input. INDEPENDENT: a task
    can fire iter 185 (each pair preserves palette) with varying
    palettes across pairs (pair 0 ``{0,1}``, pair 1 ``{2,3}``,
    each preserved) — iter 185 fires per-pair, this matcher
    rejects on the cross-pair varying palette.

  * ``palette_intersection_count_constant_across_pairs`` — a constant
    palette gives constant intersection cardinality (the intersection
    is the palette itself, which is constant). STRICT IMPLICATION:
    this matcher ⇒ that matcher. Converse fails on two pairs with
    palettes ``{0,1,2}`` and ``{0,1,3}`` (intersection count 2 in
    both — wait, intersection of {0,1,2} and {0,1,3} is {0,1}, size
    2; for "across pairs" the matcher checks per-pair input∩output
    intersection size constancy, which is per-pair not cross-pair —
    confirming the two matchers are on different axes and the
    implication direction depends on the intersection target).

  * ``palette_shift_constant_across_pairs`` — a constant shift offset
    across pairs. INDEPENDENT: a constant input palette can have any
    shift (or no defined shift); a constant shift can hold over
    varying palettes.

Params:
  (none) -- the detected palette set is data carried in a future
  rule's stored args, not in ``condition.params``. The matcher is a
  pure existence/uniqueness check on the input-palette axis.

Returns True iff:
  - ``patterns`` is a dict, AND
  - ``patterns["pair_analyses"]`` is a non-empty list, AND
  - every analysis is a dict, AND
  - every analysis has an ``input_palette`` value that is a list of
    non-bool ints, AND
  - all ``set(input_palette)`` across analyses are bit-identical
    (compared as frozensets so internal list order does not affect
    the verdict — though ``_analyze_pair`` already emits the list
    sorted, this matcher does not rely on that for its verdict).

Why strict-list-of-non-bool-ints: Python bools are an ``int``
subclass; the iter-184..190 palette matchers all reject them to keep
the recognition layer from accepting placeholder sentinels.

Why fail-closed on empty / missing: the matcher's contract is
``deterministic and side-effect-free``; a missing ``input_palette``
is upstream extractor breakage (iter 184 added the field). Universal-
over-pairs with a vacuously-true empty case would let an empty
patterns dict fire the gate, which is the wrong default.

Empty-palette degenerate case: a pair with an empty input palette
(zero-area input grid) carries the empty set; multiple pairs with
empty inputs all share that set and this matcher fires. The upstream
extractor is responsible for non-zero-area inputs.

No companion-touch required: iter 184 already emits ``input_palette``
from ``_analyze_pair``. F8 inert (no ``agent/active_operators.py``
diff in this iter).
"""

from __future__ import annotations

from agent.conditions import register


def _is_palette_list(x) -> bool:
    """A palette field must be a list of non-bool ints. Empty is
    admissible at the type level (the cross-pair equality check
    handles the degenerate ``all-empty`` case)."""
    if not isinstance(x, list):
        return False
    for v in x:
        if not isinstance(v, int) or isinstance(v, bool):
            return False
    return True


@register("input_palette_constant_across_pairs")
def match(patterns: dict, params: dict) -> bool:
    if not isinstance(patterns, dict):
        return False
    pair_analyses = patterns.get("pair_analyses")
    if not isinstance(pair_analyses, list) or not pair_analyses:
        return False

    observed: frozenset | None = None
    for analysis in pair_analyses:
        if not isinstance(analysis, dict):
            return False
        ip = analysis.get("input_palette")
        if not _is_palette_list(ip):
            return False
        current = frozenset(ip)
        if observed is None:
            observed = current
        elif observed != current:
            return False
    return observed is not None
