"""
Tests for the `pair_grid_count_majority` condition matcher (agent/conditions/).

These build *real* ARCKG.compare() receipts from real Pair nodes (the Slice-1
shape: two complete example pairs + one test pair missing its output) so the
matcher is exercised against the actual receipt shape, not a fabricated one.
The whole module-C producer chain is also exercised end-to-end via
compare_scheduler.build_patterns, proving the previously-orphaned
`pair_grid_count_comparisons` family now has a live consumer.

pytest is not installed in this environment, so the file is also runnable
directly:  python tests/test_conditions_pair_grid_count_majority.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ARCKG.grid import Grid
from ARCKG.pair import Pair
from agent.conditions import CONDITION_REGISTRY, match
import agent.conditions.pair_grid_count_majority  # noqa: F401 (ensures registration)
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


def _pair_count_receipts(pairs):
    """Pairwise (P6) PAIR-level grid_count comparison receipts over `pairs`."""
    from itertools import combinations
    return [cs.arckg_compare(a, b) for a, b in combinations(pairs, 2)]


# --- tests -----------------------------------------------------------------

def test_registry_populated():
    assert "pair_grid_count_majority" in CONDITION_REGISTRY


def test_fires_on_two_examples_plus_test():
    # P0(2), P1(2), Pa(1): receipts = COMM, DIFF, DIFF -> consensus + dissent.
    pairs = [_complete_pair(0), _complete_pair(1), _input_only_pair(2)]
    recs = _pair_count_receipts(pairs)
    types = sorted(r["result"]["type"] for r in recs)
    assert types == ["COMM", "DIFF", "DIFF"]
    patterns = {"pair_grid_count_comparisons": recs}
    assert match("pair_grid_count_majority", patterns) is True


def test_fires_via_build_patterns_endtoend():
    # The orphaned producer now has a consumer: drive it through module C.
    task = _Task([_complete_pair(0), _complete_pair(1)], [_input_only_pair(2)])
    patterns = cs.build_patterns(task)
    assert "pair_grid_count_comparisons" in patterns
    assert match("pair_grid_count_majority", patterns) is True


def test_grid_count_property_explicit():
    pairs = [_complete_pair(0), _complete_pair(1), _input_only_pair(2)]
    recs = _pair_count_receipts(pairs)
    patterns = {"pair_grid_count_comparisons": recs}
    params = {"required_properties": ["grid_count"]}
    assert match("pair_grid_count_majority", patterns, params) is True


def test_value_agnostic_ignores_colours():
    # Recolour every grid: grid_count is unchanged, so the verdict structure
    # (and the match) must be identical -> proves no value is consulted.
    pairs = [_complete_pair(0), _complete_pair(1), _input_only_pair(2)]
    for p in pairs:
        if p.input_grid is not None:
            p.input_grid.raw[0][0] = 7
        if p.output_grid is not None:
            p.output_grid.raw[3][3] = 4
    recs = _pair_count_receipts(pairs)
    patterns = {"pair_grid_count_comparisons": recs}
    assert match("pair_grid_count_majority", patterns) is True


def test_all_comm_does_not_fire():
    # Three complete pairs -> all COMM, no dissenter -> must not fire.
    pairs = [_complete_pair(0), _complete_pair(1), _complete_pair(2)]
    recs = _pair_count_receipts(pairs)
    assert all(r["result"]["type"] == "COMM" for r in recs)
    patterns = {"pair_grid_count_comparisons": recs}
    assert match("pair_grid_count_majority", patterns) is False


def test_single_comparison_does_not_fire():
    # One example + one test -> a single DIFF receipt -> below min_evidence.
    pairs = [_complete_pair(0), _input_only_pair(1)]
    recs = _pair_count_receipts(pairs)
    assert len(recs) == 1
    patterns = {"pair_grid_count_comparisons": recs}
    assert match("pair_grid_count_majority", patterns) is False


def test_min_evidence_guards_empty():
    assert match("pair_grid_count_majority", {"pair_grid_count_comparisons": []}) is False
    assert match("pair_grid_count_majority", {}) is False


def test_non_list_payload_fails_closed():
    assert match("pair_grid_count_majority", {"pair_grid_count_comparisons": "x"}) is False


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
