"""
Tests for the `all_outputs_comm` condition matcher (agent/conditions/).

These build *real* ARCKG.compare() receipts from real grids (the Slice-1
targets easy000a / easy000a2 plus an easy000b-style differing-output case) so
the matcher is exercised against the actual receipt shape, not a fabricated one.

pytest is not installed in this environment, so the file is also runnable
directly:  python tests/test_conditions_all_outputs_comm.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ARCKG.grid import Grid
from ARCKG.comparison import compare
from agent.conditions import CONDITION_REGISTRY, match
import agent.conditions.all_outputs_comm  # noqa: F401  (ensures registration)


# --- fixtures: grids straight from the slice tasks -----------------------

# easy000a: every example output is the same — red(2) at (5,5) on a 6x6 black.
EASY000A_OUT = [
    [0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 2],
]

# easy000a2: same MECHANISM, DIFFERENT fixed output — green(3) at (0,0).
EASY000A2_OUT = [
    [3, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0],
]

# easy000b-style: outputs differ across pairs (colour follows each input).
B_OUT_P0 = [
    [0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 2],
]
B_OUT_P1 = [
    [0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 1],
]


def _grid(node_id, raw):
    return Grid(node_id, [row[:] for row in raw])


def _output_comparison(raw_p0, raw_p1):
    """Build the role-aligned Inter-Grid receipt comparing two example G1s."""
    g_a = _grid("T.P0.G1", raw_p0)
    g_b = _grid("T.P1.G1", raw_p1)
    return compare(g_a, g_b)


# --- tests ----------------------------------------------------------------

def test_registry_populated():
    assert "all_outputs_comm" in CONDITION_REGISTRY


def test_identical_outputs_match_easy000a():
    rec = _output_comparison(EASY000A_OUT, EASY000A_OUT)
    assert rec["result"]["type"] == "COMM"
    patterns = {"output_grid_comparisons": [rec]}
    assert match("all_outputs_comm", patterns) is True


def test_value_agnostic_easy000a2():
    # A *different* fixed output must also match — proves no hard-coded answer.
    rec = _output_comparison(EASY000A2_OUT, EASY000A2_OUT)
    patterns = {"output_grid_comparisons": [rec]}
    assert match("all_outputs_comm", patterns) is True


def test_required_properties_size_color_contents():
    rec = _output_comparison(EASY000A_OUT, EASY000A_OUT)
    patterns = {"output_grid_comparisons": [rec]}
    params = {"required_properties": ["size", "color", "contents"]}
    assert match("all_outputs_comm", patterns, params) is True


def test_differing_outputs_do_not_match_easy000b():
    rec = _output_comparison(B_OUT_P0, B_OUT_P1)
    assert rec["result"]["type"] == "DIFF"
    patterns = {"output_grid_comparisons": [rec]}
    assert match("all_outputs_comm", patterns) is False


def test_min_evidence_guards_empty():
    # No comparisons -> must not fire (cannot conclude "all COMM" from nothing).
    assert match("all_outputs_comm", {"output_grid_comparisons": []}) is False
    assert match("all_outputs_comm", {}) is False


def test_unknown_matcher_returns_false():
    assert match("no_such_matcher", {"output_grid_comparisons": []}) is False


def test_all_must_be_comm():
    # One COMM + one DIFF receipt -> not all COMM -> False.
    comm = _output_comparison(EASY000A_OUT, EASY000A_OUT)
    diff = _output_comparison(B_OUT_P0, B_OUT_P1)
    patterns = {"output_grid_comparisons": [comm, diff]}
    assert match("all_outputs_comm", patterns) is False


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
