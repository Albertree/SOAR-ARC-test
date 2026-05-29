"""
Tests for module C — agent/compare_scheduler.py (Slice-1 scope).

Exercises the producer against *real* ARCKG Pair/Grid nodes and the real
ARCKG.compare(), then drives the two Slice-1 recognition matchers end-to-end:

  · output_grid_comparisons  -> all_outputs_comm     (GRID-level decider)
  · pair_grid_counts         -> test_output_missing   (PAIR-level trigger)

This is the iter-3 evidence that the previously-dead `all_outputs_comm` matcher
(added iter 2 with no producer) is now live: build_patterns(task) feeds it.

pytest is not installed here, so the file is also runnable directly:
    python tests/test_compare_scheduler.py
"""

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ARCKG.grid import Grid
from ARCKG.pair import Pair
from agent import compare_scheduler as cs
from agent.conditions import match


# --- fixtures: the Slice-1 target tasks, built from real nodes -----------

# easy000a: every example output identical — red(2) at (5,5) on 6x6 black.
A_OUT = [[0] * 6 for _ in range(6)]
A_OUT[5][5] = 2
A_IN_P0 = [[0] * 6 for _ in range(6)]
A_IN_P0[1][1] = 2
A_IN_P1 = [[0] * 6 for _ in range(6)]
A_IN_P1[1][4] = 1
A_IN_TEST = [[0] * 6 for _ in range(6)]
A_IN_TEST[4][2] = 4

# easy000b-style: outputs differ across pairs (colour follows each input).
B_OUT_P0 = [[0] * 6 for _ in range(6)]
B_OUT_P0[5][5] = 2
B_OUT_P1 = [[0] * 6 for _ in range(6)]
B_OUT_P1[5][5] = 1


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


def _easy000b_task():
    return _task(
        "easy000b",
        [_pair("T.P0", A_IN_P0, B_OUT_P0), _pair("T.P1", A_IN_P1, B_OUT_P1)],
        [_pair("T.Pa", A_IN_TEST)],
    )


# --- util / scope selector ------------------------------------------------

def test_pairs_of_orders_examples_then_test():
    task = _easy000a_task()
    pairs = cs.pairs_of(task)
    assert [p.node_id for p in pairs] == ["T.P0", "T.P1", "T.Pa"]


def test_grids_of_role_order():
    task = _easy000a_task()
    grids = cs.grids_of(task.example_pairs[0])
    assert [cs.role_of(g) for g in grids] == ["G0", "G1"]
    # Test pair has only the input grid.
    test_grids = cs.grids_of(task.test_pairs[0])
    assert [cs.role_of(g) for g in test_grids] == ["G0"]


def test_select_grid_level_with_predicate():
    task = _easy000a_task()
    outputs = cs.select(task.example_pairs[0], "grid",
                        predicate=lambda g: cs.role_of(g) == "G1")
    assert [g.node_id for g in outputs] == ["T.P0.G1"]


def test_select_pair_level():
    task = _easy000a_task()
    assert len(cs.select(task, "pair")) == 3


def test_select_unknown_level_raises():
    task = _easy000a_task()
    try:
        cs.select(task, "object")
    except ValueError:
        return
    raise AssertionError("expected ValueError for unsupported level")


# --- comparison scheduling (pairwise, P6) ---------------------------------

def test_output_grid_comparisons_all_comm_for_easy000a():
    recs = cs.output_grid_comparisons(_easy000a_task())
    assert len(recs) == 1  # C(2,2) == 1 pairwise comparison
    assert all(r["result"]["type"] == "COMM" for r in recs)


def test_output_grid_comparisons_diff_for_easy000b():
    recs = cs.output_grid_comparisons(_easy000b_task())
    assert len(recs) == 1
    assert recs[0]["result"]["type"] == "DIFF"


def test_pairwise_count_is_n_choose_2():
    # 3 pairs -> 3 pairwise comparisons (P6: 2-at-a-time, never 3-way).
    recs = cs.pair_grid_count_comparisons(_easy000a_task())
    assert len(recs) == 3


def test_pair_grid_counts_census():
    census = cs.pair_grid_counts(_easy000a_task())
    assert census == {"example_counts": [2, 2], "test_counts": [1]}


# --- grid comparison agenda (what the cycle's compare step executes) ------

def test_grid_comparison_specs_includes_intra_and_deciding_inter():
    specs = cs.grid_comparison_specs(_easy000a_task())
    by_type = {}
    for s in specs:
        by_type.setdefault(s["type"], []).append(s)
    # One Intra-Pair G0↔G1 spec per complete example pair (2 examples).
    assert len(by_type["grid"]) == 2
    assert {s["id1"] for s in by_type["grid"]} == {"T.P0.G0", "T.P1.G0"}
    assert {s["id2"] for s in by_type["grid"]} == {"T.P0.G1", "T.P1.G1"}
    # The deciding Inter-Grid role==G1 comparison: pairwise over example outputs
    # (C(2,2) == 1), comparing the two example G1 grids.
    assert len(by_type["inter_grid_output"]) == 1
    dec = by_type["inter_grid_output"][0]
    assert {dec["id1"], dec["id2"]} == {"T.P0.G1", "T.P1.G1"}
    # The contrast Inter-Grid role==G0 comparison: pairwise over example inputs
    # (C(2,2) == 1), comparing the two example G0 grids.
    assert len(by_type["inter_grid_input"]) == 1
    con = by_type["inter_grid_input"][0]
    assert {con["id1"], con["id2"]} == {"T.P0.G0", "T.P1.G0"}
    # Every spec carries a unique key so receipts never collide on storage.
    keys = [s["key"] for s in specs]
    assert len(keys) == len(set(keys))


def test_grid_comparison_specs_skips_test_pair_intra():
    # The test pair has only G0 — no sibling output — so it produces no Intra
    # spec and is never an Inter output (role==G1) operand.
    specs = cs.grid_comparison_specs(_easy000a_task())
    operand_ids = {s["id1"] for s in specs} | {s["id2"] for s in specs}
    assert "T.Pa.G0" not in operand_ids
    assert "T.Pa.G1" not in operand_ids


def test_pair_comparison_specs_pairwise_over_all_pairs():
    # PAIR-level Inter-Pair grid_count: every pair (examples + test) compared
    # 2-at-a-time -> C(3,2) == 3 specs, all on pair node ids (not grid ids).
    specs = cs.pair_comparison_specs(_easy000a_task())
    assert len(specs) == 3
    assert {s["type"] for s in specs} == {"inter_pair_grid_count"}
    operand_ids = {s["id1"] for s in specs} | {s["id2"] for s in specs}
    assert operand_ids == {"T.P0", "T.P1", "T.Pa"}  # pair ids, incl. the test pair
    keys = [s["key"] for s in specs]
    assert len(keys) == len(set(keys))


def test_comparison_specs_unions_grid_and_pair_with_unique_keys():
    task = _easy000a_task()
    specs = cs.comparison_specs(task)
    # Behaviour-preserving for the answer: the scheduled spec *set* (keyed) is
    # exactly the GRID ∪ PAIR specs; module A only reorders them (descent) and
    # tags each with its level.
    def _bare(s):
        return {k: v for k, v in s.items() if k != "level"}
    expected = cs.grid_comparison_specs(task) + cs.pair_comparison_specs(task)
    by_key = lambda lst: sorted(lst, key=lambda s: s["key"])
    assert by_key([_bare(s) for s in specs]) == by_key(expected)
    keys = [s["key"] for s in specs]
    assert len(keys) == len(set(keys))  # GRID and PAIR key prefixes never collide


def test_comparison_specs_descend_order_pair_before_grid():
    # Module A (P1) builds the agenda top-down TASK→PAIR→GRID, so the PAIR-level
    # Inter-Pair grid_count evidence (the §3 goal-B trigger) is scheduled before
    # the GRID-level deciding Inter-Grid comparison — not the reverse.
    specs = cs.comparison_specs(_easy000a_task())
    levels = [s["level"] for s in specs]
    assert set(levels) == {"pair", "grid"}            # TASK level schedules nothing
    assert levels == sorted(levels, key={"pair": 0, "grid": 1}.get)
    last_pair = max(i for i, lv in enumerate(levels) if lv == "pair")
    first_grid = min(i for i, lv in enumerate(levels) if lv == "grid")
    assert last_pair < first_grid                     # all PAIR specs precede all GRID


def test_comparison_specs_descent_value_agnostic_a_and_b_identical_order():
    # The descent decision reads only the structural sibling census, so the
    # level sequence is identical for easy000a and easy000b (P7, value-agnostic).
    a_levels = [s["level"] for s in cs.comparison_specs(_easy000a_task())]
    b_levels = [s["level"] for s in cs.comparison_specs(_easy000b_task())]
    assert a_levels == b_levels


def test_build_node_lookup_indexes_pairs_and_grids():
    # CompareOperator must resolve both pair ids (PAIR spec) and grid ids (GRID
    # specs); every operand id in the agenda must be present in the lookup.
    task = _easy000a_task()
    lookup = cs.build_node_lookup(task)
    assert {"T.P0", "T.P1", "T.Pa"} <= set(lookup)          # pairs (incl. test)
    assert {"T.P0.G0", "T.P0.G1", "T.Pa.G0"} <= set(lookup)  # grids
    operand_ids = set()
    for s in cs.comparison_specs(task):
        operand_ids.add(s["id1"])
        operand_ids.add(s["id2"])
    assert operand_ids <= set(lookup)


def test_pair_grid_count_majority_lives_via_build_patterns():
    # The PAIR-level recogniser fires on the real Inter-Pair grid_count receipts
    # (consensus among the two complete pairs + a dissenting test pair).
    patterns = cs.build_patterns(_easy000a_task())
    assert match("pair_grid_count_majority", patterns,
                 {"required_properties": ["grid_count"]}) is True


# --- end-to-end: producer feeds the recognition matchers ------------------

def test_all_outputs_comm_lives_via_build_patterns_easy000a():
    patterns = cs.build_patterns(_easy000a_task())
    # The deciding GRID-level recognition fires, on real receipts.
    assert match("all_outputs_comm", patterns,
                 {"required_properties": ["size", "color", "contents"]}) is True


def test_all_outputs_comm_value_agnostic_does_not_fire_easy000b():
    patterns = cs.build_patterns(_easy000b_task())
    assert match("all_outputs_comm", patterns) is False


def test_test_output_missing_fires_for_construct_regime():
    patterns = cs.build_patterns(_easy000a_task())
    assert match("test_output_missing", patterns) is True


def test_test_output_missing_value_agnostic_a_and_b_identical():
    # PAIR-level trigger depends only on structure, so easy000a / b agree.
    assert match("test_output_missing", cs.build_patterns(_easy000a_task())) is True
    assert match("test_output_missing", cs.build_patterns(_easy000b_task())) is True


def test_test_output_missing_rejects_malformed():
    assert match("test_output_missing", {}) is False
    assert match("test_output_missing", {"pair_grid_counts": {}}) is False
    # A test pair that already has an output -> not the construct regime.
    bad = {"pair_grid_counts": {"example_counts": [2, 2], "test_counts": [2]}}
    assert match("test_output_missing", bad) is False
    # bool is not a valid count (V1-style strict-int posture).
    boolish = {"pair_grid_counts": {"example_counts": [True, True], "test_counts": [1]}}
    assert match("test_output_missing", boolish) is False


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
