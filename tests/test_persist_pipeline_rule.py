"""
tests/test_persist_pipeline_rule.py — exercise the iter-15 save dispatch
``ActiveSoarAgent._persist_pipeline_rule``.

The dispatch is the post-pipeline routing: schema-aware ``save_rule``
when ``translate_to_schema`` returns a §1-shaped rule, legacy
``save_rule_to_ltm`` for non-identity slow-path shapes that still need
an anti-unification-discovered abstraction, and a no-op for the identity
fallback when the matcher does not fire (the previous
``rule_type != "identity"`` guard's replacement).

Runs without pytest:

    python tests/test_persist_pipeline_rule.py

Dependency-free, same runner style as the other tests under ``tests/``.
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

from agent.active_agent import ActiveSoarAgent  # noqa: E402
from agent.memory import validate_rule  # noqa: E402


HEX = "00576224"


def _tmp() -> str:
    return tempfile.mkdtemp(prefix="persist_pipeline_test_")


def _agent(root: str) -> ActiveSoarAgent:
    """Construct an agent whose procedural_memory_root is the test tmpdir.

    No solve() is called — only the helper under test. ``episodic_memory_root``
    is left at the default; the helper does not write episodic data.
    """
    return ActiveSoarAgent(procedural_memory_root=root)


def _identity_patterns(num_pairs: int = 2) -> dict:
    """Patterns shape that ``identity_transformation`` accepts:
    every pair has size_match=True and zero change groups."""
    return {
        "pair_analyses": [
            {"size_match": True, "groups": []} for _ in range(num_pairs)
        ],
        "grid_size_preserved": True,
    }


def _non_identity_patterns() -> dict:
    """Patterns shape that ``identity_transformation`` rejects:
    a pair with at least one change group."""
    return {
        "pair_analyses": [
            {
                "size_match": True,
                "groups": [[{"row": 0, "col": 0,
                             "input_color": 0, "output_color": 1}]],
            },
        ],
        "grid_size_preserved": True,
    }


def _list_rule_files(root: str) -> list[str]:
    if not os.path.isdir(root):
        return []
    return sorted(
        f for f in os.listdir(root)
        if f.startswith("rule_") and f.endswith(".json")
    )


# ──────────────────────────────────────────────────────────────────────────
# Tests.
# ──────────────────────────────────────────────────────────────────────────

def test_helper_exists_on_active_soar_agent() -> None:
    # Sanity: the iter-15 migration extracted the dispatch onto the class.
    assert hasattr(ActiveSoarAgent, "_persist_pipeline_rule")
    assert callable(ActiveSoarAgent._persist_pipeline_rule)


def test_identity_rule_matcher_fires_writes_schema_rule() -> None:
    # The headline migration outcome: identity + matcher firing now lands
    # a §1-compliant rule on disk via save_rule (was silently dropped).
    root = _tmp()
    try:
        agent = _agent(root)
        legacy = {"type": "identity", "confidence": 0.0}
        path = agent._persist_pipeline_rule(legacy, HEX, _identity_patterns())
        assert path is not None
        assert os.path.isfile(path)
        with open(path, encoding="utf-8") as fh:
            saved = json.load(fh)
        # Schema shape, not legacy shape: no top-level `rule` key, condition
        # and action present.
        assert "condition" in saved and "action" in saved
        assert "rule" not in saved
        assert saved["condition"]["type"] == "identity_transformation"
        assert saved["action"]["dsl"] == "coloring"
        assert saved["action"]["args"] == {"selection": [], "color": 0}
        assert saved["covers"] == [HEX]
        assert saved["source_task"] == HEX
        # The just-written rule already lives under root, so the V6
        # collision check would now reject re-saving the same id. Validate
        # against a sibling tmpdir instead — V1–V5/V7 must hold on disk.
        sibling = _tmp()
        try:
            validate_rule(saved, procedural_memory_root=sibling)
        finally:
            shutil.rmtree(sibling, ignore_errors=True)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_identity_rule_matcher_rejects_writes_nothing() -> None:
    # The iter-15 fallback contract for the seed=42 probe set: every probe
    # task today produces an identity legacy rule but its patterns dict
    # has non-zero change groups, so the matcher rejects and nothing
    # lands on disk. F4 stays inert despite the identity guard being gone.
    root = _tmp()
    try:
        agent = _agent(root)
        legacy = {"type": "identity", "confidence": 0.0}
        path = agent._persist_pipeline_rule(legacy, HEX, _non_identity_patterns())
        assert path is None
        assert _list_rule_files(root) == []
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_identity_rule_with_empty_patterns_writes_nothing() -> None:
    # Defensive: empty patterns => matcher rejects (pair_analyses empty)
    # => no rule, no fallback (rule_type == "identity").
    root = _tmp()
    try:
        agent = _agent(root)
        legacy = {"type": "identity", "confidence": 0.0}
        path = agent._persist_pipeline_rule(legacy, HEX, {})
        assert path is None
        assert _list_rule_files(root) == []
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_color_mapping_legacy_shape_is_dropped_until_au_abstraction() -> None:
    # color_mapping shape has no translator yet. The migration drops
    # rather than calls the legacy writer, because the legacy writer's
    # output shape would trip F4 (no `condition` key). The cost is the
    # rule does not persist — the gain is the slow path no longer
    # produces F4-violating files. Anti-unification discovering an
    # abstraction for this shape is the path forward (next iter's work).
    root = _tmp()
    try:
        agent = _agent(root)
        legacy = {
            "type": "color_mapping",
            "mapping": {0: 1, 1: 0},
            "confidence": 1.0,
        }
        path = agent._persist_pipeline_rule(legacy, HEX, _non_identity_patterns())
        assert path is None
        assert _list_rule_files(root) == []
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_recolor_sequential_legacy_shape_is_dropped_until_au_abstraction() -> None:
    # Same contract as above for the second non-identity legacy shape.
    # Crucial property: with `--shuffle`, the seed=42 probe surfaces
    # task `e5790162` which produces a recolor_sequential rule. The
    # pre-iter-15 dispatch would have routed it through save_rule_to_ltm
    # → legacy-shape file → F4 violation → auto-revert. The iter-15
    # dispatch drops it instead, keeping F4 inert.
    root = _tmp()
    try:
        agent = _agent(root)
        legacy = {
            "type": "recolor_sequential",
            "sort_key": "top_row",
            "start_color": 3,
            "source_colors": [0],
            "confidence": 1.0,
        }
        path = agent._persist_pipeline_rule(legacy, HEX, _non_identity_patterns())
        assert path is None
        assert _list_rule_files(root) == []
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_dispatch_assigns_monotonic_ids() -> None:
    # Two successful saves into the same root must get id=1 then id=2 —
    # next_rule_id reads from disk between calls, so the helper must
    # NOT cache.
    root = _tmp()
    try:
        agent = _agent(root)
        legacy = {"type": "identity", "confidence": 0.0}
        p1 = agent._persist_pipeline_rule(legacy, "00000001", _identity_patterns())
        p2 = agent._persist_pipeline_rule(legacy, "00000002", _identity_patterns())
        assert p1 is not None and p2 is not None
        assert os.path.basename(p1) == "rule_001.json"
        assert os.path.basename(p2) == "rule_002.json"
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_non_dict_legacy_rule_is_no_op() -> None:
    # Defensive: solve()'s slow path could in principle leak a non-dict
    # entry into active-rules; the helper must not crash and must not write.
    root = _tmp()
    try:
        agent = _agent(root)
        for bad in (None, "identity", 42, ["identity"]):
            assert agent._persist_pipeline_rule(bad, HEX, _identity_patterns()) is None
        assert _list_rule_files(root) == []
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_legacy_rule_without_type_field_is_dropped() -> None:
    # rule_type defaults to "none" for a dict missing "type". Translator
    # rejects (legacy_type not a string in its allow-list). The dispatch
    # drops the rule rather than invoking the legacy writer (which would
    # write an F4-violating file).
    root = _tmp()
    try:
        agent = _agent(root)
        legacy = {"confidence": 0.5}  # no "type" key
        path = agent._persist_pipeline_rule(legacy, HEX, _identity_patterns())
        assert path is None
        assert _list_rule_files(root) == []
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_dispatch_does_not_swallow_rule_schema_error() -> None:
    # F7 spirit: if save_rule were to raise RuleSchemaError, it must
    # propagate. We cannot easily make translate_to_schema's output fail
    # validation (it is constructed against the live registries), so this
    # test exercises the closely-related contract: the helper does not
    # wrap save_rule in try/except. If save_rule succeeds the helper
    # returns the path; if it raises, the exception escapes.
    import inspect
    from agent.active_agent import ActiveSoarAgent as _AGT
    src = inspect.getsource(_AGT._persist_pipeline_rule)
    # No bare `except` and no `except RuleSchemaError` handler in the
    # dispatch body — F7's pattern grep would find none anyway.
    assert "except" not in src, \
        "dispatch must not wrap save_rule in try/except (F7 spirit)"


def test_invalid_task_hex_short_circuits_to_no_save() -> None:
    # translate_to_schema rejects non-8-hex task_hex. For an identity
    # legacy rule with a bad hex the dispatch must skip the schema
    # writer (translator returned None) AND the legacy fallback
    # (rule_type == "identity").
    root = _tmp()
    try:
        agent = _agent(root)
        legacy = {"type": "identity", "confidence": 0.0}
        path = agent._persist_pipeline_rule(legacy, "BADHEX", _identity_patterns())
        assert path is None
        assert _list_rule_files(root) == []
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_dispatch_does_not_mutate_caller_inputs() -> None:
    # Pure dispatch: the legacy_rule and patterns dicts handed in by
    # solve() must not be mutated (other code in the same solve() call
    # keeps reading them, e.g. last_solve_info).
    root = _tmp()
    try:
        agent = _agent(root)
        legacy = {"type": "identity", "confidence": 0.0}
        legacy_copy = json.loads(json.dumps(legacy))
        patterns = _identity_patterns()
        patterns_copy = json.loads(json.dumps(patterns))
        agent._persist_pipeline_rule(legacy, HEX, patterns)
        assert legacy == legacy_copy
        assert patterns == patterns_copy
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_helper_uses_self_procedural_memory_root() -> None:
    # If the dispatch hard-coded PROCEDURAL_MEMORY_ROOT instead of
    # threading self.procedural_memory_root, multi-agent tests would
    # collide. Use two roots and verify each gets its own file.
    a_root = _tmp()
    b_root = _tmp()
    try:
        a = _agent(a_root)
        b = _agent(b_root)
        legacy = {"type": "identity", "confidence": 0.0}
        a._persist_pipeline_rule(legacy, HEX, _identity_patterns())
        b._persist_pipeline_rule(legacy, HEX, _identity_patterns())
        assert _list_rule_files(a_root) == ["rule_001.json"]
        assert _list_rule_files(b_root) == ["rule_001.json"]
    finally:
        shutil.rmtree(a_root, ignore_errors=True)
        shutil.rmtree(b_root, ignore_errors=True)


# ──────────────────────────────────────────────────────────────────────────
# Driver.
# ──────────────────────────────────────────────────────────────────────────

def _run_all() -> int:
    tests = [
        test_helper_exists_on_active_soar_agent,
        test_identity_rule_matcher_fires_writes_schema_rule,
        test_identity_rule_matcher_rejects_writes_nothing,
        test_identity_rule_with_empty_patterns_writes_nothing,
        test_color_mapping_legacy_shape_is_dropped_until_au_abstraction,
        test_recolor_sequential_legacy_shape_is_dropped_until_au_abstraction,
        test_dispatch_assigns_monotonic_ids,
        test_non_dict_legacy_rule_is_no_op,
        test_legacy_rule_without_type_field_is_dropped,
        test_dispatch_does_not_swallow_rule_schema_error,
        test_invalid_task_hex_short_circuits_to_no_save,
        test_dispatch_does_not_mutate_caller_inputs,
        test_helper_uses_self_procedural_memory_root,
    ]
    fails = 0
    for t in tests:
        try:
            t()
            print(f"  OK   {t.__name__}")
        except AssertionError as e:
            fails += 1
            print(f"  FAIL {t.__name__}: {e}")
        except Exception:
            fails += 1
            print(f"  FAIL {t.__name__}: unexpected exception")
            traceback.print_exc()
    return fails


if __name__ == "__main__":
    rc = _run_all()
    if rc == 0:
        print("\nall persist-pipeline-rule tests passed.")
    else:
        print(f"\n{rc} test(s) failed.")
    sys.exit(0 if rc == 0 else 1)
