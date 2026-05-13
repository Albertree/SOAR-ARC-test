"""
sequential_recoloring — match tasks where each example pair's changed-cell
groups are recoloured such that, when sorted by some position key (top
row or top column), the resulting output colours form a contiguous
integer sequence.

This is the recognition counterpart to the pipeline's `_try_recolor_sequential`
strategy in `agent/active_operators.py`: that detector returns a rule iff
every group has one input colour and one output colour AND the per-pair
output-colour multiset is a contiguous range AND at least one of
`top_row` / `top_col` produces the sequence when groups are sorted by it.
The matcher surfaces that same precondition as a named entry in the
condition registry, so once anti-unification produces a `coloring`-based
composition that encodes such a remap, the resulting §1-schema rule can
declare ``condition.type = "sequential_recoloring"``.

Distinct from `consistent_color_mapping` (iter 8):
  * `consistent_color_mapping` asserts each input colour has a unique
    output colour across all pairs — the mapping is functional but the
    output colours can be arbitrary and unordered.
  * `sequential_recoloring` asserts the per-pair output colours form a
    contiguous integer range AND admit a position-based ordering. It is
    stricter and not implied by `consistent_color_mapping`.

Distinct from `grid_size_preserved` (iter 1):
  * `grid_size_preserved` is a dimensional precondition only.
  * Sequential recolouring is colour/position content, dimension-agnostic
    by design — mirrors iter 8's deliberate separation of concerns. A
    future composite matcher or rule-layer conjunction can fuse the two
    if a single `condition.type` ever needs to assert both.

Params:
  (none) — the detected start_color, source_colors, and sort_key are
  data carried in `action.args` of the resulting rule, not in
  `condition.params`. The matcher is a pure existence/uniqueness check.

Returns True iff:
  - `patterns["pair_analyses"]` is a non-empty list, AND
  - every pair has the same number of change groups (> 0), AND
  - every group has exactly one input colour and one output colour, AND
  - per pair, the set of output colours is a contiguous integer range
    ``[c, c + n - 1]`` for some ``c``, AND
  - at least one of the sort keys ``top_row`` / ``top_col`` produces that
    range in order when groups are sorted by it (per pair).

Empty changed-cell sets (zero groups on any pair) return False — there
is no sequence to recognise. A pair with a single group also returns
False from the sort-key check unless the trivial 1-element range is
treated as a valid sequence; we follow `_try_recolor_sequential`'s
behaviour, which accepts a 1-group pair (a 1-element range is trivially
contiguous).
"""

from __future__ import annotations

from agent.conditions import register


def _is_contiguous_int_range(values) -> bool:
    """True iff ``values`` is a list/tuple of ints forming
    ``[c, c+1, ..., c+n-1]`` for some integer ``c``. Order-sensitive."""
    if not values:
        return False
    try:
        ints = [int(v) for v in values]
    except (TypeError, ValueError):
        return False
    return ints == list(range(ints[0], ints[0] + len(ints)))


def _sorted_outputs_form_range(groups, sort_key: str) -> bool:
    """Per-pair check: sort ``groups`` by ``sort_key`` and verify the
    extracted output colours form a contiguous integer range."""
    try:
        sorted_groups = sorted(groups, key=lambda g: g[sort_key])
    except (TypeError, KeyError):
        return False
    out_colours = []
    for g in sorted_groups:
        ocs = g.get("output_colors") or []
        if len(ocs) != 1:
            return False
        out_colours.append(ocs[0])
    return _is_contiguous_int_range(out_colours)


@register("sequential_recoloring")
def match(patterns: dict, params: dict) -> bool:
    if not isinstance(patterns, dict):
        return False
    pair_analyses = patterns.get("pair_analyses") or []
    if not pair_analyses:
        return False

    # Per-pair structural checks: same group count > 0 across pairs;
    # every group has exactly one input and one output colour.
    group_counts: list = []
    for analysis in pair_analyses:
        if not isinstance(analysis, dict):
            return False
        groups = analysis.get("groups") or []
        if not groups:
            return False
        group_counts.append(len(groups))
        for g in groups:
            if not isinstance(g, dict):
                return False
            input_colors = g.get("input_colors") or []
            output_colors = g.get("output_colors") or []
            if len(input_colors) != 1 or len(output_colors) != 1:
                return False

    if len(set(group_counts)) != 1:
        return False

    # The pipeline's strategy also requires that *some* sort key (top_row
    # or top_col) produces the sequence across every pair simultaneously.
    # Replicate that by checking the keys consistently per pair: at least
    # one sort key must work for *every* pair.
    for sort_key in ("top_row", "top_col"):
        if all(
            _sorted_outputs_form_range(a.get("groups") or [], sort_key)
            for a in pair_analyses
        ):
            return True
    return False
