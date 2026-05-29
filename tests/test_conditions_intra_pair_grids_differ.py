"""
Tests for the `intra_pair_grids_differ` condition matcher (agent/conditions/)
and its producer agent/compare_scheduler.py:intra_pair_grid_comparisons().

These build *real* ARCKG.compare() receipts from real grids (the Slice-1
targets easy000a / easy000a2 plus an identity case) so the matcher is exercised
against the actual receipt shape, not a fabricated one.

pytest is not installed in this environment, so the file is also runnable
directly:  python tests/test_conditions_intra_pair_grids_differ.py
"""

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ARCKG.grid import Grid
from ARCKG.pair import Pair
from ARCKG.comparison import compare
from agent import compare_scheduler as cs
from agent.conditions import CONDITION_REGISTRY, match
import agent.conditions.intra_pair_grids_differ  # noqa: F401  (ensures registration)


# --- fixtures -------------------------------------------------------------

# easy000a: input has red(2) at (1,1); output has red(2) at (5,5). Same 6x6
# size and same colour set {0,2}, but contents differ -> overall DIFF.
A_IN_P0 = [[0] * 6 for _ in range(6)]
A_IN_P0[1][1] = 2
A_IN_P1 = [[0] * 6 for _ in range(6)]
A_IN_P1[1][4] = 1
A_OUT = [[0] * 6 for _ in range(6)]
A_OUT[5][5] = 2
A_IN_TEST = [[0] * 6 for _ in range(6)]
A_IN_TEST[4][2] = 4

# easy000a2: same mechanism, different fixed output — green(3) at (0,0).
A2_OUT = [[0] * 6 for _ in range(6)]
A2_OUT[0][0] = 3


def _grid(node_id, raw):
    return Grid(node_id, [row[:] for row in raw])


def _pair(pid, in_raw, out_raw=None):
    out = _grid(f"{pid}.G1", out_raw) if out_raw is not None else None
    return Pair(pid, _grid(f"{pid}.G0", in_raw), out)


def _task(task_hex, example_pairs, test_pairs):
    return SimpleNamespace(
        task_hex=task_hex,
        example_pairs=example_pairs,
        test_pairs=test_pairs,
    )


def _easy000a_task():
    return _task(
        "easy000a",
        [_pair("T.P0", A_IN_P0, A_OUT), _pair("T.P1", A_IN_P1, A_OUT)],
        [_pair("T.Pa", A_IN_TEST)],
    )


def _easy000a2_task():
    return _task(
        "easy000a2",
        [_pair("T.P0", A_IN_P0, A2_OUT), _pair("T.P1", A_IN_P1, A2_OUT)],
        [_pair("T.Pa", A_IN_TEST)],
    )


def _identity_task():
    # Output identical to input within each pair -> intra comparison is COMM.
    return _task(
        "identity0",
        [_pair("T.P0", A_IN_P0, A_IN_P0), _pair("T.P1", A_IN_P1, A_IN_P1)],
        [_pair("T.Pa", A_IN_TEST)],
    )


# --- registration ---------------------------------------------------------

def test_registry_populated():
    assert "intra_pair_grids_differ" in CONDITION_REGISTRY


# --- producer (module C, Intra kind) --------------------------------------

def test_producer_one_receipt_per_example_pair():
    recs = cs.intra_pair_grid_comparisons(_easy000a_task())
    # Two complete example pairs -> one G0↔G1 comparison each. Test pair (G0
    # only) has no sibling and is naturally skipped.
    assert len(recs) == 2


def test_producer_receipts_are_diff_for_easy000a():
    recs = cs.intra_pair_grid_comparisons(_easy000a_task())
    assert all(r["result"]["type"] == "DIFF" for r in recs)


def test_build_patterns_carries_intra_key():
    patterns = cs.build_patterns(_easy000a_task())
    assert "intra_pair_grid_comparisons" in patterns
    assert len(patterns["intra_pair_grid_comparisons"]) == 2


# --- matcher --------------------------------------------------------------

def test_fires_for_easy000a_via_build_patterns():
    patterns = cs.build_patterns(_easy000a_task())
    assert match("intra_pair_grids_differ", patterns) is True


def test_value_agnostic_easy000a2():
    # A different fixed output must also fire — proves no hard-coded answer.
    patterns = cs.build_patterns(_easy000a2_task())
    assert match("intra_pair_grids_differ", patterns) is True


def test_required_property_contents_diff():
    patterns = cs.build_patterns(_easy000a_task())
    params = {"required_properties": ["contents"]}
    assert match("intra_pair_grids_differ", patterns, params) is True


def test_does_not_fire_for_identity():
    # G0 == G1 within each pair -> COMM, not DIFF -> must not fire.
    recs = cs.intra_pair_grid_comparisons(_identity_task())
    assert all(r["result"]["type"] == "COMM" for r in recs)
    patterns = cs.build_patterns(_identity_task())
    assert match("intra_pair_grids_differ", patterns) is False


def test_min_evidence_guards_empty():
    assert match("intra_pair_grids_differ", {"intra_pair_grid_comparisons": []}) is False
    assert match("intra_pair_grids_differ", {}) is False


def test_all_must_be_diff():
    # One DIFF + one COMM receipt -> not all DIFF -> False.
    diff = compare(_grid("T.P0.G0", A_IN_P0), _grid("T.P0.G1", A_OUT))
    comm = compare(_grid("T.P1.G0", A_IN_P1), _grid("T.P1.G1", A_IN_P1))
    assert diff["result"]["type"] == "DIFF"
    assert comm["result"]["type"] == "COMM"
    patterns = {"intra_pair_grid_comparisons": [diff, comm]}
    assert match("intra_pair_grids_differ", patterns) is False


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
        except Exception as e:  # noqa: BLE001 — surface unexpected errors too
            failed += 1
            print(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(funcs) - failed}/{len(funcs)} passed")
    sys.exit(1 if failed else 0)
