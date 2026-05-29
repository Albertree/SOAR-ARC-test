"""
Tests for module B — agent/goal.py (GoalStack with Evolution, Slice-1 scope).

Exercises the two evolution rules (Refinement value→action, Decomposition
action→schema) and the GoalStack chain that the easy000a flow walks:

    grid-count census  →  PAIR-level value goal
                       →  (refine)   action goal "construct Gx"
                       →  (decompose) schema goal {size, color, contents}

The key Slice-1 property is **value-agnosticism** (SLICE_1_LOOP.md §9): the goal
tree is built from structural grid counts and property *names* only, so the
easy000a (red output) and easy000a2 (green output) censuses — which are
structurally identical — must yield byte-identical goal trees. A test asserts
exactly that, so a future value leak would fail here.

pytest is not installed here, so the file is also runnable directly:
    python tests/test_goal.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import goal as G


# --- censuses: both Slice-1 targets have 2 complete examples + 1 deficient test
# (structurally identical regardless of the output colour — the whole point).
CENSUS_A = {"example_counts": [2, 2], "test_counts": [1]}
CENSUS_A2 = {"example_counts": [2, 2], "test_counts": [1]}


# --- value-goal construction from the census -----------------------------

def test_value_goal_from_census_flags_deficient_test_pair():
    g = G.value_goal_from_grid_count_census(CENSUS_A)
    assert g is not None
    assert g["kind"] == G.KIND_VALUE
    assert g["property"] == "grid_count"
    assert g["target_count"] == 2          # the example majority, derived
    assert g["deficient_test_pairs"] == [0]
    assert g["status"] == G.STATUS_OPEN


def test_value_goal_none_when_no_deficiency():
    # test pair already has the majority count -> nothing to construct
    g = G.value_goal_from_grid_count_census(
        {"example_counts": [2, 2], "test_counts": [2]})
    assert g is None


def test_value_goal_none_when_no_examples():
    g = G.value_goal_from_grid_count_census(
        {"example_counts": [], "test_counts": [1]})
    assert g is None


def test_value_goal_carries_no_colour_or_coordinate():
    # value-agnostic: serialised goal must mention no colour/coord vocabulary
    blob = json.dumps(G.value_goal_from_grid_count_census(CENSUS_A))
    for banned in ("color", "red", "green", "coord", "(5, 5)", "(0, 0)"):
        assert banned not in blob


# --- Refinement: value -> action -----------------------------------------

def test_refine_value_to_action():
    value = G.value_goal_from_grid_count_census(CENSUS_A)
    action = G.refine_value_to_action(value)
    assert action["kind"] == G.KIND_ACTION
    assert action["verb"] == "construct"
    assert action["target"] == "Gx"
    assert action["in_test_pairs"] == [0]
    assert action["from_property"] == "grid_count"
    assert action["status"] == G.STATUS_OPEN


def test_refine_rejects_non_value_goal():
    try:
        G.refine_value_to_action({"kind": G.KIND_ACTION})
    except ValueError:
        return
    raise AssertionError("expected ValueError refining a non-value goal")


# --- Decomposition: action -> schema -------------------------------------

def test_decompose_action_over_grid_schema():
    action = G.refine_value_to_action(
        G.value_goal_from_grid_count_census(CENSUS_A))
    schema_goal = G.decompose_action(action)
    assert schema_goal["kind"] == G.KIND_SCHEMA
    assert set(schema_goal["subgoals"]) == {"size", "color", "contents"}
    for prop, child in schema_goal["subgoals"].items():
        assert child["status"] == G.STATUS_OPEN
        assert child["determine"] == f"Gx.{prop}"
    assert schema_goal["in_test_pairs"] == [0]


def test_decompose_rejects_non_action_goal():
    try:
        G.decompose_action({"kind": G.KIND_VALUE})
    except ValueError:
        return
    raise AssertionError("expected ValueError decomposing a non-action goal")


def test_decompose_rejects_empty_schema():
    action = G.refine_value_to_action(
        G.value_goal_from_grid_count_census(CENSUS_A))
    try:
        G.decompose_action(action, schema=())
    except ValueError:
        return
    raise AssertionError("expected ValueError on empty schema")


# --- evolve() dispatch ----------------------------------------------------

def test_evolve_dispatches_by_kind():
    value = G.value_goal_from_grid_count_census(CENSUS_A)
    action = G.evolve(value)
    assert action["kind"] == G.KIND_ACTION
    schema_goal = G.evolve(action)
    assert schema_goal["kind"] == G.KIND_SCHEMA
    # schema goal is terminal for evolution
    assert G.evolve(schema_goal) is schema_goal


# --- GoalStack chain ------------------------------------------------------

def test_goalstack_full_chain_and_satisfaction():
    stack = G.GoalStack(G.value_goal_from_grid_count_census(CENSUS_A))
    assert stack.current["kind"] == G.KIND_VALUE
    assert not stack.is_satisfied()

    stack.advance()                       # value -> action
    assert stack.current["kind"] == G.KIND_ACTION

    stack.advance()                       # action -> schema
    assert stack.current["kind"] == G.KIND_SCHEMA
    assert not stack.is_satisfied()

    # history records the two prior forms, in order
    assert [g["kind"] for g in stack.history] == [G.KIND_VALUE, G.KIND_ACTION]

    # solving each property satisfies the schema goal
    for prop in ("size", "color", "contents"):
        assert not stack.is_satisfied()
        stack.mark_property_solved(prop)
    assert stack.is_satisfied()


def test_goalstack_advance_is_noop_at_terminal():
    stack = G.GoalStack(G.value_goal_from_grid_count_census(CENSUS_A))
    stack.advance()
    stack.advance()
    depth = len(stack.history)
    # advancing a terminal (schema) goal changes nothing
    stack.advance()
    assert len(stack.history) == depth
    assert stack.current["kind"] == G.KIND_SCHEMA


def test_goalstack_requires_goal_node():
    for bad in (None, {}, {"no_kind": 1}, 42):
        try:
            G.GoalStack(bad)
        except ValueError:
            continue
        raise AssertionError(f"expected ValueError for {bad!r}")


def test_to_json_is_serialisable():
    stack = G.GoalStack(G.value_goal_from_grid_count_census(CENSUS_A))
    stack.advance()
    stack.advance()
    blob = json.dumps(stack.to_json())          # must not raise
    assert "subgoals" in blob


# --- value-agnosticism: easy000a vs easy000a2 produce identical trees -----

def test_goal_tree_identical_across_targets():
    def tree(census):
        s = G.GoalStack(G.value_goal_from_grid_count_census(census))
        s.advance()
        s.advance()
        return s.to_json()
    assert tree(CENSUS_A) == tree(CENSUS_A2)


# --- the Slice-1 goal walk built straight from a patterns bundle ----------
# build_goalstack_from_census + mark_schema_leaves_by_comparison are the
# module-B library functions ActiveSoarAgent now delegates to (extracted from
# its inlined goal walk). They are exercised here on their own so module B's
# walk is guarded independent of the agent.

def _comm_receipt(props):
    """A compare() receipt whose per-property category carries the COMM/DIFF
    type for each name in `props` (a {prop: "COMM"|"DIFF"} map)."""
    return {"result": {"type": "COMM", "score": "1/1",
                       "category": {p: {"type": t} for p, t in props.items()}}}

_ALL_COMM = {"size": "COMM", "color": "COMM", "contents": "COMM"}
_CONTENTS_DIFF = {"size": "COMM", "color": "COMM", "contents": "DIFF"}


def test_build_goalstack_from_census_walks_full_chain():
    stack = G.build_goalstack_from_census(CENSUS_A)
    assert stack is not None
    assert stack.current["kind"] == G.KIND_SCHEMA
    assert set(stack.current["subgoals"]) == {"size", "color", "contents"}
    assert [g["kind"] for g in stack.history] == [G.KIND_VALUE, G.KIND_ACTION]
    assert not stack.is_satisfied()           # leaves all open until grounded


def test_build_goalstack_from_census_none_when_no_deficiency():
    assert G.build_goalstack_from_census(
        {"example_counts": [2, 2], "test_counts": [2]}) is None


def test_mark_schema_leaves_all_comm_satisfies():
    stack = G.build_goalstack_from_census(CENSUS_A)
    patterns = {"output_grid_comparisons": [_comm_receipt(_ALL_COMM)]}
    G.mark_schema_leaves_by_comparison(stack, patterns)
    assert stack.is_satisfied()               # every property has a COMM basis
    for child in stack.current["subgoals"].values():
        assert child["status"] == G.STATUS_SOLVED


def test_mark_schema_leaves_leaves_uncompared_property_open():
    """A property the role-aligned comparison did not settle (contents DIFF)
    stays open even though size/color are COMM (P3/P4 — basis, not blanket)."""
    stack = G.build_goalstack_from_census(CENSUS_A)
    patterns = {"output_grid_comparisons": [_comm_receipt(_CONTENTS_DIFF)]}
    G.mark_schema_leaves_by_comparison(stack, patterns)
    subs = stack.current["subgoals"]
    assert subs["size"]["status"] == G.STATUS_SOLVED
    assert subs["color"]["status"] == G.STATUS_SOLVED
    assert subs["contents"]["status"] == G.STATUS_OPEN
    assert not stack.is_satisfied()


def test_mark_schema_leaves_no_basis_leaves_all_open():
    # no comparison receipts -> all_outputs_comm cannot fire -> nothing settled
    stack = G.build_goalstack_from_census(CENSUS_A)
    G.mark_schema_leaves_by_comparison(stack, {"output_grid_comparisons": []})
    for child in stack.current["subgoals"].values():
        assert child["status"] == G.STATUS_OPEN


def test_goal_walk_from_patterns_value_agnostic():
    """Same structural census + same COMM verdicts -> identical satisfied stack,
    regardless of which colour the (here-absent) literal output would carry."""
    def walk(census):
        s = G.build_goalstack_from_census(census)
        G.mark_schema_leaves_by_comparison(
            s, {"output_grid_comparisons": [_comm_receipt(_ALL_COMM)]})
        return s.to_json()
    assert walk(CENSUS_A) == walk(CENSUS_A2)


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items())
           if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in fns:
        fn()
        passed += 1
        print(f"  ok  {fn.__name__}")
    print(f"\n{passed}/{len(fns)} goal tests passed")
