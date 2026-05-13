"""
tests/test_load_related.py — exercise the iter-7 ``load_related`` helper.

Runs without pytest:

    python tests/test_load_related.py

``load_related(category)`` is the read step before
``save_rule(rule, related_rules=...)``. It scans ``procedural_memory/`` for
schema-compliant rule files whose ``category`` matches and skips
malformed / legacy entries silently. These tests verify:

  * the happy path (matching rule(s) returned, sorted by filename),
  * non-matching category filtering,
  * legacy / malformed shape rejection (no ``condition``/``action`` block),
  * non-JSON garbage tolerance,
  * non-rule filenames ignored,
  * empty / missing directory handled,
  * bad-category input rejected.

Dependency-free — same runner style as ``tests/test_save_rule.py``.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import traceback

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from agent.memory import load_related  # noqa: E402


# ──────────────────────────────────────────────────────────────────────────
# Fixtures.
# ──────────────────────────────────────────────────────────────────────────

def _schema_rule(rule_id: int, category: str, *,
                 dsl: str = "stub_for_test",
                 cond_type: str = "grid_size_preserved",
                 source: str = "abcdef12") -> dict:
    return {
        "id": rule_id,
        "concept": "fixture_rule",
        "category": category,
        "condition": {
            "type": cond_type,
            "params": {},
            "min_evidence": 1,
        },
        "action": {
            "dsl": dsl,
            "args": {},
        },
        "covers": [source],
        "source_task": source,
        "anti_unification_trace": None,
        "created_at": "2026-05-13T18:00:00.000000",
        "times_reused": 0,
    }


def _write_rule(root: str, rule_id: int, rule: dict) -> str:
    path = os.path.join(root, f"rule_{rule_id:03d}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(rule, fh, indent=2)
    return path


# ──────────────────────────────────────────────────────────────────────────
# Tests.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_only_matching_category(tmp_root: str) -> None:
    _write_rule(tmp_root, 1, _schema_rule(1, "color_transform"))
    _write_rule(tmp_root, 2, _schema_rule(2, "spatial_transform"))
    _write_rule(tmp_root, 3, _schema_rule(3, "color_transform",
                                          source="aabbccdd"))

    out = load_related("color_transform", procedural_memory_root=tmp_root)
    ids = sorted(r["id"] for r in out)
    assert ids == [1, 3], f"expected ids [1, 3], got {ids}"
    for r in out:
        assert r["category"] == "color_transform"


def test_skips_legacy_rules_without_condition_block(tmp_root: str) -> None:
    """Legacy rules emitted by save_rule_to_ltm have a top-level ``rule``
    key and no ``condition``/``action`` block. load_related must skip
    them so they never reach unify()."""
    legacy = {
        "id": 1,
        "concept": "legacy",
        "category": "color_transform",
        "rule": {"type": "color_mapping", "mapping": {"0": 1}},
        "covers": ["abcdef12"],
        "source_task": "abcdef12",
        "created_at": "2026-04-29T07:50:25.355401",
        "times_reused": 0,
    }
    _write_rule(tmp_root, 1, legacy)
    _write_rule(tmp_root, 2, _schema_rule(2, "color_transform",
                                          source="cafebabe"))
    out = load_related("color_transform", procedural_memory_root=tmp_root)
    ids = [r["id"] for r in out]
    assert ids == [2], (
        f"legacy rule should have been skipped; got ids {ids}"
    )


def test_skips_rule_with_non_dict_action(tmp_root: str) -> None:
    malformed = _schema_rule(1, "color_transform")
    malformed["action"] = "not-a-dict"  # type: ignore[assignment]
    _write_rule(tmp_root, 1, malformed)
    out = load_related("color_transform", procedural_memory_root=tmp_root)
    assert out == [], f"expected [], got {out}"


def test_skips_rule_with_missing_condition_type(tmp_root: str) -> None:
    malformed = _schema_rule(1, "color_transform")
    del malformed["condition"]["type"]
    _write_rule(tmp_root, 1, malformed)
    out = load_related("color_transform", procedural_memory_root=tmp_root)
    assert out == [], f"expected [], got {out}"


def test_skips_non_json_file(tmp_root: str) -> None:
    bad_path = os.path.join(tmp_root, "rule_001.json")
    with open(bad_path, "w", encoding="utf-8") as fh:
        fh.write("this is not json {{{")
    _write_rule(tmp_root, 2, _schema_rule(2, "color_transform"))
    out = load_related("color_transform", procedural_memory_root=tmp_root)
    ids = [r["id"] for r in out]
    assert ids == [2], f"non-JSON file leaked into output; ids={ids}"


def test_ignores_unrelated_filenames(tmp_root: str) -> None:
    """Files that don't match the rule_NNN.json pattern are ignored
    entirely (not read, so they cannot crash the loader)."""
    with open(os.path.join(tmp_root, "README.md"), "w", encoding="utf-8") as fh:
        fh.write("# unrelated")
    with open(os.path.join(tmp_root, "rule_001.bak"), "w", encoding="utf-8") as fh:
        fh.write("not a rule")
    _write_rule(tmp_root, 5, _schema_rule(5, "spatial_transform"))
    out = load_related("spatial_transform", procedural_memory_root=tmp_root)
    ids = [r["id"] for r in out]
    assert ids == [5], f"expected ids [5], got {ids}"


def test_empty_directory_returns_empty_list(tmp_root: str) -> None:
    assert load_related("anything",
                        procedural_memory_root=tmp_root) == []


def test_missing_directory_returns_empty_list(tmp_root: str) -> None:
    missing = os.path.join(tmp_root, "does_not_exist")
    assert load_related("anything", procedural_memory_root=missing) == []


def test_empty_or_non_string_category_returns_empty(tmp_root: str) -> None:
    _write_rule(tmp_root, 1, _schema_rule(1, "color_transform"))
    assert load_related("", procedural_memory_root=tmp_root) == []
    assert load_related(None, procedural_memory_root=tmp_root) == []  # type: ignore[arg-type]
    assert load_related(42, procedural_memory_root=tmp_root) == []  # type: ignore[arg-type]


def test_load_related_does_not_mutate_disk(tmp_root: str) -> None:
    _write_rule(tmp_root, 1, _schema_rule(1, "color_transform"))
    before = sorted(os.listdir(tmp_root))
    load_related("color_transform", procedural_memory_root=tmp_root)
    after = sorted(os.listdir(tmp_root))
    assert before == after, (
        f"load_related mutated procedural_memory: {before} -> {after}"
    )


def test_returned_rules_are_usable_by_unify(tmp_root: str) -> None:
    """Smoke check: the rules returned by load_related must be acceptable
    as input to program.anti_unification.unify (i.e. have the keys
    unify reads). Two same-category rules with identical skeleton
    should produce a UnifyResult, not a NoCommonSkeleton."""
    from program.anti_unification import NoCommonSkeleton, unify

    r1 = _schema_rule(1, "color_transform", source="00000001")
    r1["action"]["args"] = {"color": 3}
    r2 = _schema_rule(2, "color_transform", source="00000002")
    r2["action"]["args"] = {"color": 5}
    _write_rule(tmp_root, 1, r1)
    _write_rule(tmp_root, 2, r2)

    related = load_related("color_transform",
                           procedural_memory_root=tmp_root)
    assert len(related) == 2
    cwd = os.getcwd()
    sandbox = tempfile.mkdtemp(prefix="arbor_load_related_au_")
    try:
        os.chdir(sandbox)
        result = unify(related)
        assert result.is_more_general(), (
            "two same-skeleton rules from load_related did not unify"
        )
    except NoCommonSkeleton as exc:  # pragma: no cover - failure mode
        raise AssertionError(
            f"unify raised NoCommonSkeleton on load_related output: {exc}"
        )
    finally:
        os.chdir(cwd)
        shutil.rmtree(sandbox, ignore_errors=True)


# ──────────────────────────────────────────────────────────────────────────
# Driver.
# ──────────────────────────────────────────────────────────────────────────

def _run_all() -> int:
    tests = [
        test_returns_only_matching_category,
        test_skips_legacy_rules_without_condition_block,
        test_skips_rule_with_non_dict_action,
        test_skips_rule_with_missing_condition_type,
        test_skips_non_json_file,
        test_ignores_unrelated_filenames,
        test_empty_directory_returns_empty_list,
        test_missing_directory_returns_empty_list,
        test_empty_or_non_string_category_returns_empty,
        test_load_related_does_not_mutate_disk,
        test_returned_rules_are_usable_by_unify,
    ]
    fails = 0
    for t in tests:
        tmp_root = tempfile.mkdtemp(prefix="arbor_load_related_")
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
        print("\nall load_related tests passed.")
    else:
        print(f"\n{rc} test(s) failed.")
    sys.exit(0 if rc == 0 else 1)
