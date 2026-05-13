"""
tests/test_save_rule.py — exercise the schema-aware writer added in iter 2.

Runs without pytest. Invoke directly:

    python tests/test_save_rule.py

Exits 0 on success, non-zero on first failed assertion (with traceback).

The DSL primitive registry does not yet exist on this branch, so V3 ("unknown
action.dsl") will reject any rule whose action.dsl is not bootstrapped. The
happy-path test installs a stub DSL_REGISTRY at runtime to verify the writer
itself; this stub disappears when the test process exits and does NOT create
a hand-coded DSL primitive on disk (no F3 invariant trip).
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import traceback

# Make the repo root importable when invoked as `python tests/test_save_rule.py`.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from agent import memory  # noqa: E402
from agent.memory import RuleSchemaError, save_rule, validate_rule  # noqa: E402


# ──────────────────────────────────────────────────────────────────────────
# Test-only DSL registry stub. We monkeypatch memory._dsl_registry rather
# than create a real procedural_memory/DSL/ module so V3 has a primitive
# to recognise during the happy path without writing any DSL Python file.
# ──────────────────────────────────────────────────────────────────────────

_TEST_DSL_REGISTRY = {"stub_for_test": object()}


def _install_dsl_stub() -> None:
    memory._dsl_registry = lambda: dict(_TEST_DSL_REGISTRY)


def _restore_dsl_stub() -> None:
    # Reload of original lazy importer.
    from agent import memory as _mem

    def _real():
        try:
            from procedural_memory.DSL.apply import DSL_REGISTRY  # type: ignore
        except Exception:
            return {}
        return DSL_REGISTRY
    _mem._dsl_registry = _real


def _valid_rule(rule_id: int = 1) -> dict:
    """Return a freshly-constructed rule that passes V1–V7 with the stub
    registries in place."""
    return {
        "id": rule_id,
        "concept": "test_rule",
        "category": "test",
        "condition": {
            "type": "grid_size_preserved",
            "params": {},
            "min_evidence": 1,
        },
        "action": {
            "dsl": "stub_for_test",
            "args": {},
        },
        "covers": ["abcdef12"],
        "source_task": "abcdef12",
        "anti_unification_trace": None,
        "created_at": "2026-05-13T17:40:00.000000",
        "times_reused": 0,
    }


# ──────────────────────────────────────────────────────────────────────────
# Individual checks.
# ──────────────────────────────────────────────────────────────────────────

def _expect_raises(label: str, fn, *, match: str | None = None):
    try:
        fn()
    except RuleSchemaError as exc:
        if match is not None and match not in str(exc):
            raise AssertionError(
                f"{label}: expected RuleSchemaError matching {match!r}, got {exc!s}"
            )
        return
    raise AssertionError(f"{label}: expected RuleSchemaError, none raised")


def test_v1_missing_required_key(tmp_root: str) -> None:
    rule = _valid_rule()
    del rule["id"]
    _expect_raises("V1", lambda: validate_rule(rule, procedural_memory_root=tmp_root),
                   match="missing required key")


def test_v2_unknown_condition_type(tmp_root: str) -> None:
    rule = _valid_rule()
    rule["condition"]["type"] = "no_such_matcher_definitely"
    _expect_raises("V2", lambda: validate_rule(rule, procedural_memory_root=tmp_root),
                   match="unknown condition.type")


def test_v3_unknown_action_dsl(tmp_root: str) -> None:
    rule = _valid_rule()
    rule["action"]["dsl"] = "no_such_primitive"
    _expect_raises("V3", lambda: validate_rule(rule, procedural_memory_root=tmp_root),
                   match="unknown action.dsl")


def test_v4_source_task_not_in_covers(tmp_root: str) -> None:
    rule = _valid_rule()
    rule["source_task"] = "deadbeef"
    _expect_raises("V4", lambda: validate_rule(rule, procedural_memory_root=tmp_root),
                   match="source_task must appear in covers")


def test_v5_au_trace_path_must_exist(tmp_root: str) -> None:
    rule = _valid_rule()
    rule["anti_unification_trace"] = (
        "episodic_memory/abcdef12/anti_unification/au_999.json"
    )
    _expect_raises("V5", lambda: validate_rule(rule, procedural_memory_root=tmp_root),
                   match="trace file not found")


def test_v6_id_collision(tmp_root: str) -> None:
    rule = _valid_rule(rule_id=1)
    path = save_rule(rule, procedural_memory_root=tmp_root)
    assert os.path.isfile(path), "first save did not produce file"
    rule2 = _valid_rule(rule_id=1)
    _expect_raises("V6", lambda: save_rule(rule2, procedural_memory_root=tmp_root),
                   match="id collision")


def test_v7_unexpected_key(tmp_root: str) -> None:
    rule = _valid_rule()
    rule["surprise"] = "hello"
    _expect_raises("V7", lambda: validate_rule(rule, procedural_memory_root=tmp_root),
                   match="unexpected key")


def test_happy_path_writes_schema_compliant_file(tmp_root: str) -> None:
    rule = _valid_rule(rule_id=42)
    path = save_rule(rule, procedural_memory_root=tmp_root)
    assert os.path.basename(path) == "rule_042.json"
    with open(path, encoding="utf-8") as fh:
        on_disk = json.load(fh)
    assert "condition" in on_disk and "action" in on_disk, (
        "saved rule is missing condition/action — would trip F4"
    )
    assert "rule" not in on_disk, "legacy 'rule' key leaked into schema-aware path"
    for k in (
        "id", "concept", "category", "condition", "action",
        "covers", "source_task", "anti_unification_trace",
        "created_at", "times_reused",
    ):
        assert k in on_disk, f"missing required key on disk: {k}"


def test_validate_rule_does_not_write(tmp_root: str) -> None:
    # validate_rule should be side-effect-free.
    before = set(os.listdir(tmp_root))
    rule = _valid_rule(rule_id=7)
    validate_rule(rule, procedural_memory_root=tmp_root)
    after = set(os.listdir(tmp_root))
    assert before == after, "validate_rule leaked a write to disk"


def test_v3_when_dsl_registry_empty(tmp_root: str) -> None:
    """With no DSL primitives installed, every rule fails V3 — correct-by-
    construction until coloring/make_grid land."""
    _restore_dsl_stub()
    try:
        rule = _valid_rule()
        _expect_raises("V3-empty",
                       lambda: validate_rule(rule, procedural_memory_root=tmp_root),
                       match="unknown action.dsl")
    finally:
        _install_dsl_stub()


# ──────────────────────────────────────────────────────────────────────────
# Iter 6 — anti-unification wiring through save_rule().
# These tests exercise the CLAUDE.md §8 contract: save_rule is the sole
# permitted caller of program.anti_unification.unify. The trace_path
# produced by unify must satisfy V5, so the tests chdir into a sandbox so
# the default ``episodic_memory_root="episodic_memory"`` resolves cleanly.
# ──────────────────────────────────────────────────────────────────────────

def test_au_wiring_no_related_rules_behaves_like_iter5(tmp_root: str) -> None:
    """A call without related_rules must not import or invoke unify().
    Verified by overriding the unify symbol to raise — if save_rule
    touched it, the test would fail loudly."""
    import program.anti_unification as au
    sentinel = []

    def _trip(*a, **kw):
        sentinel.append(True)
        raise RuntimeError("unify was called when it should not have been")
    real_unify = au.unify
    au.unify = _trip
    try:
        path = save_rule(_valid_rule(rule_id=11), procedural_memory_root=tmp_root)
    finally:
        au.unify = real_unify
    assert os.path.isfile(path)
    assert sentinel == [], "save_rule called unify with no related_rules"


def test_au_wiring_replaces_with_abstract_rule_when_more_general(
        tmp_root: str) -> None:
    """Two rules differing on action.args.color produce a non-null
    abstract rule whose anti_unification_trace points to a real file
    (so V5 passes) and whose covers is the union of inputs."""
    cwd = os.getcwd()
    sandbox = tempfile.mkdtemp(prefix="arbor_au_save_")
    try:
        os.chdir(sandbox)
        pm_root = os.path.join(sandbox, "procedural_memory")
        os.makedirs(pm_root, exist_ok=True)

        existing = _valid_rule(rule_id=1)
        existing["source_task"] = "00576224"
        existing["covers"] = ["00576224"]
        existing["action"]["args"] = {"color": 3}

        new = _valid_rule(rule_id=2)
        new["source_task"] = "007bbfb7"
        new["covers"] = ["007bbfb7"]
        new["action"]["args"] = {"color": 5}

        path = save_rule(new,
                         related_rules=[existing],
                         procedural_memory_root=pm_root)
        assert os.path.basename(path) == "rule_002.json"

        with open(path, encoding="utf-8") as fh:
            on_disk = json.load(fh)

        # Abstract rule replaced new — selection/color lifted to a variable.
        assert on_disk["action"]["args"]["color"].startswith("?v"), (
            f"action.args.color was not lifted: {on_disk['action']['args']}"
        )
        # covers union, first-seen order.
        assert on_disk["covers"] == ["00576224", "007bbfb7"]
        # anti_unification_trace is set and points to a real on-disk file.
        trace = on_disk["anti_unification_trace"]
        assert trace is not None
        assert trace.startswith("episodic_memory/"), trace
        assert "/anti_unification/" in trace, trace
        assert os.path.isfile(trace), f"trace file missing: {trace}"
    finally:
        os.chdir(cwd)
        shutil.rmtree(sandbox, ignore_errors=True)


def test_au_wiring_keeps_rule_unchanged_on_no_common_skeleton(
        tmp_root: str) -> None:
    """When the related rule disagrees on action.dsl, NoCommonSkeleton
    fires inside unify and save_rule must persist the new rule
    unchanged (no abstract_rule, no trace)."""
    # Install a second DSL primitive so the second rule's dsl="make_grid_stub"
    # also passes V3 — without this, save_rule would reject the new rule on V3
    # before AU is even reached.
    _TEST_DSL_REGISTRY["make_grid_stub"] = object()
    try:
        existing = _valid_rule(rule_id=1)
        existing["source_task"] = "00576224"
        existing["covers"] = ["00576224"]
        existing["action"]["dsl"] = "stub_for_test"

        new = _valid_rule(rule_id=2)
        new["source_task"] = "007bbfb7"
        new["covers"] = ["007bbfb7"]
        new["action"]["dsl"] = "make_grid_stub"

        path = save_rule(new,
                         related_rules=[existing],
                         procedural_memory_root=tmp_root)
        with open(path, encoding="utf-8") as fh:
            on_disk = json.load(fh)
        # Rule persisted untouched — dsl unchanged, no trace.
        assert on_disk["action"]["dsl"] == "make_grid_stub"
        assert on_disk["anti_unification_trace"] is None
        assert on_disk["covers"] == ["007bbfb7"]
    finally:
        _TEST_DSL_REGISTRY.pop("make_grid_stub", None)


def test_au_wiring_identical_inputs_no_trace(tmp_root: str) -> None:
    """When the related rule and the new rule are structurally identical
    (no substitutions), unify still merges covers but does NOT write a
    trace. save_rule persists the abstract rule with trace=None — which
    means save_rule must NOT swap to the abstract rule (otherwise V5
    passes vacuously but we lose the new rule's source-only identity).
    The contract per docs/ANTI_UNIFICATION.md §1.1 says is_more_general()
    is False here, so save_rule does NOT swap. The new rule is persisted
    as-is."""
    existing = _valid_rule(rule_id=1)
    existing["source_task"] = "00576224"
    existing["covers"] = ["00576224"]
    existing["action"]["args"] = {"color": 3}

    new = _valid_rule(rule_id=2)
    new["source_task"] = "007bbfb7"
    new["covers"] = ["007bbfb7"]
    new["action"]["args"] = {"color": 3}   # identical to existing

    path = save_rule(new,
                     related_rules=[existing],
                     procedural_memory_root=tmp_root)
    with open(path, encoding="utf-8") as fh:
        on_disk = json.load(fh)
    # new rule unchanged: still source_task=007bbfb7, covers=[007bbfb7],
    # trace=None — the merge happens at no-op-substitution time, but the
    # caller (this test) hasn't asked save_rule to update existing's covers.
    assert on_disk["source_task"] == "007bbfb7"
    assert on_disk["covers"] == ["007bbfb7"]
    assert on_disk["anti_unification_trace"] is None


# ──────────────────────────────────────────────────────────────────────────
# Driver.
# ──────────────────────────────────────────────────────────────────────────

def _run_all() -> int:
    tests = [
        test_v1_missing_required_key,
        test_v2_unknown_condition_type,
        test_v3_unknown_action_dsl,
        test_v4_source_task_not_in_covers,
        test_v5_au_trace_path_must_exist,
        test_v6_id_collision,
        test_v7_unexpected_key,
        test_happy_path_writes_schema_compliant_file,
        test_validate_rule_does_not_write,
        test_v3_when_dsl_registry_empty,
        test_au_wiring_no_related_rules_behaves_like_iter5,
        test_au_wiring_replaces_with_abstract_rule_when_more_general,
        test_au_wiring_keeps_rule_unchanged_on_no_common_skeleton,
        test_au_wiring_identical_inputs_no_trace,
    ]
    fails = 0
    _install_dsl_stub()
    try:
        for t in tests:
            tmp_root = tempfile.mkdtemp(prefix="arbor_test_pm_")
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
    finally:
        _restore_dsl_stub()
    return fails


if __name__ == "__main__":
    rc = _run_all()
    if rc == 0:
        print("\nall save_rule tests passed.")
    else:
        print(f"\n{rc} test(s) failed.")
    sys.exit(0 if rc == 0 else 1)
