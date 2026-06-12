"""
Tests for R3 anti-unification on the **canvas_fill** family (BACKLOG_LOOP §2.5-3/4,
CLAUDE.md §8).

`canvas_fill` fills a same-size solid canvas with a learned *colour reading* of
the input (`COLOR_READING_VOCAB`: `most_frequent_color` for the dominant-fill
family, `least_frequent_color` for the minority/foreground-fill family). The
family is value-agnostic at predict (the reading is recomputed off each test
input), so the literal `fill_reading` carried in a concrete rule is pure
self-description. Left un-lifted, each distinct reading accretes its own rule.
These tests pin that two concrete `fill_canvas` rules with *different* readings
lift into one abstract rule (`fill_reading` -> `?v0`, `covers` = union, with an
`anti_unification_trace`), and that the lift is stable across re-saves.
"""

import os

from program import anti_unification
from agent import memory
from agent.dsl_expr.selection import (
    least_frequent_color, most_frequent_color, COLOR_READING_VOCAB,
)


def _concrete_fill_rule(reading):
    return {
        "condition": {"type": "canvas_fill",
                      "params": {"min_evidence": 2}, "min_evidence": 2},
        "action": {"dsl": "fill_canvas", "args": {"fill_reading": reading}},
        "concept": "fill_canvas_with_color_reading",
        "category": "canvas_fill",
    }


def test_least_frequent_color_reads_minority():
    # one minority cell on a dominant background -> the minority colour
    grid = [[0, 0, 0], [0, 5, 0], [0, 0, 0]]
    assert least_frequent_color(grid) == 5
    assert most_frequent_color(grid) == 0
    # ties -> smallest colour; empty -> 0
    assert least_frequent_color([[1, 1, 2, 2]]) == 1
    assert least_frequent_color([]) == 0


def test_vocab_priority_keeps_dominant_first():
    # most_frequent_color must remain the first-tried reading so the dominant-fill
    # family (5582e5ca) is unchanged by adding the minority reading.
    assert list(COLOR_READING_VOCAB) == [
        "most_frequent_color", "least_frequent_color"]


def test_unify_lifts_two_fill_readings():
    res = anti_unification.unify([
        _concrete_fill_rule("most_frequent_color"),
        _concrete_fill_rule("least_frequent_color"),
    ])
    assert res is not None
    assert res.is_more_general()
    ar = res.abstract_rule
    assert ar["action"]["dsl"] == "fill_canvas"
    assert ar["action"]["args"]["fill_reading"].startswith("?v")
    assert sorted(ar["action"]["args"]["fill_readings"]) == [
        "least_frequent_color", "most_frequent_color"]
    assert ar["condition"]["type"] == "canvas_fill"


def test_unify_declines_fill_vs_unrelated():
    other = {
        "condition": {"type": "constant_output", "params": {}, "min_evidence": 2},
        "action": {"dsl": "copy_common_output", "args": {}},
        "category": "constant_output",
    }
    assert anti_unification.unify(
        [_concrete_fill_rule("most_frequent_color"), other]) is None


def test_save_consolidates_canvas_fill_family_and_is_stable(tmp_path):
    root = str(tmp_path)
    memory.save_rule_to_ltm(_concrete_fill_rule("most_frequent_color"),
                            "5582e5ca", root)
    memory.save_rule_to_ltm(_concrete_fill_rule("least_frequent_color"),
                            "madeup_fill_foreground_color", root)

    rules = memory.load_all_rules(root)
    # Exactly one rule — the abstract lift — covering both tasks (no accretion).
    assert len(rules) == 1
    abstract = rules[0]
    assert abstract["action"]["dsl"] == "fill_canvas"
    assert abstract["action"]["args"]["fill_reading"].startswith("?v")
    assert sorted(abstract["covers"]) == [
        "5582e5ca", "madeup_fill_foreground_color"]
    assert abstract["anti_unification_trace"]
    assert os.path.exists(abstract["anti_unification_trace"])

    # Re-discovering a reading already in range must merge (absorb), not re-spawn.
    memory.save_rule_to_ltm(_concrete_fill_rule("most_frequent_color"),
                            "dup_dominant", root)
    rules2 = memory.load_all_rules(root)
    assert len(rules2) == 1
    assert "dup_dominant" in rules2[0]["covers"]


def test_abstract_fill_rule_passes_validation():
    res = anti_unification.unify([
        _concrete_fill_rule("most_frequent_color"),
        _concrete_fill_rule("least_frequent_color"),
    ])
    entry = dict(res.abstract_rule)
    entry["covers"] = ["5582e5ca", "madeup_fill_foreground_color"]
    memory.validate_rule(entry)  # must not raise
