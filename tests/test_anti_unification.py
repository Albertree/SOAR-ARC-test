"""
Tests for program/anti_unification.py — the leaf-case anti-unification keystone
specified in docs/ANTI_UNIFICATION.md §1–§3.

These prove that unify() lifts skeleton-sharing rules into one abstract rule
with ?vN variables, rejects skeleton mismatches, and writes a conformant trace.
"""

import json
import os
import re

import pytest

from program import unify, UnifyResult, NoCommonSkeleton
from program.anti_unification import anti_unify


# V5 trace-path regex from docs/RULE_FORMAT.md §1.
_V5 = re.compile(r"^episodic_memory/.+/anti_unification/.+\.json$")


def _rule(rid, *, cond_type="object_motion", dsl="place_object",
          params=None, args=None, min_evidence=2, covers=None,
          source_task="00000001", concept="c", category="other"):
    """Build a RULE_FORMAT-conformant rule dict for tests."""
    return {
        "id": rid,
        "concept": concept,
        "category": category,
        "condition": {
            "type": cond_type,
            "params": params if params is not None else {},
            "min_evidence": min_evidence,
        },
        "action": {
            "dsl": dsl,
            "args": args if args is not None else {},
        },
        "covers": covers if covers is not None else [source_task],
        "source_task": source_task,
        "anti_unification_trace": None,
        "created_at": "2026-06-14T00:00:00",
        "times_reused": 0,
    }


# ----------------------------------------------------------------------
# Skeleton guards
# ----------------------------------------------------------------------

def test_fewer_than_two_rules_raises(tmp_path):
    with pytest.raises(NoCommonSkeleton):
        unify([_rule(1)], episodic_memory_root=str(tmp_path))


def test_condition_type_mismatch_raises(tmp_path):
    a = _rule(1, cond_type="object_motion")
    b = _rule(2, cond_type="constant_output")
    with pytest.raises(NoCommonSkeleton):
        unify([a, b], episodic_memory_root=str(tmp_path))


def test_action_dsl_mismatch_raises(tmp_path):
    a = _rule(1, dsl="coloring")
    b = _rule(2, dsl="make_grid")
    with pytest.raises(NoCommonSkeleton) as exc:
        unify([a, b], episodic_memory_root=str(tmp_path))
    assert "action.dsl" in str(exc.value)


# ----------------------------------------------------------------------
# Leaf-case lifting
# ----------------------------------------------------------------------

def test_disagreeing_arg_is_lifted_to_variable(tmp_path):
    a = _rule(1, args={"color": 3, "selection": "all"}, covers=["00000001"])
    b = _rule(2, args={"color": 5, "selection": "all"}, covers=["00000002"])
    res = unify([a, b], episodic_memory_root=str(tmp_path))

    assert isinstance(res, UnifyResult)
    assert res.is_more_general()
    # 'color' differs -> lifted; 'selection' agrees -> kept verbatim.
    assert res.abstract_rule["action"]["args"]["color"] == "?v1"
    assert res.abstract_rule["action"]["args"]["selection"] == "all"
    assert res.substitutions == {"action.args.color": "?v1"}


def test_identical_rules_are_not_more_general_and_write_no_trace(tmp_path):
    a = _rule(1, args={"color": 3}, covers=["00000001"])
    b = _rule(2, args={"color": 3}, covers=["00000002"])
    res = unify([a, b], episodic_memory_root=str(tmp_path))

    assert not res.is_more_general()
    assert res.substitutions == {}
    assert res.trace_path is None
    # No trace directory should have been created.
    assert not (tmp_path / "00000002").exists()


def test_key_absent_from_some_input_is_a_disagreement(tmp_path):
    a = _rule(1, args={"color": 3, "offset": 1})
    b = _rule(2, args={"color": 3})  # 'offset' missing
    res = unify([a, b], episodic_memory_root=str(tmp_path))

    assert "action.args.offset" in res.substitutions
    assert res.abstract_rule["action"]["args"]["offset"].startswith("?v")
    assert res.abstract_rule["action"]["args"]["color"] == 3


def test_condition_params_are_lifted_too(tmp_path):
    a = _rule(1, params={"k": 1})
    b = _rule(2, params={"k": 2})
    res = unify([a, b], episodic_memory_root=str(tmp_path))
    assert res.substitutions == {"condition.params.k": "?v1"}
    assert res.abstract_rule["condition"]["params"]["k"] == "?v1"


def test_variables_number_sequentially_across_field_groups(tmp_path):
    a = _rule(1, params={"k": 1}, args={"color": 3})
    b = _rule(2, params={"k": 2}, args={"color": 5})
    res = unify([a, b], episodic_memory_root=str(tmp_path))
    # condition.params first, then action.args.
    assert res.substitutions == {
        "condition.params.k": "?v1",
        "action.args.color": "?v2",
    }


# ----------------------------------------------------------------------
# Recursive descent into nested sequence terms (synthesized programs)
# ----------------------------------------------------------------------

def test_nested_sequence_term_lifts_only_the_divergent_leaf(tmp_path):
    # Two synthesizer programs (lists of step tuples) that share the
    # make_grid+paint_objects skeleton but differ only in the fitted output dim.
    # unify() must descend and lift just the divergent leaves — preserving the
    # skeleton — not collapse the whole program to one opaque ?v.
    progA = [("make_grid", ("const", 6), ("const", 6), ("bg",)),
             ("paint_objects", ("all_objects",))]
    progB = [("make_grid", ("const", 5), ("const", 5), ("bg",)),
             ("paint_objects", ("all_objects",))]
    a = _rule(1, cond_type="synthesized_program", dsl="run_program",
              args={"program": progA})
    b = _rule(2, cond_type="synthesized_program", dsl="run_program",
              args={"program": progB})
    res = unify([a, b], episodic_memory_root=str(tmp_path))

    assert res.is_more_general()
    abstract = res.abstract_rule["action"]["args"]["program"]
    # Skeleton preserved; only the two dim leaves became variables.
    assert abstract == [
        ["make_grid", ["const", "?v1"], ["const", "?v2"], ["bg"]],
        ["paint_objects", ["all_objects"]],
    ]
    # Substitution paths point at the exact divergent leaves.
    assert res.substitutions == {
        "action.args.program[0][1][1]": "?v1",
        "action.args.program[0][2][1]": "?v2",
    }


def test_identical_nested_sequence_terms_are_not_more_general(tmp_path):
    # Same program written with tuples (in-memory) vs lists (JSON round-trip)
    # must compare equal: a plain covers merge, no lift, no trace.
    prog_tuples = [("make_grid", ("const", 4), ("const", 4), ("bg",)),
                   ("paint_objects", ("all_objects",))]
    prog_lists = [["make_grid", ["const", 4], ["const", 4], ["bg"]],
                  ["paint_objects", ["all_objects"]]]
    a = _rule(1, cond_type="synthesized_program", dsl="run_program",
              args={"program": prog_tuples})
    b = _rule(2, cond_type="synthesized_program", dsl="run_program",
              args={"program": prog_lists})
    res = unify([a, b], episodic_memory_root=str(tmp_path))
    assert not res.is_more_general()
    assert res.trace_path is None


def test_dict_valued_position_still_lifts_whole(tmp_path):
    # Descent is sequence-only: a dict-valued descriptor (object_motion's target)
    # that differs is lifted whole to a single ?v, NOT descended key-wise — the
    # family rules' abstractions are unchanged by this iter's program-term descent.
    a = _rule(1, args={"target": {"kind": "bottom_right"}})
    b = _rule(2, args={"target": {"kind": "constant", "pos": [5, 5]}})
    res = unify([a, b], episodic_memory_root=str(tmp_path))
    assert res.abstract_rule["action"]["args"]["target"] == "?v1"
    assert res.substitutions == {"action.args.target": "?v1"}


def test_unequal_length_sequences_lift_whole(tmp_path):
    # Ragged sequences have no shared skeleton to descend into → lift whole.
    a = _rule(1, args={"target": ["corner"]})
    b = _rule(2, args={"target": ["const", 5, 5]})
    res = unify([a, b], episodic_memory_root=str(tmp_path))
    assert res.abstract_rule["action"]["args"]["target"] == "?v1"


# ----------------------------------------------------------------------
# Skeleton + bookkeeping fields
# ----------------------------------------------------------------------

def test_skeleton_fields_copied_through(tmp_path):
    a = _rule(1, cond_type="object_motion", dsl="place_object", args={"x": 1})
    b = _rule(2, cond_type="object_motion", dsl="place_object", args={"x": 2})
    res = unify([a, b], episodic_memory_root=str(tmp_path))
    assert res.abstract_rule["condition"]["type"] == "object_motion"
    assert res.abstract_rule["action"]["dsl"] == "place_object"


def test_min_evidence_takes_the_strictest(tmp_path):
    a = _rule(1, min_evidence=2, args={"x": 1})
    b = _rule(2, min_evidence=5, args={"x": 2})
    res = unify([a, b], episodic_memory_root=str(tmp_path))
    assert res.abstract_rule["condition"]["min_evidence"] == 5


def test_covers_union_preserves_first_seen_order(tmp_path):
    a = _rule(1, args={"x": 1}, covers=["00000001", "00000003"])
    b = _rule(2, args={"x": 2}, covers=["00000003", "00000002"])
    res = unify([a, b], episodic_memory_root=str(tmp_path))
    assert res.abstract_rule["covers"] == ["00000001", "00000003", "00000002"]


def test_template_fields_from_last_input(tmp_path):
    a = _rule(1, args={"x": 1}, source_task="00000001", concept="first")
    b = _rule(2, args={"x": 2}, source_task="00000002", concept="second")
    res = unify([a, b], episodic_memory_root=str(tmp_path))
    assert res.abstract_rule["source_task"] == "00000002"
    assert res.abstract_rule["concept"] == "second"
    assert res.abstract_rule["times_reused"] == 0


def test_no_aliasing_leaks_for_container_values(tmp_path):
    shared = {"nested": [1, 2, 3]}
    a = _rule(1, args={"box": shared, "x": 1})
    b = _rule(2, args={"box": {"nested": [1, 2, 3]}, "x": 2})
    res = unify([a, b], episodic_memory_root=str(tmp_path))
    # box agrees -> kept, but must be a deep copy (mutating output won't touch input).
    res.abstract_rule["action"]["args"]["box"]["nested"].append(99)
    assert shared["nested"] == [1, 2, 3]


# ----------------------------------------------------------------------
# Trace JSON
# ----------------------------------------------------------------------

def test_trace_written_with_expected_shape(tmp_path):
    a = _rule(1, args={"color": 3}, source_task="00000001")
    b = _rule(2, args={"color": 5}, source_task="00000002")
    res = unify([a, b], episodic_memory_root=str(tmp_path))

    assert res.trace_path is not None
    on_disk = tmp_path / "00000002" / "anti_unification" / "au_001.json"
    assert on_disk.exists()
    trace = json.loads(on_disk.read_text())
    assert trace["skeleton"] == {
        "condition_type": "object_motion", "action_dsl": "place_object"
    }
    assert trace["substitutions"] == {"action.args.color": "?v1"}
    assert trace["var_count"] == 1
    assert trace["input_rules"] == [
        {"id": 1, "source_task": "00000001"},
        {"id": 2, "source_task": "00000002"},
    ]


def test_trace_sequence_number_increments(tmp_path):
    a = _rule(1, args={"color": 3}, source_task="00000002")
    b = _rule(2, args={"color": 5}, source_task="00000002")
    unify([a, b], episodic_memory_root=str(tmp_path))
    res2 = unify([a, b], episodic_memory_root=str(tmp_path))
    assert res2.trace_path.endswith("au_002.json")
    assert (tmp_path / "00000002" / "anti_unification" / "au_002.json").exists()


def test_trace_path_matches_v5_regex_under_default_root(tmp_path, monkeypatch):
    # Run with the canonical root so the returned path begins "episodic_memory/".
    monkeypatch.chdir(tmp_path)
    a = _rule(1, args={"color": 3}, source_task="00000001")
    b = _rule(2, args={"color": 5}, source_task="00000002")
    res = unify([a, b])  # default episodic_memory_root="episodic_memory"
    assert _V5.match(res.trace_path), res.trace_path


def test_anti_unify_alias_is_unify():
    assert anti_unify is unify
