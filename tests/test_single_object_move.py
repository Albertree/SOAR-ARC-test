"""
Tests for R1's recognition substrate: the seed object-expression vocabulary
(`agent.dsl_expr`) and the `single_object_move` matcher (BACKLOG_LOOP.md R1).

Three layers:
  * vocabulary  — `objects_of`/`unique`/`color_of`/`size_of`/`position_of` on a
                  raw grid select and read the single foreground object.
  * unit        — the matcher's logic on synthetic `object_transition` dicts.
  * integration — the matcher fed by the REAL `object_transition` signal that
                  ExtractPatternOperator surfaces for the actual easy000c–i
                  move family, proving matcher and pipeline agree on schema, and
                  a negative on a constant-output task whose outputs do not move
                  a single object.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.conditions import CONDITION_REGISTRY, get_matcher, match  # noqa: E402
from agent.dsl_expr import (  # noqa: E402
    objects_of, unique, color_of, size_of, position_of,
)


# ── seed vocabulary ───────────────────────────────────────────────────
def test_objects_of_selects_single_foreground_object():
    grid = [
        [0, 0, 0],
        [0, 2, 0],
        [0, 0, 0],
    ]
    objs = objects_of(grid)
    assert len(objs) == 1
    obj = unique(objs)
    assert obj is not None
    assert color_of(obj) == 2
    assert size_of(obj) == 1
    assert position_of(obj) == (1, 1)


def test_unique_is_none_when_not_exactly_one():
    assert unique([]) is None
    assert unique([{"a": 1}, {"b": 2}]) is None
    two_objs = objects_of([[2, 0, 3]])
    assert len(two_objs) == 2
    assert unique(two_objs) is None


# ── registry ──────────────────────────────────────────────────────────
def test_matcher_is_registered():
    assert "single_object_move" in CONDITION_REGISTRY
    assert get_matcher("single_object_move") is not None


# ── unit: matcher logic on synthetic patterns ─────────────────────────
def _transition(**kw):
    base = {
        "all_single": True, "color_preserved": True,
        "shape_preserved": True, "moved": True, "evidence_count": 2,
    }
    base.update(kw)
    return {"object_transition": base}


def test_fires_on_color_shape_preserving_move():
    assert match("single_object_move", _transition()) is True


def test_rejects_when_color_changes():
    assert match("single_object_move", _transition(color_preserved=False)) is False


def test_rejects_when_not_single_object():
    assert match("single_object_move", _transition(all_single=False)) is False


def test_rejects_when_object_did_not_move():
    assert match("single_object_move", _transition(moved=False)) is False


def test_rejects_insufficient_evidence():
    assert match("single_object_move",
                 _transition(evidence_count=1), {"min_evidence": 2}) is False


def test_rejects_missing_signal():
    assert match("single_object_move", {"grid_size_preserved": True}) is False
    assert match("single_object_move", None) is False


# ── integration: real ExtractPatternOperator output ───────────────────
def _extract_patterns(task_path, data_root="data"):
    from managers.arc_manager import ARCManager
    from agent.wm import WorkingMemory
    from agent.active_operators import ExtractPatternOperator

    with tempfile.TemporaryDirectory() as tmp:
        task = ARCManager(data_root=data_root,
                          semantic_memory_root=tmp).load_task(task_path)
    wm = WorkingMemory()
    wm.task = task
    ExtractPatternOperator().effect(wm)
    return wm.s1["patterns"]


def test_extract_pattern_surfaces_move_on_easy_a_family():
    # Every easy000c–i task is a single foreground object moved with its color
    # and shape preserved — the matcher must recognize the whole family from the
    # real signal, value-agnostically (different colors, targets, grid sizes).
    for name in ["c", "d", "e", "f", "g", "h", "i"]:
        patterns = _extract_patterns(f"ARC_easy_a/easy000{name}")
        trans = patterns["object_transition"]
        assert trans["all_single"] is True, name
        assert trans["color_preserved"] is True, name
        assert trans["shape_preserved"] is True, name
        assert trans["moved"] is True, name
        assert match("single_object_move", patterns) is True, name


def test_does_not_fire_on_recolor_in_place():
    # A single object that is *recolored in place* (color changes, position does
    # not) is not a move — the matcher must reject it through the real pipeline,
    # proving it discriminates on the COMM/DIFF (color preserved + moved), not
    # merely on "there is one object." Built on disk so it flows through the
    # actual ExtractPattern → object_transition path.
    import json

    recolor = {
        "train": [
            {"input": [[0, 0, 0], [0, 2, 0], [0, 0, 0]],
             "output": [[0, 0, 0], [0, 3, 0], [0, 0, 0]]},
            {"input": [[0, 0, 0], [0, 2, 0], [0, 0, 0]],
             "output": [[0, 0, 0], [0, 3, 0], [0, 0, 0]]},
        ],
        "test": [
            {"input": [[0, 0, 0], [0, 2, 0], [0, 0, 0]],
             "output": [[0, 0, 0], [0, 3, 0], [0, 0, 0]]},
        ],
    }
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "recolor.json"), "w") as fh:
            json.dump(recolor, fh)
        patterns = _extract_patterns("recolor", data_root=d)

    trans = patterns["object_transition"]
    assert trans["all_single"] is True          # one object — but...
    assert trans["color_preserved"] is False    # ...recolored...
    assert trans["moved"] is False              # ...and did not move.
    assert match("single_object_move", patterns) is False
