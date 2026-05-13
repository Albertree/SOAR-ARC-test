"""
tests/test_unify.py — exercise the anti-unification API added in iter 5.

Runs without pytest. Invoke directly:

    python tests/test_unify.py

Exits 0 on success, non-zero on first failed assertion. The test uses a
tmpdir for ``episodic_memory_root`` so it never pollutes the real
``episodic_memory/`` tree under the repo.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
import traceback

# Make the repo root importable when invoked as `python tests/test_unify.py`.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from program.anti_unification import (  # noqa: E402
    NoCommonSkeleton,
    UnifyResult,
    unify,
)


# ──────────────────────────────────────────────────────────────────────────
# Test fixtures.
# ──────────────────────────────────────────────────────────────────────────

def _make_rule(*,
               rule_id: int,
               source_task: str,
               cond_type: str = "grid_size_preserved",
               cond_params: dict | None = None,
               dsl: str = "coloring",
               args: dict | None = None,
               concept: str = "test_rule",
               category: str = "test") -> dict:
    return {
        "id": rule_id,
        "concept": concept,
        "category": category,
        "condition": {
            "type": cond_type,
            "params": dict(cond_params or {}),
            "min_evidence": 1,
        },
        "action": {
            "dsl": dsl,
            "args": dict(args or {}),
        },
        "covers": [source_task],
        "source_task": source_task,
        "anti_unification_trace": None,
        "created_at": "2026-05-13T19:00:00.000000",
        "times_reused": 0,
    }


# ──────────────────────────────────────────────────────────────────────────
# Tests.
# ──────────────────────────────────────────────────────────────────────────

def test_single_rule_raises(tmp_root: str) -> None:
    try:
        unify([_make_rule(rule_id=1, source_task="00576224")],
              episodic_memory_root=tmp_root)
    except NoCommonSkeleton:
        return
    raise AssertionError("expected NoCommonSkeleton for single-rule input")


def test_non_list_raises(tmp_root: str) -> None:
    try:
        unify(_make_rule(rule_id=1, source_task="00576224"),  # type: ignore[arg-type]
              episodic_memory_root=tmp_root)
    except NoCommonSkeleton:
        return
    raise AssertionError("expected NoCommonSkeleton for non-list input")


def test_skeleton_mismatch_condition_type(tmp_root: str) -> None:
    r1 = _make_rule(rule_id=1, source_task="00576224", cond_type="A")
    r2 = _make_rule(rule_id=2, source_task="007bbfb7", cond_type="B")
    try:
        unify([r1, r2], episodic_memory_root=tmp_root)
    except NoCommonSkeleton as e:
        assert "condition.type" in str(e), f"wrong msg: {e}"
        return
    raise AssertionError("expected NoCommonSkeleton on condition.type mismatch")


def test_skeleton_mismatch_action_dsl(tmp_root: str) -> None:
    r1 = _make_rule(rule_id=1, source_task="00576224", dsl="coloring")
    r2 = _make_rule(rule_id=2, source_task="007bbfb7", dsl="make_grid")
    try:
        unify([r1, r2], episodic_memory_root=tmp_root)
    except NoCommonSkeleton as e:
        assert "action.dsl" in str(e), f"wrong msg: {e}"
        return
    raise AssertionError("expected NoCommonSkeleton on action.dsl mismatch")


def test_identical_rules_no_substitution(tmp_root: str) -> None:
    """Identical inputs produce no substitutions, no trace file, but the
    abstract_rule still carries union covers."""
    r1 = _make_rule(rule_id=1, source_task="00576224",
                    args={"color": 3, "selection": [0, 0]})
    r2 = _make_rule(rule_id=2, source_task="007bbfb7",
                    args={"color": 3, "selection": [0, 0]})
    result = unify([r1, r2], episodic_memory_root=tmp_root)

    assert isinstance(result, UnifyResult)
    assert result.is_more_general() is False, (
        "identical rules should not be flagged is_more_general"
    )
    assert result.trace_path is None, (
        f"no trace expected when there are no substitutions, got {result.trace_path!r}"
    )
    assert result.substitutions == {}, (
        f"unexpected substitutions: {result.substitutions}"
    )
    # covers union, dedup, first-seen order preserved
    assert result.abstract_rule["covers"] == ["00576224", "007bbfb7"]
    # no trace file written
    trace_dir = os.path.join(tmp_root, "007bbfb7", "anti_unification")
    if os.path.isdir(trace_dir):
        assert os.listdir(trace_dir) == [], (
            f"unexpected files in {trace_dir}: {os.listdir(trace_dir)}"
        )


def test_differing_args_lifted_to_variable(tmp_root: str) -> None:
    """Two rules differing only in action.args.color lift that position to
    a fresh variable, leaving the shared field untouched."""
    r1 = _make_rule(rule_id=1, source_task="00576224",
                    args={"color": 3, "selection": [0, 0]})
    r2 = _make_rule(rule_id=2, source_task="007bbfb7",
                    args={"color": 5, "selection": [0, 0]})
    result = unify([r1, r2], episodic_memory_root=tmp_root)

    assert result.is_more_general() is True
    assert result.substitutions == {"action.args.color": "?v1"}, (
        f"unexpected substitutions: {result.substitutions}"
    )

    abstract = result.abstract_rule
    assert abstract["action"]["args"]["color"] == "?v1"
    assert abstract["action"]["args"]["selection"] == [0, 0], (
        "shared selection should pass through unchanged"
    )

    # trace file exists and has the documented shape
    assert result.trace_path is not None
    # The portion AFTER the (possibly-Windows-absolute) tmpdir root must use
    # forward slashes. Canonical-root V5-regex coverage lives in
    # ``test_trace_path_matches_v5_regex_with_default_root``.
    suffix = result.trace_path[len(tmp_root):]
    assert "\\" not in suffix, (
        f"trace_path suffix has backslashes: {suffix!r}"
    )
    # the on-disk path uses the tmpdir as root
    on_disk = os.path.join(tmp_root, "007bbfb7", "anti_unification")
    files = os.listdir(on_disk)
    assert len(files) == 1 and files[0].startswith("au_") and files[0].endswith(".json"), files
    trace = json.loads(open(os.path.join(on_disk, files[0]), encoding="utf-8").read())
    assert trace["skeleton"] == {
        "condition_type": "grid_size_preserved",
        "action_dsl": "coloring",
    }
    assert trace["substitutions"] == {"action.args.color": "?v1"}
    assert trace["var_count"] == 1
    assert trace["input_rules"] == [
        {"id": 1, "source_task": "00576224"},
        {"id": 2, "source_task": "007bbfb7"},
    ]


def test_multiple_differing_positions_get_unique_vars(tmp_root: str) -> None:
    r1 = _make_rule(rule_id=1, source_task="00576224",
                    args={"color": 3, "selection": [0, 0]})
    r2 = _make_rule(rule_id=2, source_task="007bbfb7",
                    args={"color": 5, "selection": [1, 1]})
    result = unify([r1, r2], episodic_memory_root=tmp_root)

    assert result.is_more_general() is True
    # Two distinct positions ⇒ two distinct variables.
    subs = result.substitutions
    assert set(subs.keys()) == {"action.args.color", "action.args.selection"}
    var_names = set(subs.values())
    assert var_names == {"?v1", "?v2"}, var_names


def test_three_rules_partial_agreement(tmp_root: str) -> None:
    """Three rules where two agree on color but the third doesn't, and
    selection differs across all three. Both positions lift."""
    r1 = _make_rule(rule_id=1, source_task="00576224",
                    args={"color": 3, "selection": [0, 0]})
    r2 = _make_rule(rule_id=2, source_task="007bbfb7",
                    args={"color": 3, "selection": [1, 1]})
    r3 = _make_rule(rule_id=3, source_task="009d5c81",
                    args={"color": 7, "selection": [2, 2]})
    result = unify([r1, r2, r3], episodic_memory_root=tmp_root)

    assert result.is_more_general()
    assert "action.args.color" in result.substitutions
    assert "action.args.selection" in result.substitutions
    # covers in first-seen order
    assert result.abstract_rule["covers"] == ["00576224", "007bbfb7", "009d5c81"]


def test_min_evidence_takes_strictest(tmp_root: str) -> None:
    r1 = _make_rule(rule_id=1, source_task="00576224")
    r1["condition"]["min_evidence"] = 2
    r2 = _make_rule(rule_id=2, source_task="007bbfb7")
    r2["condition"]["min_evidence"] = 5
    # Force a substitution so we get a real abstract rule back.
    r1["action"]["args"] = {"color": 3}
    r2["action"]["args"] = {"color": 9}
    result = unify([r1, r2], episodic_memory_root=tmp_root)
    assert result.abstract_rule["condition"]["min_evidence"] == 5


def test_covers_union_dedup_preserves_first_seen(tmp_root: str) -> None:
    r1 = _make_rule(rule_id=1, source_task="00576224",
                    args={"color": 3})
    r1["covers"] = ["00576224", "deadbeef"]
    r2 = _make_rule(rule_id=2, source_task="007bbfb7",
                    args={"color": 5})
    r2["covers"] = ["deadbeef", "007bbfb7"]   # overlap with r1 on deadbeef
    result = unify([r1, r2], episodic_memory_root=tmp_root)
    assert result.abstract_rule["covers"] == ["00576224", "deadbeef", "007bbfb7"]


def test_disjoint_arg_keys_get_lifted(tmp_root: str) -> None:
    """A key present in some inputs but not all is treated as disagreement."""
    r1 = _make_rule(rule_id=1, source_task="00576224",
                    args={"color": 3})
    r2 = _make_rule(rule_id=2, source_task="007bbfb7",
                    args={"color": 3, "selection": [0, 0]})
    result = unify([r1, r2], episodic_memory_root=tmp_root)
    assert result.is_more_general()
    assert "action.args.selection" in result.substitutions


def test_abstract_rule_not_aliased_with_inputs(tmp_root: str) -> None:
    """Mutating the abstract_rule's args must not mutate either input."""
    r1 = _make_rule(rule_id=1, source_task="00576224",
                    args={"color": 3, "selection": [0, 0]})
    r2 = _make_rule(rule_id=2, source_task="007bbfb7",
                    args={"color": 3, "selection": [0, 0]})
    result = unify([r1, r2], episodic_memory_root=tmp_root)
    # selection is the shared, deep-copied list — mutating it via the
    # abstract rule must not leak back to the inputs.
    sel = result.abstract_rule["action"]["args"]["selection"]
    assert sel == [0, 0]
    sel.append(99)
    assert r1["action"]["args"]["selection"] == [0, 0]
    assert r2["action"]["args"]["selection"] == [0, 0]


def test_trace_path_matches_v5_regex_with_default_root(tmp_root: str) -> None:
    """When called with the default ``episodic_memory_root="episodic_memory"``
    the trace_path must match the V5 regex from docs/RULE_FORMAT.md. We
    can't write into the real episodic_memory/ (tests should be hermetic),
    but we can run unify() with the default root inside a chdir'd tmpdir
    and verify the path shape."""
    pattern = re.compile(r"^episodic_memory/.+/anti_unification/.+\.json$")
    cwd = os.getcwd()
    sandbox = tempfile.mkdtemp(prefix="arbor_unify_v5_")
    try:
        os.chdir(sandbox)
        r1 = _make_rule(rule_id=1, source_task="aaaaaaaa", args={"color": 3})
        r2 = _make_rule(rule_id=2, source_task="bbbbbbbb", args={"color": 9})
        result = unify([r1, r2])  # default episodic_memory_root
        assert result.trace_path is not None
        assert pattern.match(result.trace_path), (
            f"trace_path {result.trace_path!r} does not match V5 regex"
        )
        # file was actually written
        assert os.path.isfile(result.trace_path), (
            f"trace file missing on disk: {result.trace_path}"
        )
    finally:
        os.chdir(cwd)
        shutil.rmtree(sandbox, ignore_errors=True)


def test_trace_id_increments_within_same_task(tmp_root: str) -> None:
    """Two consecutive unifies whose ``new_rule`` shares a source_task land
    their traces in the same directory; the sequence number monotonically
    increases."""
    r1 = _make_rule(rule_id=1, source_task="00576224", args={"color": 3})
    r2 = _make_rule(rule_id=2, source_task="007bbfb7", args={"color": 5})
    res_a = unify([r1, r2], episodic_memory_root=tmp_root)
    assert res_a.trace_path is not None and res_a.trace_path.endswith("au_001.json"), (
        f"expected au_001.json, got {res_a.trace_path}"
    )

    r3 = _make_rule(rule_id=3, source_task="009d5c81", args={"color": 4})
    r4 = _make_rule(rule_id=4, source_task="007bbfb7", args={"color": 8})
    res_b = unify([r3, r4], episodic_memory_root=tmp_root)
    assert res_b.trace_path is not None and res_b.trace_path.endswith("au_002.json"), (
        f"expected au_002.json, got {res_b.trace_path}"
    )


# ──────────────────────────────────────────────────────────────────────────
# Driver.
# ──────────────────────────────────────────────────────────────────────────

def _run_all() -> int:
    tests = [
        test_single_rule_raises,
        test_non_list_raises,
        test_skeleton_mismatch_condition_type,
        test_skeleton_mismatch_action_dsl,
        test_identical_rules_no_substitution,
        test_differing_args_lifted_to_variable,
        test_multiple_differing_positions_get_unique_vars,
        test_three_rules_partial_agreement,
        test_min_evidence_takes_strictest,
        test_covers_union_dedup_preserves_first_seen,
        test_disjoint_arg_keys_get_lifted,
        test_abstract_rule_not_aliased_with_inputs,
        test_trace_path_matches_v5_regex_with_default_root,
        test_trace_id_increments_within_same_task,
    ]
    fails = 0
    for t in tests:
        tmp_root = tempfile.mkdtemp(prefix="arbor_test_unify_")
        try:
            t(tmp_root)
            print(f"  OK   {t.__name__}")
        except AssertionError as e:
            fails += 1
            print(f"  FAIL {t.__name__}: {e}")
        except Exception:
            fails += 1
            print(f"  FAIL {t.__name__}: unexpected exception")
            traceback.print_exc()
        finally:
            shutil.rmtree(tmp_root, ignore_errors=True)
    return fails


if __name__ == "__main__":
    rc = _run_all()
    if rc == 0:
        print("\nall unify tests passed.")
    else:
        print(f"\n{rc} test(s) failed.")
    sys.exit(0 if rc == 0 else 1)
