"""
Tests for the `test_output_missing` condition matcher (agent/conditions/).

`test_output_missing` is one of the **two load-bearing matchers** in the Slice-1
decisive solve: `GeneralizeOperator._recognizes_copy_common_output`
(agent/active_operators.py) fires the value-agnostic copy-common-output rule only
when BOTH `test_output_missing` (PAIR level) AND `all_outputs_comm` (GRID level)
match. Its GRID-level partner `all_outputs_comm` already has a unit test, as do
the three *non-decisive* flow-step matchers (`inputs_vary`,
`intra_pair_grids_differ`, `pair_grid_count_majority`) — but this gating matcher
had none. This file closes that asymmetry.

As with the sibling matcher tests, the positive and value-agnostic cases are
driven end-to-end through `compare_scheduler.build_patterns` over *real* Pair /
Grid nodes (the Slice-1 shape: two complete example pairs + one test pair missing
its output), so the matcher is exercised against the real census shape
`pair_grid_counts()` produces, not a fabricated one. The fail-closed / edge cases
use hand-built censuses since they describe malformed inputs a producer would
never emit.

pytest is not installed in this environment, so the file is also runnable
directly:  python tests/test_conditions_test_output_missing.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ARCKG.grid import Grid
from ARCKG.pair import Pair
from agent.conditions import CONDITION_REGISTRY, match
import agent.conditions.test_output_missing  # noqa: F401 (ensures registration)
from agent import compare_scheduler as cs


# --- fixtures --------------------------------------------------------------

ROWS = [[0, 0, 0, 0, 0, 0] for _ in range(6)]


def _grid(node_id):
    return Grid(node_id, [row[:] for row in ROWS])


def _complete_pair(idx):
    """An example pair: input + output present -> grid_count 2."""
    return Pair(f"T.P{idx}", _grid(f"T.P{idx}.G0"), _grid(f"T.P{idx}.G1"))


def _input_only_pair(idx):
    """A test pair: input only -> grid_count 1."""
    return Pair(f"T.P{idx}", _grid(f"T.P{idx}.G0"), None)


class _Task:
    """Minimal task carrying the example/test pair split build_patterns needs."""
    def __init__(self, example_pairs, test_pairs):
        self.example_pairs = example_pairs
        self.test_pairs = test_pairs


# --- tests -----------------------------------------------------------------

def test_registry_populated():
    assert "test_output_missing" in CONDITION_REGISTRY


def test_fires_on_two_examples_plus_test_endtoend():
    # The Slice-1 shape: P0(2), P1(2) examples + Pa(1) test. Driven through the
    # real module-C producer so the census shape is the one solve() consumes.
    task = _Task([_complete_pair(0), _complete_pair(1)], [_input_only_pair(2)])
    patterns = cs.build_patterns(task)
    assert patterns["pair_grid_counts"] == {
        "example_counts": [2, 2],
        "test_counts": [1],
    }
    assert match("test_output_missing", patterns) is True


def test_fires_on_single_example_plus_test():
    # min_evidence defaults to 1: one complete example + one input-only test is
    # enough to recognise the construct-the-output regime.
    task = _Task([_complete_pair(0)], [_input_only_pair(1)])
    patterns = cs.build_patterns(task)
    assert match("test_output_missing", patterns) is True


def test_value_agnostic_ignores_colours():
    # Recolour every grid: grid_count is unchanged, so the census (and the
    # match) must be identical -> proves no colour/coordinate value is consulted.
    ex0, ex1, test = _complete_pair(0), _complete_pair(1), _input_only_pair(2)
    for p in (ex0, ex1, test):
        if p.input_grid is not None:
            p.input_grid.raw[0][0] = 7
        if p.output_grid is not None:
            p.output_grid.raw[3][3] = 4
    patterns = cs.build_patterns(_Task([ex0, ex1], [test]))
    assert match("test_output_missing", patterns) is True


def test_does_not_fire_when_test_has_output():
    # Test pair carries an output too (grid_count 2): there is nothing missing to
    # construct, so the construct-the-output regime must NOT be recognised.
    task = _Task([_complete_pair(0), _complete_pair(1)], [_complete_pair(2)])
    patterns = cs.build_patterns(task)
    assert patterns["pair_grid_counts"]["test_counts"] == [2]
    assert match("test_output_missing", patterns) is False


def test_does_not_fire_when_no_test_pair():
    # No test pair at all -> empty test_counts -> nothing to construct -> False
    # (fail-closed: all() over an empty list is vacuously True, but the matcher
    # must require >= 1 input-only test pair, not zero).
    task = _Task([_complete_pair(0), _complete_pair(1)], [])
    patterns = cs.build_patterns(task)
    assert patterns["pair_grid_counts"]["test_counts"] == []
    assert match("test_output_missing", patterns) is False


def test_does_not_fire_when_example_incomplete():
    # An "example" missing its output (grid_count 1) breaks the complete-examples
    # precondition -> must not fire (we have no complete pair to copy from).
    task = _Task([_complete_pair(0), _input_only_pair(1)], [_input_only_pair(2)])
    patterns = cs.build_patterns(task)
    assert patterns["pair_grid_counts"]["example_counts"] == [2, 1]
    assert match("test_output_missing", patterns) is False


def test_min_evidence_guards_empty_examples():
    # No example pairs -> below min_evidence -> False (and the empty example
    # census also fails the _all_ints non-empty guard).
    patterns = {"pair_grid_counts": {"example_counts": [], "test_counts": [1]}}
    assert match("test_output_missing", patterns) is False


def test_min_evidence_param_respected():
    census = {"pair_grid_counts": {"example_counts": [2], "test_counts": [1]}}
    assert match("test_output_missing", census, {"min_evidence": 1}) is True
    # Demanding two examples when only one is present must fail closed.
    assert match("test_output_missing", census, {"min_evidence": 2}) is False


def test_missing_census_fails_closed():
    assert match("test_output_missing", {}) is False


def test_non_dict_census_fails_closed():
    assert match("test_output_missing", {"pair_grid_counts": "x"}) is False


def test_non_int_counts_fail_closed():
    # bool is an int subclass but must be rejected (mirrors _all_ints posture);
    # string counts are upstream extractor breakage, not evidence.
    assert match(
        "test_output_missing",
        {"pair_grid_counts": {"example_counts": [True, True], "test_counts": [1]}},
    ) is False
    assert match(
        "test_output_missing",
        {"pair_grid_counts": {"example_counts": ["2", "2"], "test_counts": ["1"]}},
    ) is False


if __name__ == "__main__":
    funcs = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in funcs:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {fn.__name__}: {e}")
    print(f"\n{len(funcs) - failed}/{len(funcs)} passed")
    sys.exit(1 if failed else 0)
