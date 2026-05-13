"""
tests/test_output_dimensions_square.py -- exercise the iter-183 matcher
``agent.conditions.output_dimensions_square`` (new in this iter).

Pins the matcher's contract per ``agent/conditions/output_dimensions_
square.py`` docstring: every pair's ``output_height`` == ``output_width``
(both strict positive ints, bool rejected) on a non-empty
``pair_analyses`` list. The "smoke" membership / callability slots
mirror the other matcher tests so the registry-vs-test-file diff
stays empty.

Runs without pytest:

    python tests/test_output_dimensions_square.py

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


MATCHER_NAME = "output_dimensions_square"


def _matcher():
    return CONDITION_REGISTRY[MATCHER_NAME]


def _square_out_pair(n: int = 3, size_match: bool = True) -> dict:
    """A pair_analysis shaped like ExtractPatternOperator's output for a
    pair whose output is ``n x n``. ``size_match`` is independent of
    output square-ness (square-output is an output-only property; the
    iter-1 matcher handles the input==output axis)."""
    return {
        "input_height": n,
        "input_width": n,
        "output_height": n,
        "output_width": n,
        "size_match": size_match,
        "total_changes": 0,
        "num_groups": 0,
        "groups": [],
    }


def _non_square_out_pair(h: int = 2, w: int = 3) -> dict:
    """A pair_analysis whose output is rectangular but not square."""
    return {
        "input_height": h,
        "input_width": w,
        "output_height": h,
        "output_width": w,
        "size_match": True,
        "total_changes": 0,
        "num_groups": 0,
        "groups": [],
    }


def _tile_out_pair(n_out: int = 3, n_in: int = 2) -> dict:
    """A pair with non-square ``n_in x (n_in+1)`` input and square
    ``n_out x n_out`` output. Used to assert the matcher fires on the
    output side even when the input side is non-square."""
    return {
        "input_height": n_in,
        "input_width": n_in + 1,
        "output_height": n_out,
        "output_width": n_out,
        "size_match": False,
        "total_changes": 0,
        "num_groups": 0,
        "groups": [],
    }


# ──────────────────────────────────────────────────────────────────────────
# Smoke / membership tests.
# ──────────────────────────────────────────────────────────────────────────

def test_registered_in_global_registry() -> None:
    assert MATCHER_NAME in CONDITION_REGISTRY, (
        f"{MATCHER_NAME!r} not registered; got {sorted(CONDITION_REGISTRY)}"
    )


def test_matcher_is_callable() -> None:
    fn = _matcher()
    assert callable(fn), f"registered entry is not callable: {fn!r}"


# ──────────────────────────────────────────────────────────────────────────
# Positive cases.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_true_on_single_square_output_pair() -> None:
    patterns = {"pair_analyses": [_square_out_pair(3)]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_all_pairs_square_output() -> None:
    patterns = {
        "pair_analyses": [_square_out_pair(2), _square_out_pair(3),
                          _square_out_pair(4)],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_on_1x1_output_pair() -> None:
    # Edge case: 1x1 is technically square. Strict positive int gate
    # admits 1; the equality H == W trivially holds.
    patterns = {"pair_analyses": [_square_out_pair(1)]}
    assert _matcher()(patterns, {}) is True


def test_returns_true_when_input_non_square_but_output_square() -> None:
    # The output-side dual of input_dimensions_square's tile-style
    # case. A 2x3 -> 5x5 task has non-square inputs but square
    # outputs; this matcher inspects the output axis only -- it must
    # fire here.
    patterns = {
        "pair_analyses": [_tile_out_pair(5, 2), _tile_out_pair(5, 2)],
    }
    assert _matcher()(patterns, {}) is True


def test_returns_true_when_output_dims_vary_across_pairs_but_each_is_square() -> None:
    # Cross-pair constancy is iter 20's territory (output_dimensions_
    # constant). This matcher inspects the per-pair output square
    # property and is INDEPENDENT of cross-pair constancy of (H, W).
    patterns = {
        "pair_analyses": [_square_out_pair(2), _square_out_pair(3),
                          _square_out_pair(5)],
    }
    assert _matcher()(patterns, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Negative cases.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_false_on_single_non_square_output_pair() -> None:
    patterns = {"pair_analyses": [_non_square_out_pair(2, 3)]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_any_pair_output_is_non_square() -> None:
    # Universal-over-pairs semantic: a single non-square-output pair
    # fails the whole task.
    patterns = {
        "pair_analyses": [_square_out_pair(3), _non_square_out_pair(2, 3),
                          _square_out_pair(4)],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_every_pair_output_is_non_square() -> None:
    patterns = {
        "pair_analyses": [_non_square_out_pair(2, 3),
                          _non_square_out_pair(4, 5)],
    }
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_empty_pair_analyses() -> None:
    # Empty list must NOT vacuously fire -- the iter-1 / iter-13 /
    # iter-17 / iter-20 / iter-22 / iter-33 / iter-182 fail-closed
    # posture on empty input.
    patterns = {"pair_analyses": []}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_missing_pair_analyses() -> None:
    patterns = {}
    assert _matcher()(patterns, {}) is False


def test_returns_false_on_non_list_pair_analyses() -> None:
    for bad in (None, 42, "oops", {"a": 1}, (), True):
        patterns = {"pair_analyses": bad}
        assert _matcher()(patterns, {}) is False, (
            f"pair_analyses={bad!r} should not fire"
        )


def test_returns_false_on_non_dict_patterns() -> None:
    assert _matcher()(None, {}) is False         # type: ignore[arg-type]
    assert _matcher()([], {}) is False           # type: ignore[arg-type]
    assert _matcher()("oops", {}) is False       # type: ignore[arg-type]
    assert _matcher()(42, {}) is False           # type: ignore[arg-type]


def test_returns_false_when_any_analysis_is_not_dict() -> None:
    patterns = {
        "pair_analyses": [_square_out_pair(3), "not-a-dict",
                          _square_out_pair(4)],
    }
    assert _matcher()(patterns, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Strict-type-gate cases (mirrors validate_rule V1's bool-rejection and
# the iter-13 / 17 / 20 / 22 / 33 / 182 strict-positive-int posture).
# ──────────────────────────────────────────────────────────────────────────

def test_returns_false_when_output_height_missing() -> None:
    analysis = _square_out_pair(3)
    del analysis["output_height"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_width_missing() -> None:
    analysis = _square_out_pair(3)
    del analysis["output_width"]
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_height_is_bool() -> None:
    # Python bools are an int subclass; strict gate must reject them.
    analysis = _square_out_pair(3)
    analysis["output_height"] = True
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_width_is_bool() -> None:
    analysis = _square_out_pair(3)
    analysis["output_width"] = True
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_height_is_zero() -> None:
    analysis = _square_out_pair(3)
    analysis["output_height"] = 0
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_width_is_zero() -> None:
    analysis = _square_out_pair(3)
    analysis["output_width"] = 0
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_height_is_negative() -> None:
    analysis = _square_out_pair(3)
    analysis["output_height"] = -3
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_height_is_float() -> None:
    analysis = _square_out_pair(3)
    analysis["output_height"] = 3.0
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


def test_returns_false_when_output_height_is_string() -> None:
    analysis = _square_out_pair(3)
    analysis["output_height"] = "3"
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is False


# ──────────────────────────────────────────────────────────────────────────
# Behavioural-contract cases.
# ──────────────────────────────────────────────────────────────────────────

def test_is_side_effect_free_on_inputs() -> None:
    patterns = {
        "pair_analyses": [_square_out_pair(3), _non_square_out_pair(2, 3)],
    }
    params = {"unused": 1}
    before_p = copy.deepcopy(patterns)
    before_q = copy.deepcopy(params)
    _matcher()(patterns, params)
    assert patterns == before_p, "matcher mutated patterns"
    assert params == before_q, "matcher mutated params"


def test_is_deterministic_across_repeats() -> None:
    patterns = {"pair_analyses": [_square_out_pair(3), _square_out_pair(4)]}
    results = [_matcher()(patterns, {}) for _ in range(5)]
    assert len(set(results)) == 1, f"non-deterministic outputs: {results}"


def test_returned_value_is_boolean_not_truthy() -> None:
    # recognized_conditions filters on ``match(...) is True`` exactly,
    # so the matcher must return literal Booleans.
    patterns_true = {"pair_analyses": [_square_out_pair(3)]}
    patterns_false = {"pair_analyses": [_non_square_out_pair(2, 3)]}
    out_true = _matcher()(patterns_true, {})
    out_false = _matcher()(patterns_false, {})
    assert out_true is True, f"expected literal True, got {out_true!r}"
    assert out_false is False, f"expected literal False, got {out_false!r}"


def test_ignores_input_dimensions() -> None:
    # The matcher inspects OUTPUT dims only. A square-output pair with
    # arbitrary non-square input dims must still fire.
    analysis = {
        "input_height": 2, "input_width": 5,
        "output_height": 3, "output_width": 3,
        "size_match": False,
        "total_changes": 0, "num_groups": 0, "groups": [],
    }
    patterns = {"pair_analyses": [analysis]}
    assert _matcher()(patterns, {}) is True


def test_ignores_size_match_flag() -> None:
    # size_match is the per-pair input==output flag. The matcher must
    # NOT depend on it -- a square-output pair fires regardless of
    # whether output matches input.
    sq_match = _square_out_pair(3, size_match=True)
    sq_mismatch = _square_out_pair(3, size_match=False)
    assert _matcher()({"pair_analyses": [sq_match]}, {}) is True
    assert _matcher()({"pair_analyses": [sq_mismatch]}, {}) is True


# ──────────────────────────────────────────────────────────────────────────
# Orthogonality tests against the dimensional matcher quadrant.
# ──────────────────────────────────────────────────────────────────────────

def test_orthogonal_to_grid_size_preserved() -> None:
    # The output-square axis is independent of the per-pair size_match
    # axis. Four-cell matrix: {square-out, non-square-out} x {preserved,
    # changed}.
    gsp = CONDITION_REGISTRY["grid_size_preserved"]

    # square-out + preserved -- both fire (3x3 -> 3x3)
    p1 = {
        "grid_size_preserved": True,
        "pair_analyses": [_square_out_pair(3, size_match=True)],
    }
    assert _matcher()(p1, {}) is True and gsp(p1, {}) is True

    # square-out + changed -- only square-out fires (2x3 -> 5x5)
    p2 = {
        "grid_size_preserved": False,
        "pair_analyses": [_tile_out_pair(5, 2)],
    }
    assert _matcher()(p2, {}) is True and gsp(p2, {}) is False

    # non-square-out + preserved -- only preserved fires (3x4 -> 3x4)
    p3 = {
        "grid_size_preserved": True,
        "pair_analyses": [_non_square_out_pair(3, 4)],
    }
    assert _matcher()(p3, {}) is False and gsp(p3, {}) is True

    # non-square-out + changed -- neither fires (3x4 -> 5x6)
    rect_changed = dict(_non_square_out_pair(3, 4))
    rect_changed["output_height"] = 5
    rect_changed["output_width"] = 6
    rect_changed["size_match"] = False
    p4 = {
        "grid_size_preserved": False,
        "pair_analyses": [rect_changed],
    }
    assert _matcher()(p4, {}) is False and gsp(p4, {}) is False


def test_orthogonal_to_output_dimensions_constant() -> None:
    # Cross-pair constancy of (H, W) is iter-20's axis. This matcher's
    # per-pair output-square property is INDEPENDENT.
    odc = CONDITION_REGISTRY["output_dimensions_constant"]

    # square-out + constant -- both fire
    p1 = {"pair_analyses": [_square_out_pair(3), _square_out_pair(3)]}
    assert _matcher()(p1, {}) is True and odc(p1, {}) is True

    # square-out + non-constant -- only square-out fires
    p2 = {"pair_analyses": [_square_out_pair(2), _square_out_pair(3)]}
    assert _matcher()(p2, {}) is True and odc(p2, {}) is False

    # non-square-out + constant -- only constant fires
    rect = _non_square_out_pair(2, 3)
    p3 = {"pair_analyses": [rect, dict(rect)]}
    assert _matcher()(p3, {}) is False and odc(p3, {}) is True

    # non-square-out + non-constant -- neither fires
    p4 = {
        "pair_analyses": [_non_square_out_pair(2, 3),
                          _non_square_out_pair(4, 5)],
    }
    assert _matcher()(p4, {}) is False and odc(p4, {}) is False


def test_orthogonal_to_input_dimensions_square() -> None:
    # Iter 182's input-side dual. The two matchers' truth values are
    # independent: the {input-square, input-non-square} x {output-
    # square, output-non-square} 2x2 matrix has all four cells
    # populable.
    ids_mat = CONDITION_REGISTRY["input_dimensions_square"]

    # input-sq + output-sq -- both fire (3x3 -> 4x4)
    p1 = {
        "pair_analyses": [{
            "input_height": 3, "input_width": 3,
            "output_height": 4, "output_width": 4,
            "size_match": False,
            "total_changes": 0, "num_groups": 0, "groups": [],
        }],
    }
    assert _matcher()(p1, {}) is True and ids_mat(p1, {}) is True

    # input-sq + output-non-sq -- only iter 182 fires (3x3 -> 5x4)
    p2 = {
        "pair_analyses": [{
            "input_height": 3, "input_width": 3,
            "output_height": 5, "output_width": 4,
            "size_match": False,
            "total_changes": 0, "num_groups": 0, "groups": [],
        }],
    }
    assert _matcher()(p2, {}) is False and ids_mat(p2, {}) is True

    # input-non-sq + output-sq -- only this matcher fires (3x4 -> 5x5)
    p3 = {
        "pair_analyses": [{
            "input_height": 3, "input_width": 4,
            "output_height": 5, "output_width": 5,
            "size_match": False,
            "total_changes": 0, "num_groups": 0, "groups": [],
        }],
    }
    assert _matcher()(p3, {}) is True and ids_mat(p3, {}) is False

    # input-non-sq + output-non-sq -- neither fires (3x4 -> 5x6)
    p4 = {
        "pair_analyses": [{
            "input_height": 3, "input_width": 4,
            "output_height": 5, "output_width": 6,
            "size_match": False,
            "total_changes": 0, "num_groups": 0, "groups": [],
        }],
    }
    assert _matcher()(p4, {}) is False and ids_mat(p4, {}) is False


def test_orthogonal_to_output_dimensions_multiple_of_input() -> None:
    # Iter 33's relational scale-ratio axis is orthogonal to whether
    # either axis is square. A non-square tile-style task fires iter
    # 33 but NOT this matcher.
    odmi = CONDITION_REGISTRY["output_dimensions_multiple_of_input"]

    # square-out + multiple_of -- both fire (3x3 -> 9x9)
    sq_tiled = {
        "input_height": 3, "input_width": 3,
        "output_height": 9, "output_width": 9,
        "size_match": False,
        "total_changes": 0, "num_groups": 0, "groups": [],
    }
    p1 = {"pair_analyses": [sq_tiled, sq_tiled]}
    assert _matcher()(p1, {}) is True and odmi(p1, {}) is True

    # non-square-out + multiple_of -- only iter 33 fires (2x3 -> 6x9)
    nonsq_tiled = {
        "input_height": 2, "input_width": 3,
        "output_height": 6, "output_width": 9,
        "size_match": False,
        "total_changes": 0, "num_groups": 0, "groups": [],
    }
    p2 = {"pair_analyses": [nonsq_tiled, nonsq_tiled]}
    assert _matcher()(p2, {}) is False and odmi(p2, {}) is True


def test_recognized_conditions_includes_output_dimensions_square() -> None:
    # The applier in agent/conditions/__init__.py must surface the new
    # matcher when its pattern is fired -- pins the wiring.
    from agent.conditions import recognized_conditions
    patterns = {"pair_analyses": [_square_out_pair(3), _square_out_pair(3)]}
    fired = recognized_conditions(patterns)
    assert MATCHER_NAME in fired, (
        f"{MATCHER_NAME!r} missing from recognized_conditions output: "
        f"{fired!r}"
    )


# ──────────────────────────────────────────────────────────────────────────
# Driver.
# ──────────────────────────────────────────────────────────────────────────

def _run_all() -> int:
    tests = [
        test_registered_in_global_registry,
        test_matcher_is_callable,
        test_returns_true_on_single_square_output_pair,
        test_returns_true_on_all_pairs_square_output,
        test_returns_true_on_1x1_output_pair,
        test_returns_true_when_input_non_square_but_output_square,
        test_returns_true_when_output_dims_vary_across_pairs_but_each_is_square,
        test_returns_false_on_single_non_square_output_pair,
        test_returns_false_when_any_pair_output_is_non_square,
        test_returns_false_when_every_pair_output_is_non_square,
        test_returns_false_on_empty_pair_analyses,
        test_returns_false_on_missing_pair_analyses,
        test_returns_false_on_non_list_pair_analyses,
        test_returns_false_on_non_dict_patterns,
        test_returns_false_when_any_analysis_is_not_dict,
        test_returns_false_when_output_height_missing,
        test_returns_false_when_output_width_missing,
        test_returns_false_when_output_height_is_bool,
        test_returns_false_when_output_width_is_bool,
        test_returns_false_when_output_height_is_zero,
        test_returns_false_when_output_width_is_zero,
        test_returns_false_when_output_height_is_negative,
        test_returns_false_when_output_height_is_float,
        test_returns_false_when_output_height_is_string,
        test_is_side_effect_free_on_inputs,
        test_is_deterministic_across_repeats,
        test_returned_value_is_boolean_not_truthy,
        test_ignores_input_dimensions,
        test_ignores_size_match_flag,
        test_orthogonal_to_grid_size_preserved,
        test_orthogonal_to_output_dimensions_constant,
        test_orthogonal_to_input_dimensions_square,
        test_orthogonal_to_output_dimensions_multiple_of_input,
        test_recognized_conditions_includes_output_dimensions_square,
    ]
    fails = 0
    for t in tests:
        try:
            t()
            print(f"  OK   {t.__name__}")
        except AssertionError as e:
            fails += 1
            print(f"  FAIL {t.__name__}: {e}")
        except Exception:
            fails += 1
            print(f"  FAIL {t.__name__}: unexpected exception")
            traceback.print_exc()
    return fails


if __name__ == "__main__":
    n = _run_all()
    sys.exit(1 if n else 0)
