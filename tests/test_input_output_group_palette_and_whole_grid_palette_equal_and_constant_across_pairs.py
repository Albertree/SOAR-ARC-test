"""
tests/test_input_output_group_palette_and_whole_grid_palette_equal_and_constant_across_pairs.py
-- exercise the iter-997 matcher
``agent.conditions.input_output_group_palette_and_whole_grid_palette_equal_and_constant_across_pairs``
(new in this iter).

Pins the matcher's contract per the docstring of
``agent/conditions/input_output_group_palette_and_whole_grid_palette_equal_and_constant_across_pairs.py``:
the conjunction of iter 991's
``input_output_palette_equal_and_constant_across_pairs`` AND iter 996's
``input_output_group_palette_equal_and_constant_across_pairs``. Fires
iff both named conjuncts fire on the patterns dict.

This is the within-axis (palette only) per-group AND whole-grid
conjunction analogue of iter 993's between-axis (dimension AND palette)
whole-grid conjunction. The discriminating-axis tests verify that the
matcher fires iff both of those fire on a non-empty pair_analyses list.

Runs without pytest:

    python tests/test_input_output_group_palette_and_whole_grid_palette_equal_and_constant_across_pairs.py

Dependency-free, same runner style as the other tests under ``tests/``.
"""

from __future__ import annotations

import copy
import os
import sys
import traceback

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from agent.conditions import CONDITION_REGISTRY  # noqa: E402


MATCHER_NAME = (
    "input_output_group_palette_and_whole_grid_palette_equal_and_constant_across_pairs"
)
WHOLE_GRID_CONJUNCT = "input_output_palette_equal_and_constant_across_pairs"
PER_GROUP_CONJUNCT = "input_output_group_palette_equal_and_constant_across_pairs"


def _matcher():
    return CONDITION_REGISTRY[MATCHER_NAME]


def _group(palette, **overrides):
    """A group_analysis shaped like ``_analyze_pair``'s emit (iter-1
    schema), defaulting input_colors == output_colors == palette."""
    base = {
        "input_colors": list(palette),
        "output_colors": list(palette),
        "top_row": 0,
        "top_col": 0,
        "cell_count": max(len(palette), 1),
        "positions": [(0, 0)],
    }
    base.update(overrides)
    return base


def _pair(groups, input_palette=None, output_palette=None, **overrides):
    """A pair_analysis with the supplied ``groups`` list AND the iter-184
    whole-grid palette fields. Defaults to whole-grid input/output
    palettes mirroring the per-blob palette so iter 991 fires alongside
    iter 996 unless explicitly overridden."""
    if groups and input_palette is None:
        # Default whole-grid palette to a superset of all per-blob inputs.
        union = set()
        for g in groups:
            union.update(g.get("input_colors", []))
        input_palette = sorted(union) if union else [0]
    elif input_palette is None:
        input_palette = [0, 1]
    if output_palette is None:
        output_palette = list(input_palette)
    total_changes = sum(g.get("cell_count", 1) for g in groups)
    base = {
        "input_height": 3,
        "input_width": 3,
        "output_height": 3,
        "output_width": 3,
        "size_match": True,
        "total_changes": total_changes,
        "num_groups": len(groups),
        "groups": list(groups),
        "input_palette": list(input_palette),
        "output_palette": list(output_palette),
    }
    base.update(overrides)
    return base


# ──────────────────────────────────────────────────────────────────────────
# Smoke / membership.
# ──────────────────────────────────────────────────────────────────────────

def test_registered_in_global_registry() -> None:
    assert MATCHER_NAME in CONDITION_REGISTRY, (
        f"{MATCHER_NAME!r} not registered; got {sorted(CONDITION_REGISTRY)}"
    )


def test_matcher_is_callable() -> None:
    fn = _matcher()
    assert callable(fn), f"registered entry is not callable: {fn!r}"


def test_p5_at_least_91() -> None:
    # Iter-997 brings the registry to >= 91 (P5 monotone). The probe
    # baseline was P5 = 90 after iter 996.
    assert len(CONDITION_REGISTRY) >= 91, (
        f"expected >= 91 matchers post-iter-997; got {len(CONDITION_REGISTRY)}"
    )


def test_named_conjuncts_present() -> None:
    # The matcher dispatches to two named registry entries; if either is
    # missing the iter is mis-staged.
    assert WHOLE_GRID_CONJUNCT in CONDITION_REGISTRY, (
        f"missing iter-991 conjunct {WHOLE_GRID_CONJUNCT!r}"
    )
    assert PER_GROUP_CONJUNCT in CONDITION_REGISTRY, (
        f"missing iter-996 conjunct {PER_GROUP_CONJUNCT!r}"
    )


# ──────────────────────────────────────────────────────────────────────────
# Positive cases.
# ──────────────────────────────────────────────────────────────────────────

def test_single_pair_single_group_aligned_palettes_fires() -> None:
    # Per-blob input/output = whole-grid input/output = {0, 1}.
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1])], input_palette=[0, 1],
                  output_palette=[0, 1]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_two_pairs_aligned_palettes_fires() -> None:
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1])], input_palette=[0, 1],
                  output_palette=[0, 1]),
            _pair([_group([0, 1])], input_palette=[0, 1],
                  output_palette=[0, 1]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_per_blob_subset_of_whole_grid_fires() -> None:
    # Whole-grid palette = {0, 1, 2} constant on both sides across pairs;
    # per-blob palette = {0, 1} constant on both sides across blobs and
    # pairs. iter 991 fires (whole-grid stable), iter 996 fires (per-blob
    # stable). This matcher fires.
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1])], input_palette=[0, 1, 2],
                  output_palette=[0, 1, 2]),
            _pair([_group([0, 1])], input_palette=[0, 1, 2],
                  output_palette=[0, 1, 2]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_multiple_groups_same_palette_per_pair_fires() -> None:
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1]), _group([0, 1])],
                  input_palette=[0, 1, 2], output_palette=[0, 1, 2]),
            _pair([_group([0, 1])], input_palette=[0, 1, 2],
                  output_palette=[0, 1, 2]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_three_pairs_aligned_fires() -> None:
    patterns = {
        "pair_analyses": [
            _pair([_group([7, 8])], input_palette=[7, 8],
                  output_palette=[7, 8]),
            _pair([_group([7, 8])], input_palette=[7, 8],
                  output_palette=[7, 8]),
            _pair([_group([7, 8])], input_palette=[7, 8],
                  output_palette=[7, 8]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_set_equal_different_list_order_fires() -> None:
    # frozenset equality is order-insensitive on every conjunct.
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1, 2],
                          input_colors=[2, 0, 1],
                          output_colors=[1, 2, 0])],
                  input_palette=[1, 0, 2], output_palette=[2, 1, 0]),
            _pair([_group([0, 1, 2],
                          input_colors=[1, 0, 2],
                          output_colors=[0, 2, 1])],
                  input_palette=[0, 2, 1], output_palette=[1, 0, 2]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_singleton_palette_fires() -> None:
    patterns = {
        "pair_analyses": [
            _pair([_group([5])], input_palette=[5], output_palette=[5]),
            _pair([_group([5])], input_palette=[5], output_palette=[5]),
        ],
    }
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Negative cases (whole-grid conjunct fails -- iter 991 rejects).
# ──────────────────────────────────────────────────────────────────────────

def test_whole_grid_cross_pair_variation_rejects() -> None:
    # Per-blob palette is constant {0, 1} across pairs (iter 996 fires),
    # but whole-grid palette varies ({0, 1, 2} vs {0, 1, 3}) -- iter 991
    # rejects, so this matcher rejects.
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1])], input_palette=[0, 1, 2],
                  output_palette=[0, 1, 2]),
            _pair([_group([0, 1])], input_palette=[0, 1, 3],
                  output_palette=[0, 1, 3]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_whole_grid_per_pair_mismatch_rejects() -> None:
    # Per-blob palette constant; whole-grid input != whole-grid output
    # per pair (e.g. recolour of background) -- iter 991 rejects.
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1])], input_palette=[0, 1, 2],
                  output_palette=[0, 1, 3]),
            _pair([_group([0, 1])], input_palette=[0, 1, 2],
                  output_palette=[0, 1, 3]),
        ],
    }
    assert _matcher()(patterns, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Negative cases (per-group conjunct fails -- iter 996 rejects).
# ──────────────────────────────────────────────────────────────────────────

def test_per_group_cross_pair_variation_rejects() -> None:
    # Whole-grid palette = {0, 1, 2} constant on both sides across pairs
    # (iter 991 fires), but per-blob palette varies across pairs ({0, 1}
    # in pair 0, {1, 2} in pair 1) -- iter 996 rejects.
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1])], input_palette=[0, 1, 2],
                  output_palette=[0, 1, 2]),
            _pair([_group([1, 2])], input_palette=[0, 1, 2],
                  output_palette=[0, 1, 2]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_per_group_cross_side_mismatch_rejects() -> None:
    # Whole-grid palette constant on both sides; per-blob input != output
    # per group -- iter 996 rejects.
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1], output_colors=[2, 3])],
                  input_palette=[0, 1, 2, 3],
                  output_palette=[0, 1, 2, 3]),
            _pair([_group([0, 1], output_colors=[2, 3])],
                  input_palette=[0, 1, 2, 3],
                  output_palette=[0, 1, 2, 3]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_per_group_within_pair_mismatch_rejects() -> None:
    # Whole-grid constant; two groups in same pair have different per-
    # blob palettes -- iter 996 rejects.
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1]), _group([2, 3])],
                  input_palette=[0, 1, 2, 3],
                  output_palette=[0, 1, 2, 3]),
        ],
    }
    assert _matcher()(patterns, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Negative cases (both conjuncts fail).
# ──────────────────────────────────────────────────────────────────────────

def test_both_axes_violated_rejects() -> None:
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1])], input_palette=[0, 1, 2],
                  output_palette=[0, 1, 2]),
            _pair([_group([2, 3])], input_palette=[2, 3, 4],
                  output_palette=[2, 3, 4]),
        ],
    }
    assert _matcher()(patterns, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Fail-closed paths (inherited from named conjuncts).
# ──────────────────────────────────────────────────────────────────────────

def test_empty_pair_analyses_rejects() -> None:
    assert _matcher()({"pair_analyses": []}, {}) is False


def test_missing_pair_analyses_rejects() -> None:
    assert _matcher()({}, {}) is False


def test_non_list_pair_analyses_rejects() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (), True):
        assert _matcher()({"pair_analyses": bad}, {}) is False, (
            f"pair_analyses={bad!r} should not fire"
        )


def test_non_dict_patterns_rejects() -> None:
    for bad in (None, [], "oops", 42):
        assert _matcher()(bad, {}) is False, (  # type: ignore[arg-type]
            f"patterns={bad!r} should not fire"
        )


def test_non_dict_analysis_rejects() -> None:
    patterns = {
        "pair_analyses": [_pair([_group([0, 1])]), "not-a-dict"]
    }
    assert _matcher()(patterns, {}) is False


def test_empty_groups_list_rejects_identity_territory() -> None:
    # Iter 996 fails closed on zero-group pairs (identity-territory
    # rejection); this matcher inherits.
    patterns = {"pair_analyses": [_pair([])]}
    assert _matcher()(patterns, {}) is False


def test_one_pair_no_groups_rejects() -> None:
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1])]),
            _pair([]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_missing_palette_field_rejects() -> None:
    analysis = _pair([_group([0, 1])])
    del analysis["input_palette"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_missing_input_colors_in_group_rejects() -> None:
    g = _group([0, 1])
    del g["input_colors"]
    patterns = {"pair_analyses": [_pair([g])]}
    assert _matcher()(patterns, {}) is False


def test_missing_output_colors_in_group_rejects() -> None:
    g = _group([0, 1])
    del g["output_colors"]
    patterns = {"pair_analyses": [_pair([g])]}
    assert _matcher()(patterns, {}) is False


def test_bool_in_palette_rejects() -> None:
    analysis = _pair([_group([0, 1])])
    analysis["input_palette"] = [True, 0, 1]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_bool_in_group_colors_rejects() -> None:
    g = _group([0, 1])
    g["input_colors"] = [0, True]
    patterns = {"pair_analyses": [_pair([g])]}
    assert _matcher()(patterns, {}) is False


def test_out_of_range_color_in_group_rejects() -> None:
    g = _group([0, 1])
    g["input_colors"] = [0, 13]
    patterns = {"pair_analyses": [_pair([g])]}
    assert _matcher()(patterns, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Behavioural contract.
# ──────────────────────────────────────────────────────────────────────────

def test_side_effect_free() -> None:
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1])], input_palette=[0, 1],
                  output_palette=[0, 1]),
            _pair([_group([0, 1])], input_palette=[0, 1],
                  output_palette=[0, 1]),
        ],
    }
    params = {"unused": 1}
    before_p = copy.deepcopy(patterns)
    before_q = copy.deepcopy(params)
    _matcher()(patterns, params)
    assert patterns == before_p, "matcher mutated patterns"
    assert params == before_q, "matcher mutated params"


def test_deterministic_across_repeats() -> None:
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1])], input_palette=[0, 1],
                  output_palette=[0, 1]),
            _pair([_group([0, 1])], input_palette=[0, 1],
                  output_palette=[0, 1]),
        ],
    }
    results = [_matcher()(patterns, {}) for _ in range(5)]
    assert len(set(results)) == 1, f"non-deterministic: {results}"


def test_returns_literal_boolean() -> None:
    out_true = _matcher()(
        {"pair_analyses": [
            _pair([_group([0, 1])], input_palette=[0, 1],
                  output_palette=[0, 1])
        ]},
        {},
    )
    out_false = _matcher()(
        {"pair_analyses": [
            _pair([_group([0, 1])], input_palette=[0, 1],
                  output_palette=[0, 1]),
            _pair([_group([2, 3])], input_palette=[2, 3],
                  output_palette=[2, 3]),
        ]},
        {},
    )
    assert out_true is True, f"expected literal True, got {out_true!r}"
    assert out_false is False, f"expected literal False, got {out_false!r}"


def test_params_ignored() -> None:
    patterns = {"pair_analyses": [
        _pair([_group([0, 1])], input_palette=[0, 1],
              output_palette=[0, 1])
    ]}
    for params in ({}, {"x": 1}, {"min_palette_size": 100}, {"strict": False}):
        assert _matcher()(patterns, params) is True


# ──────────────────────────────────────────────────────────────────────────
# Conjunction relationships -- the two named conjuncts.
# ──────────────────────────────────────────────────────────────────────────

def test_fires_iff_both_named_conjuncts_fire() -> None:
    # Discriminating-axis test. The matcher must agree with the literal
    # conjunction of iter 991 and iter 996 on every cell of the
    # (whole-grid, per-group) 2x2 truth table the fixture vocabulary
    # realises.
    whole_grid_m = CONDITION_REGISTRY[WHOLE_GRID_CONJUNCT]
    per_group_m = CONDITION_REGISTRY[PER_GROUP_CONJUNCT]

    cases = [
        # (T, T) -- both fire: aligned per-blob and whole-grid palettes
        # constant across pairs.
        {
            "pair_analyses": [
                _pair([_group([0, 1])], input_palette=[0, 1, 2],
                      output_palette=[0, 1, 2]),
                _pair([_group([0, 1])], input_palette=[0, 1, 2],
                      output_palette=[0, 1, 2]),
            ],
        },
        # (T, F) -- whole-grid fires alone: whole-grid palette constant
        # but per-blob palette varies across pairs.
        {
            "pair_analyses": [
                _pair([_group([0, 1])], input_palette=[0, 1, 2],
                      output_palette=[0, 1, 2]),
                _pair([_group([1, 2])], input_palette=[0, 1, 2],
                      output_palette=[0, 1, 2]),
            ],
        },
        # (F, T) -- per-blob fires alone: per-blob palette constant but
        # whole-grid palette varies across pairs.
        {
            "pair_analyses": [
                _pair([_group([0, 1])], input_palette=[0, 1, 2],
                      output_palette=[0, 1, 2]),
                _pair([_group([0, 1])], input_palette=[0, 1, 3],
                      output_palette=[0, 1, 3]),
            ],
        },
        # (F, F) -- neither fires: both axes vary across pairs.
        {
            "pair_analyses": [
                _pair([_group([0, 1])], input_palette=[0, 1, 2],
                      output_palette=[0, 1, 2]),
                _pair([_group([2, 3])], input_palette=[2, 3, 4],
                      output_palette=[2, 3, 4]),
            ],
        },
    ]
    for p in cases:
        m = _matcher()(p, {})
        expected = (
            whole_grid_m(p, {}) is True and per_group_m(p, {}) is True
        )
        assert m is expected, (
            f"matcher disagrees with literal conjunction on {p!r}: "
            f"matcher={m!r}, expected={expected!r}"
        )


def test_strictly_implies_iter_991_conjunct() -> None:
    # When this matcher fires, iter 991's whole-grid conjunction-handle
    # must also fire.
    whole_grid_m = CONDITION_REGISTRY[WHOLE_GRID_CONJUNCT]
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1])], input_palette=[0, 1, 2],
                  output_palette=[0, 1, 2]),
            _pair([_group([0, 1])], input_palette=[0, 1, 2],
                  output_palette=[0, 1, 2]),
        ],
    }
    assert _matcher()(patterns, {}) is True
    assert whole_grid_m(patterns, {}) is True


def test_strictly_implies_iter_996_conjunct() -> None:
    # When this matcher fires, iter 996's per-group conjunction-handle
    # must also fire.
    per_group_m = CONDITION_REGISTRY[PER_GROUP_CONJUNCT]
    patterns = {
        "pair_analyses": [
            _pair([_group([7, 8])], input_palette=[7, 8, 9],
                  output_palette=[7, 8, 9]),
            _pair([_group([7, 8])], input_palette=[7, 8, 9],
                  output_palette=[7, 8, 9]),
        ],
    }
    assert _matcher()(patterns, {}) is True
    assert per_group_m(patterns, {}) is True


def test_converse_fails_whole_grid_only() -> None:
    # Iter 991 fires alone (whole-grid stable); per-blob palette varies
    # across pairs -- this matcher rejects on the per-group axis.
    whole_grid_m = CONDITION_REGISTRY[WHOLE_GRID_CONJUNCT]
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1])], input_palette=[0, 1, 2],
                  output_palette=[0, 1, 2]),
            _pair([_group([1, 2])], input_palette=[0, 1, 2],
                  output_palette=[0, 1, 2]),
        ],
    }
    assert whole_grid_m(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_converse_fails_per_group_only() -> None:
    # Iter 996 fires alone (per-blob stable); whole-grid palette varies
    # across pairs -- this matcher rejects on the whole-grid axis.
    per_group_m = CONDITION_REGISTRY[PER_GROUP_CONJUNCT]
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1])], input_palette=[0, 1, 2],
                  output_palette=[0, 1, 2]),
            _pair([_group([0, 1])], input_palette=[0, 1, 3],
                  output_palette=[0, 1, 3]),
        ],
    }
    assert per_group_m(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Transitive implications.
# ──────────────────────────────────────────────────────────────────────────

def test_strictly_implies_underlying_palette_axis_conjuncts() -> None:
    # When this matcher fires, every underlying palette-axis conjunct
    # transitively reachable through iter 991 or iter 996 must fire.
    underlying = [
        "output_palette_equals_input",                # via iter 991
        "input_palette_constant_across_pairs",        # via iter 991
        "output_palette_constant_across_pairs",       # via iter 991
        "input_group_palette_constant_across_pairs",  # via iter 996
        "output_group_palette_constant_across_pairs", # via iter 996
        "change_input_color_count_per_group_constant_across_pairs",   # via iter 994 -> 996
        "change_output_color_count_per_group_constant_across_pairs",  # via iter 995 -> 996
    ]
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1])], input_palette=[0, 1, 2],
                  output_palette=[0, 1, 2]),
            _pair([_group([0, 1])], input_palette=[0, 1, 2],
                  output_palette=[0, 1, 2]),
        ],
    }
    assert _matcher()(patterns, {}) is True
    for name in underlying:
        m = CONDITION_REGISTRY[name]
        assert m(patterns, {}) is True, (
            f"transitive implication broken: {name!r} did not fire on "
            f"aligned-palettes fixture"
        )


# ──────────────────────────────────────────────────────────────────────────
# Sibling-matcher relationships.
# ──────────────────────────────────────────────────────────────────────────

def test_independent_from_identity_transformation() -> None:
    # Identity rejects through iter 996's identity-territory clause.
    identity = CONDITION_REGISTRY["identity_transformation"]
    p_identity = {
        "pair_analyses": [
            _pair([], total_changes=0),
            _pair([], total_changes=0),
        ],
    }
    assert identity(p_identity, {}) is True
    assert _matcher()(p_identity, {}) is False


def test_independent_from_dimensional_conjunctions() -> None:
    # Iter 993 (whole-grid (H, W) AND palette conjunction). Independent:
    # this matcher does not constrain shape, and iter 993 does not
    # constrain per-blob content.
    iter993 = CONDITION_REGISTRY[
        "input_output_dimensions_and_palette_equal_and_constant_across_pairs"
    ]

    # This matcher fires, iter 993 rejects: per-blob and whole-grid
    # palettes stable, but shape varies across pairs.
    p_pal_only = {
        "pair_analyses": [
            _pair([_group([0, 1])], input_palette=[0, 1, 2],
                  output_palette=[0, 1, 2]),
            _pair([_group([0, 1])], input_palette=[0, 1, 2],
                  output_palette=[0, 1, 2], input_height=5, input_width=5,
                  output_height=5, output_width=5),
        ],
    }
    assert _matcher()(p_pal_only, {}) is True
    assert iter993(p_pal_only, {}) is False


def test_recognized_conditions_includes_this_matcher() -> None:
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1])], input_palette=[0, 1, 2],
                  output_palette=[0, 1, 2]),
            _pair([_group([0, 1])], input_palette=[0, 1, 2],
                  output_palette=[0, 1, 2]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME in fired, (
        f"{MATCHER_NAME!r} did not fire on an aligned-palettes fixture; "
        f"got {fired!r}"
    )


def test_recognized_conditions_excludes_on_whole_grid_mismatch() -> None:
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1])], input_palette=[0, 1, 2],
                  output_palette=[0, 1, 2]),
            _pair([_group([0, 1])], input_palette=[0, 1, 3],
                  output_palette=[0, 1, 3]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME not in fired, (
        f"{MATCHER_NAME!r} must NOT fire when whole-grid palette varies "
        f"across pairs; got {fired!r}"
    )


def test_recognized_conditions_excludes_on_per_group_mismatch() -> None:
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _pair([_group([0, 1])], input_palette=[0, 1, 2],
                  output_palette=[0, 1, 2]),
            _pair([_group([1, 2])], input_palette=[0, 1, 2],
                  output_palette=[0, 1, 2]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME not in fired, (
        f"{MATCHER_NAME!r} must NOT fire when per-blob palette varies "
        f"across pairs; got {fired!r}"
    )


def test_recognized_conditions_excludes_on_identity_territory() -> None:
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _pair([], total_changes=0),
            _pair([], total_changes=0),
        ],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME not in fired, (
        f"{MATCHER_NAME!r} must NOT fire on identity-territory; "
        f"got {fired!r}"
    )


def test_does_not_displace_adjacent_iter_matchers() -> None:
    # Adjacent-iter non-displacement: every conjunct + sibling matcher
    # remains in the registry alongside this new one.
    expected = {
        "input_palette_constant_across_pairs",
        "output_palette_constant_across_pairs",
        "input_output_palette_equal_and_constant_across_pairs",
        "input_output_dimensions_equal_and_constant_across_pairs",
        "input_output_dimensions_and_palette_equal_and_constant_across_pairs",
        "input_group_palette_constant_across_pairs",
        "output_group_palette_constant_across_pairs",
        "input_output_group_palette_equal_and_constant_across_pairs",
        "identity_transformation",
        "output_palette_equals_input",
    }
    missing = expected - set(CONDITION_REGISTRY)
    assert not missing, (
        f"adjacent matchers missing post-iter-997: {missing!r}"
    )


# ──────────────────────────────────────────────────────────────────────────
# Runner.
# ──────────────────────────────────────────────────────────────────────────

def _collect_tests():
    return [
        (name, obj)
        for name, obj in globals().items()
        if name.startswith("test_") and callable(obj)
    ]


def main() -> int:
    failures = []
    tests = _collect_tests()
    for name, fn in tests:
        try:
            fn()
        except AssertionError as e:
            failures.append((name, str(e) or repr(e), traceback.format_exc()))
        except Exception as e:  # pragma: no cover -- contract assertions
            failures.append((name, f"{type(e).__name__}: {e}", traceback.format_exc()))
    total = len(tests)
    passed = total - len(failures)
    print(f"{passed}/{total} tests passed")
    for name, msg, tb in failures:
        print(f"\nFAIL {name}: {msg}\n{tb}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
