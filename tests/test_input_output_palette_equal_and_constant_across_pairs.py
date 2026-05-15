"""
tests/test_input_output_palette_equal_and_constant_across_pairs.py --
exercise the iter-991 matcher
``agent.conditions.input_output_palette_equal_and_constant_across_pairs``
(new in this iter).

Pins the matcher's contract per the docstring of
``agent/conditions/input_output_palette_equal_and_constant_across_pairs.py``:
there exists a single colour set S such that every pair's input palette
AND output palette is exactly S, on a non-empty ``pair_analyses`` list
with each palette shaped as a list of non-bool ints.

Conjunction handle for the three pre-existing conjuncts (iter 989
input-side constancy, iter 990 output-side constancy, iter 185 per-pair
set equality). The discriminating-axis tests verify that the new
matcher fires iff all three of those fire.

Runs without pytest:

    python tests/test_input_output_palette_equal_and_constant_across_pairs.py

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


MATCHER_NAME = "input_output_palette_equal_and_constant_across_pairs"


def _matcher():
    return CONDITION_REGISTRY[MATCHER_NAME]


def _pair(input_palette, output_palette=None, **overrides):
    """A pair_analysis shaped like ExtractPatternOperator's output
    (iter-184 schema, with the palette fields).

    By default ``output_palette`` mirrors ``input_palette`` so the
    per-pair set-equality conjunct is satisfied unless explicitly
    overridden.
    """
    if output_palette is None:
        output_palette = list(input_palette)
    base = {
        "input_height": 3,
        "input_width": 3,
        "output_height": 3,
        "output_width": 3,
        "size_match": True,
        "total_changes": 0,
        "num_groups": 0,
        "groups": [],
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


def test_p5_at_least_85() -> None:
    # Iter-991 brings the registry to >= 85 (P5 monotone). The probe
    # baseline was P5 = 84 after iter 990.
    assert len(CONDITION_REGISTRY) >= 85, (
        f"expected >= 85 matchers post-iter-991; got {len(CONDITION_REGISTRY)}"
    )


# ──────────────────────────────────────────────────────────────────────────
# Positive cases.
# ──────────────────────────────────────────────────────────────────────────

def test_single_pair_with_equal_palettes_fires() -> None:
    patterns = {"pair_analyses": [_pair([0, 1, 2])]}
    assert _matcher()(patterns, {}) is True


def test_two_pairs_same_palette_input_equal_output_fires() -> None:
    patterns = {"pair_analyses": [_pair([0, 1, 2]), _pair([0, 1, 2])]}
    assert _matcher()(patterns, {}) is True


def test_set_equal_under_different_list_order_fires() -> None:
    # frozenset equality is order-insensitive; the verdict holds
    # regardless of how _analyze_pair orders the lists.
    patterns = {
        "pair_analyses": [
            _pair([2, 0, 1], output_palette=[1, 2, 0]),
            _pair([1, 2, 0], output_palette=[0, 1, 2]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_set_equal_with_duplicates_fires() -> None:
    # Duplicates within either list collapse under set semantics.
    patterns = {
        "pair_analyses": [
            _pair([0, 0, 1, 1], output_palette=[1, 0, 1, 0]),
            _pair([1, 0, 1, 0], output_palette=[0, 0, 1, 1]),
        ],
    }
    assert _matcher()(patterns, {}) is True


def test_all_empty_palettes_fires() -> None:
    # Degenerate all-empty case (per iter 989/990 posture): every
    # pair has empty input AND empty output palette, both shared
    # across pairs. The matcher fires.
    patterns = {
        "pair_analyses": [_pair([], []), _pair([], [])]
    }
    assert _matcher()(patterns, {}) is True


def test_singleton_palette_fires() -> None:
    patterns = {"pair_analyses": [_pair([5]), _pair([5])]}
    assert _matcher()(patterns, {}) is True


def test_three_pairs_all_same_palette_fires() -> None:
    patterns = {
        "pair_analyses": [
            _pair([0, 1, 2]),
            _pair([0, 1, 2]),
            _pair([0, 1, 2]),
        ],
    }
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Negative cases (per-pair equality violated).
# ──────────────────────────────────────────────────────────────────────────

def test_per_pair_input_neq_output_rejects() -> None:
    # Iter-185 conjunct fails on the first pair: input != output.
    patterns = {
        "pair_analyses": [
            _pair([0, 1, 2], output_palette=[0, 1, 3]),
            _pair([0, 1, 2]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_per_pair_disjoint_palettes_rejects() -> None:
    # Per-pair input disjoint from output -- iter-185 conjunct fails.
    patterns = {
        "pair_analyses": [
            _pair([0, 1, 2], output_palette=[3, 4, 5]),
            _pair([0, 1, 2], output_palette=[3, 4, 5]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_per_pair_subset_relation_rejects() -> None:
    # Input strict subset of output -- iter-185 conjunct fails.
    patterns = {
        "pair_analyses": [
            _pair([0, 1], output_palette=[0, 1, 2]),
        ],
    }
    assert _matcher()(patterns, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Negative cases (cross-pair constancy violated).
# ──────────────────────────────────────────────────────────────────────────

def test_input_constancy_violated_rejects() -> None:
    # Each pair has input == output as sets (iter-185 fires per-pair),
    # but the shared per-pair palette differs across pairs.
    patterns = {
        "pair_analyses": [
            _pair([0, 1]),
            _pair([2, 3]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_output_constancy_violated_rejects() -> None:
    # Same as above with explicit different output sets on pair 2;
    # both conjuncts (input-constant, output-constant) fail.
    patterns = {
        "pair_analyses": [
            _pair([0, 1, 2], output_palette=[0, 1, 2]),
            _pair([3, 4, 5], output_palette=[3, 4, 5]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_one_offending_pair_fails_the_gate() -> None:
    # Universal-over-pairs: one mismatched pair fails the whole task.
    patterns = {
        "pair_analyses": [
            _pair([0, 1, 2]),
            _pair([0, 1, 2]),
            _pair([0, 1, 9]),  # offending pair (per-pair OK, cross-pair NO)
            _pair([0, 1, 2]),
        ],
    }
    assert _matcher()(patterns, {}) is False


def test_partial_overlap_across_pairs_rejects() -> None:
    # Per-pair input == output. Cross-pair: pair 0 palette {0,1,2},
    # pair 1 palette {0,1,3} -- non-equal, gate fails.
    patterns = {
        "pair_analyses": [
            _pair([0, 1, 2]),
            _pair([0, 1, 3]),
        ],
    }
    assert _matcher()(patterns, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Fail-closed paths.
# ──────────────────────────────────────────────────────────────────────────

def test_empty_pair_analyses_rejects() -> None:
    patterns = {"pair_analyses": []}
    assert _matcher()(patterns, {}) is False


def test_missing_pair_analyses_rejects() -> None:
    assert _matcher()({}, {}) is False


def test_non_list_pair_analyses_rejects() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (), True):
        assert _matcher()({"pair_analyses": bad}, {}) is False, (
            f"pair_analyses={bad!r} should not fire"
        )


def test_non_dict_patterns_rejects() -> None:
    for bad in (None, [], "oops", 42):
        assert _matcher()(bad, {}) is False, f"patterns={bad!r} should not fire"  # type: ignore[arg-type]


def test_non_dict_analysis_rejects() -> None:
    patterns = {
        "pair_analyses": [_pair([0, 1]), "not-a-dict", _pair([0, 1])]
    }
    assert _matcher()(patterns, {}) is False


def test_missing_input_palette_rejects() -> None:
    analysis = _pair([0, 1])
    del analysis["input_palette"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_missing_output_palette_rejects() -> None:
    analysis = _pair([0, 1])
    del analysis["output_palette"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_non_list_input_palette_rejects() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (0, 1), True, {0, 1}):
        analysis = _pair([0, 1])
        analysis["input_palette"] = bad
        patterns = {"pair_analyses": [analysis]}
        assert _matcher()(patterns, {}) is False, (
            f"input_palette={bad!r} should not fire"
        )


def test_non_list_output_palette_rejects() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (0, 1), True, {0, 1}):
        analysis = _pair([0, 1])
        analysis["output_palette"] = bad
        patterns = {"pair_analyses": [analysis]}
        assert _matcher()(patterns, {}) is False, (
            f"output_palette={bad!r} should not fire"
        )


def test_bool_in_input_palette_rejects() -> None:
    analysis = _pair([0, 1])
    analysis["input_palette"] = [0, True]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_bool_in_output_palette_rejects() -> None:
    analysis = _pair([0, 1])
    analysis["output_palette"] = [0, True]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_non_int_in_input_palette_rejects() -> None:
    analysis = _pair([0, 1])
    analysis["input_palette"] = [0, "1"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False

    analysis2 = _pair([0, 1])
    analysis2["input_palette"] = [0.0, 1]
    patterns2 = {"pair_analyses": [analysis2]}
    assert _matcher()(patterns2, {}) is False


def test_non_int_in_output_palette_rejects() -> None:
    analysis = _pair([0, 1])
    analysis["output_palette"] = [0, "1"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False

    analysis2 = _pair([0, 1])
    analysis2["output_palette"] = [0.0, 1]
    patterns2 = {"pair_analyses": [analysis2]}
    assert _matcher()(patterns2, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Behavioural contract.
# ──────────────────────────────────────────────────────────────────────────

def test_side_effect_free() -> None:
    patterns = {"pair_analyses": [_pair([0, 1]), _pair([1, 0])]}
    params = {"unused": 1}
    before_p = copy.deepcopy(patterns)
    before_q = copy.deepcopy(params)
    _matcher()(patterns, params)
    assert patterns == before_p, "matcher mutated patterns"
    assert params == before_q, "matcher mutated params"


def test_deterministic_across_repeats() -> None:
    patterns = {"pair_analyses": [_pair([0, 1, 2]), _pair([0, 1, 2])]}
    results = [_matcher()(patterns, {}) for _ in range(5)]
    assert len(set(results)) == 1, f"non-deterministic: {results}"


def test_returns_literal_boolean() -> None:
    out_true = _matcher()({"pair_analyses": [_pair([0, 1])]}, {})
    out_false = _matcher()(
        {"pair_analyses": [_pair([0]), _pair([1])]}, {}
    )
    assert out_true is True, f"expected literal True, got {out_true!r}"
    assert out_false is False, f"expected literal False, got {out_false!r}"


def test_ignores_dimensional_fields() -> None:
    # Dim fields are orthogonal -- arbitrary dim values must not change
    # the verdict.
    patterns = {
        "pair_analyses": [
            _pair([0, 1], input_height=7, input_width=9, output_height=2,
                  output_width=3, size_match=False),
            _pair([0, 1], input_height=2, input_width=3, output_height=2,
                  output_width=3, size_match=True),
        ],
    }
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Conjunction relationships -- the three named conjuncts.
# ──────────────────────────────────────────────────────────────────────────

def test_fires_iff_all_three_conjuncts_fire() -> None:
    # Discriminating-axis test. The matcher must agree with the literal
    # conjunction of iter 185 (output_palette_equals_input), iter 989
    # (input_palette_constant_across_pairs), and iter 990
    # (output_palette_constant_across_pairs) on every cell of the 2^3
    # truth table that the fixture vocabulary can realise.
    ope = CONDITION_REGISTRY["output_palette_equals_input"]
    ipc = CONDITION_REGISTRY["input_palette_constant_across_pairs"]
    opc = CONDITION_REGISTRY["output_palette_constant_across_pairs"]

    cases = [
        # All three fire -- conjunction fires.
        {"pair_analyses": [_pair([0, 1]), _pair([0, 1])]},
        # All three fire (singleton palette).
        {"pair_analyses": [_pair([5]), _pair([5])]},
        # iter 185 fails per-pair (input != output) -- conjunction rejects.
        {
            "pair_analyses": [
                _pair([0, 1], output_palette=[0, 2]),
                _pair([0, 1], output_palette=[0, 2]),
            ],
        },
        # iter 989 fails (input varies) -- conjunction rejects.
        {
            "pair_analyses": [
                _pair([0, 1]),
                _pair([2, 3]),
            ],
        },
        # iter 990 fails (output varies even though per-pair equal and
        # input is constant) is impossible: if input is constant and
        # per-pair input == output, output is also constant. So the only
        # two-of-three failure modes are "per-pair fails" and "constancy
        # fails", both covered above.
    ]
    for p in cases:
        m = _matcher()(p, {})
        expected = (
            ope(p, {}) is True
            and ipc(p, {}) is True
            and opc(p, {}) is True
        )
        assert m is expected, (
            f"matcher disagrees with literal conjunction on {p!r}: "
            f"matcher={m!r}, expected={expected!r}"
        )


def test_strictly_implies_each_conjunct() -> None:
    # When this matcher fires, each individual conjunct must also fire.
    ope = CONDITION_REGISTRY["output_palette_equals_input"]
    ipc = CONDITION_REGISTRY["input_palette_constant_across_pairs"]
    opc = CONDITION_REGISTRY["output_palette_constant_across_pairs"]

    patterns = {"pair_analyses": [_pair([0, 1, 2]), _pair([0, 1, 2])]}
    assert _matcher()(patterns, {}) is True
    assert ope(patterns, {}) is True, "iter-185 conjunct must hold"
    assert ipc(patterns, {}) is True, "iter-989 conjunct must hold"
    assert opc(patterns, {}) is True, "iter-990 conjunct must hold"


def test_converse_fails_iter_185_alone_does_not_imply() -> None:
    # iter 185 fires per-pair; cross-pair palette can vary. This matcher
    # rejects on cross-pair variation even when iter 185 is universally
    # satisfied.
    ope = CONDITION_REGISTRY["output_palette_equals_input"]
    patterns = {
        "pair_analyses": [_pair([0, 1]), _pair([2, 3])],
    }
    assert ope(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


def test_converse_fails_iter_989_990_alone_do_not_imply() -> None:
    # iter 989 AND iter 990 can both fire while per-pair input != output.
    ipc = CONDITION_REGISTRY["input_palette_constant_across_pairs"]
    opc = CONDITION_REGISTRY["output_palette_constant_across_pairs"]
    patterns = {
        "pair_analyses": [
            _pair([0, 1], output_palette=[2, 3]),
            _pair([0, 1], output_palette=[2, 3]),
        ],
    }
    assert ipc(patterns, {}) is True
    assert opc(patterns, {}) is True
    assert _matcher()(patterns, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Sibling-matcher relationships.
# ──────────────────────────────────────────────────────────────────────────

def test_independent_from_identity_transformation() -> None:
    # Identity says every pair internally preserves; says nothing about
    # cross-pair palette equality. INDEPENDENT.
    identity = CONDITION_REGISTRY["identity_transformation"]

    # Identity fires but palettes vary across pairs -- this matcher
    # rejects, identity accepts.
    p1 = {
        "pair_analyses": [_pair([0, 1]), _pair([2, 3])],
    }
    assert identity(p1, {}) is True
    assert _matcher()(p1, {}) is False

    # Identity fires AND palettes match -- both fire.
    p2 = {
        "pair_analyses": [_pair([0, 1]), _pair([0, 1])],
    }
    assert identity(p2, {}) is True
    assert _matcher()(p2, {}) is True

    # This matcher fires on a permutation (changed cells, palettes
    # equal as sets) -- identity REJECTS because the per-pair change
    # group list is non-empty.
    _group = {"input_colors": [0], "output_colors": [1],
              "positions": [(0, 0)], "top_row": 0, "top_col": 0}
    p3 = {
        "pair_analyses": [
            _pair([0, 1], num_groups=1, total_changes=1,
                  groups=[dict(_group)]),
            _pair([0, 1], num_groups=1, total_changes=1,
                  groups=[dict(_group)]),
        ],
    }
    # iter 13 inspects ``groups`` (a list of change groups); on a
    # permutation that list is non-empty so identity rejects, while
    # our matcher only inspects palettes and fires.
    assert identity(p3, {}) is False
    assert _matcher()(p3, {}) is True


def test_independent_from_output_dimensions_constant() -> None:
    # Dimensional axis vs palette axis -- independent.
    odc = CONDITION_REGISTRY["output_dimensions_constant"]

    # Both fire.
    p_both = {"pair_analyses": [_pair([0, 1]), _pair([0, 1])]}
    assert _matcher()(p_both, {}) is True and odc(p_both, {}) is True

    # Only this matcher: same palette, different output dims.
    p_pal_only = {
        "pair_analyses": [
            _pair([0, 1], output_height=3, output_width=3),
            _pair([0, 1], output_height=5, output_width=5),
        ],
    }
    assert _matcher()(p_pal_only, {}) is True and odc(p_pal_only, {}) is False

    # Only iter 20: same output dims, different palette.
    p_dim_only = {
        "pair_analyses": [
            _pair([0, 1], output_height=3, output_width=3),
            _pair([2, 3], output_height=3, output_width=3),
        ],
    }
    assert _matcher()(p_dim_only, {}) is False and odc(p_dim_only, {}) is True


def test_recognized_conditions_includes_this_matcher() -> None:
    from agent.conditions import recognized_conditions
    patterns = {"pair_analyses": [_pair([0, 1, 2]), _pair([0, 1, 2])]}
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME in fired, (
        f"{MATCHER_NAME!r} did not fire on a clearly fixed-vocabulary "
        f"patterns dict; got {fired!r}"
    )


def test_recognized_conditions_excludes_on_per_pair_mismatch() -> None:
    from agent.conditions import recognized_conditions
    patterns = {
        "pair_analyses": [
            _pair([0, 1], output_palette=[2, 3]),
            _pair([0, 1], output_palette=[2, 3]),
        ],
    }
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME not in fired, (
        f"{MATCHER_NAME!r} must NOT fire on per-pair palette inequality; "
        f"got {fired!r}"
    )


def test_recognized_conditions_excludes_on_cross_pair_mismatch() -> None:
    from agent.conditions import recognized_conditions
    patterns = {"pair_analyses": [_pair([0, 1]), _pair([2, 3])]}
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME not in fired, (
        f"{MATCHER_NAME!r} must NOT fire on cross-pair palette variation; "
        f"got {fired!r}"
    )


def test_does_not_displace_adjacent_iter_matchers() -> None:
    # Adjacent-iter non-displacement: every iter-13/20/22/185/989/990
    # matcher remains in the registry alongside this new one.
    expected = {
        "identity_transformation",
        "input_dimensions_constant",
        "output_dimensions_constant",
        "output_palette_equals_input",
        "input_palette_constant_across_pairs",
        "output_palette_constant_across_pairs",
    }
    missing = expected - set(CONDITION_REGISTRY)
    assert not missing, (
        f"adjacent matchers missing post-iter-991: {missing!r}"
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
