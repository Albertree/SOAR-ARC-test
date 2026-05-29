"""
Tests for the `inputs_vary` matcher (agent/conditions/inputs_vary.py) and its
producer agent/compare_scheduler.py:input_grid_comparisons().

`inputs_vary` is the role==G0 counterpart to `all_outputs_comm` (role==G1): it
names the §3 contrast step "the example inputs all DIFF" (raw prose easy000a:
"색집합이 모두 다르다"). Together the two matchers cover *both* roles of module
C's single Inter-Grid (Grid-level) analysis kind.

Built on *real* ARCKG Grid nodes and the real ARCKG.compare() so the receipts
are genuine, not synthetic. Strictly value-agnostic: the same matcher fires for
easy000a (red inputs) and easy000a2 (green inputs) — different colours, same
DIFF verdict.

pytest is not installed here, so the file is also runnable directly:
    python tests/test_conditions_inputs_vary.py
"""

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ARCKG.grid import Grid
from ARCKG.pair import Pair
from agent import compare_scheduler as cs
from agent.conditions import match


# --- fixtures --------------------------------------------------------------

def _grid(node_id, raw):
    return Grid(node_id, [row[:] for row in raw])


def _pair(pid, in_raw, out_raw=None):
    out = _grid(f"{pid}.G1", out_raw) if out_raw is not None else None
    return Pair(pid, _grid(f"{pid}.G0", in_raw), out)


def _task(task_hex, example_pairs, test_pairs):
    return SimpleNamespace(
        task_hex=task_hex, example_pairs=example_pairs, test_pairs=test_pairs)


def _blank():
    return [[0] * 6 for _ in range(6)]


def _easy000a_task():
    # inputs differ across pairs (red@(1,1) vs blue@(1,4)); fixed red output.
    p0_in = _blank(); p0_in[1][1] = 2
    p1_in = _blank(); p1_in[1][4] = 1
    out = _blank(); out[5][5] = 2
    test_in = _blank(); test_in[4][2] = 4
    return _task("easy000a",
                 [_pair("T.P0", p0_in, out), _pair("T.P1", p1_in, out)],
                 [_pair("T.Pa", test_in)])


def _easy000a2_task():
    # value-agnostic twin: different colours, same DIFF-inputs structure.
    p0_in = _blank(); p0_in[2][2] = 3
    p1_in = _blank(); p1_in[0][3] = 8
    out = _blank()  # fixed green output elsewhere; irrelevant to inputs_vary
    out[0][0] = 3
    test_in = _blank(); test_in[5][1] = 6
    return _task("easy000a2",
                 [_pair("T.P0", p0_in, out), _pair("T.P1", p1_in, out)],
                 [_pair("T.Pa", test_in)])


def _identical_inputs_task():
    # degenerate: both example inputs identical -> inputs_vary must NOT fire.
    same_in = _blank(); same_in[1][1] = 2
    out = _blank(); out[5][5] = 2
    return _task("identical",
                 [_pair("T.P0", same_in, out), _pair("T.P1", same_in, out)],
                 [_pair("T.Pa", _blank())])


# --- tests -----------------------------------------------------------------

RESULTS = []


def _check(name, cond):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name)


def test_producer_one_receipt_for_two_examples():
    recs = cs.input_grid_comparisons(_easy000a_task())
    _check("test_producer_one_receipt_for_two_examples", len(recs) == 1)


def test_producer_skips_test_pair_g0():
    # Only example inputs are compared; the test pair's G0 is excluded.
    recs = cs.input_grid_comparisons(_easy000a_task())
    ids = recs[0]["id"]
    _check("test_producer_skips_test_pair_g0",
           "Pa" not in ids["id1"] and "Pa" not in ids["id2"])


def test_fires_diff_for_easy000a():
    patterns = {"input_grid_comparisons":
                cs.input_grid_comparisons(_easy000a_task())}
    _check("test_fires_diff_for_easy000a",
           match("inputs_vary", patterns, {"min_evidence": 1}) is True)


def test_value_agnostic_easy000a2():
    patterns = {"input_grid_comparisons":
                cs.input_grid_comparisons(_easy000a2_task())}
    _check("test_value_agnostic_easy000a2",
           match("inputs_vary", patterns, {"min_evidence": 1}) is True)


def test_required_property_color_diff():
    patterns = {"input_grid_comparisons":
                cs.input_grid_comparisons(_easy000a_task())}
    _check("test_required_property_color_diff",
           match("inputs_vary", patterns,
                 {"min_evidence": 1, "required_properties": ["color"]}) is True)


def test_does_not_fire_for_identical_inputs():
    patterns = {"input_grid_comparisons":
                cs.input_grid_comparisons(_identical_inputs_task())}
    _check("test_does_not_fire_for_identical_inputs",
           match("inputs_vary", patterns, {"min_evidence": 1}) is False)


def test_min_evidence_guard_on_empty():
    _check("test_min_evidence_guard_on_empty",
           match("inputs_vary", {"input_grid_comparisons": []},
                 {"min_evidence": 1}) is False)


def test_non_list_receipts_fail_closed():
    _check("test_non_list_receipts_fail_closed",
           match("inputs_vary", {"input_grid_comparisons": "nope"}) is False)


def test_end_to_end_via_build_patterns():
    patterns = cs.build_patterns(_easy000a_task())
    _check("test_end_to_end_via_build_patterns",
           "input_grid_comparisons" in patterns
           and match("inputs_vary", patterns, {"min_evidence": 1}) is True)


def test_registered_in_registry():
    from agent.conditions import CONDITION_REGISTRY, get
    get("inputs_vary")  # trigger lazy load
    _check("test_registered_in_registry", "inputs_vary" in CONDITION_REGISTRY)


if __name__ == "__main__":
    for fn in list(globals().values()):
        if callable(fn) and getattr(fn, "__name__", "").startswith("test_"):
            fn()
    passed = sum(1 for _, ok in RESULTS if ok)
    total = len(RESULTS)
    print(f"\n{passed}/{total} passed")
    sys.exit(0 if passed == total else 1)
