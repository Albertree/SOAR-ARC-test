"""
tests/test_fast_path_schema_rule.py — exercise iter-16's schema-aware
fast-path dispatch in ``agent/active_agent.py``.

Background
----------
Iter 14 added ``translate_to_schema``; iter 15 wired the post-pipeline
save path through ``save_rule`` so a successful solve can land a
§1-compliant ``rule_NNN.json`` on disk. The pre-iter-16 fast-path loop
in ``ActiveSoarAgent.solve()`` did ``entry.get("rule", {})`` and
dispatched the inner legacy dict through
``PredictOperator._apply_rule`` — schema entries have NO top-level
``rule`` key, so their action was silently dropped. That wasted every
iter-14/iter-15 save the moment one landed.

Iter 16 adds ``_predict_with_entry`` (and friends) which recognise the
``{condition, action, ...}`` shape and route the rule through
``apply_DSL`` instead. This test exercises the dispatch helpers in
isolation plus an end-to-end smoke that an on-disk schema rule is
actually consumed by ``solve()``.

Runs without pytest:

    python tests/test_fast_path_schema_rule.py

Dependency-free, same runner style as the other tests under ``tests/``.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import traceback
import types

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from agent.active_agent import ActiveSoarAgent  # noqa: E402
from agent.memory import save_rule  # noqa: E402


HEX = "00576224"


# ──────────────────────────────────────────────────────────────────────────
# Builders.
# ──────────────────────────────────────────────────────────────────────────

def _tmp() -> str:
    return tempfile.mkdtemp(prefix="fast_path_schema_test_")


def _agent(proc_root: str, epi_root: str | None = None) -> ActiveSoarAgent:
    """ActiveSoarAgent with both ``procedural_memory_root`` and
    ``episodic_memory_root`` redirected to tmp paths, so ``solve``'s
    episodic write does not pollute the repo."""
    if epi_root is None:
        epi_root = _tmp()
    return ActiveSoarAgent(
        procedural_memory_root=proc_root,
        episodic_memory_root=epi_root,
    )


def _grid(raw: list) -> types.SimpleNamespace:
    """Lightweight stand-in for ``ARCKG.grid.Grid`` — exposes ``.raw``,
    which is all the fast-path code reads."""
    return types.SimpleNamespace(raw=raw)


def _pair(input_raw: list | None, output_raw: list | None) -> types.SimpleNamespace:
    return types.SimpleNamespace(
        input_grid=_grid(input_raw) if input_raw is not None else None,
        output_grid=_grid(output_raw) if output_raw is not None else None,
    )


def _task(task_hex: str, example_pairs: list, test_pairs: list) -> types.SimpleNamespace:
    return types.SimpleNamespace(
        task_hex=task_hex,
        example_pairs=example_pairs,
        test_pairs=test_pairs,
    )


def _schema_rule_paint_origin(rule_id: int = 1, hex_: str = HEX) -> dict:
    """A §1-compliant non-identity ``coloring`` rule: paint cell (0,0)
    with color 5. Uses ``grid_size_preserved`` as the condition.type so
    V2 passes; ``coloring`` for action.dsl so V3 passes."""
    return {
        "id": rule_id,
        "concept": "paint_origin_with_5",
        "category": "color_transform",
        "condition": {
            "type": "grid_size_preserved",
            "params": {},
            "min_evidence": 1,
        },
        "action": {
            "dsl": "coloring",
            "args": {"selection": [[0, 0]], "color": 5},
        },
        "covers": [hex_],
        "source_task": hex_,
        "anti_unification_trace": None,
        "created_at": "2026-05-13T00:00:00",
        "times_reused": 0,
    }


def _schema_rule_identity(rule_id: int = 1, hex_: str = HEX) -> dict:
    """A §1-compliant no-op identity rule (the iter-14 translator's
    output shape). Should be skipped by the fast-path identity guard."""
    return {
        "id": rule_id,
        "concept": "identity",
        "category": "other",
        "condition": {
            "type": "identity_transformation",
            "params": {},
            "min_evidence": 1,
        },
        "action": {
            "dsl": "coloring",
            "args": {"selection": [], "color": 0},
        },
        "covers": [hex_],
        "source_task": hex_,
        "anti_unification_trace": None,
        "created_at": "2026-05-13T00:00:00",
        "times_reused": 0,
    }


def _schema_rule_make_grid(rule_id: int = 1, hex_: str = HEX) -> dict:
    """A §1-compliant ``make_grid`` rule: produce a 2x2 grid of zeros.
    Exercises the ``grid=None`` dispatch branch in ``apply_DSL``."""
    return {
        "id": rule_id,
        "concept": "fresh_2x2_canvas",
        "category": "other",
        "condition": {
            "type": "grid_size_preserved",
            "params": {},
            "min_evidence": 1,
        },
        "action": {
            "dsl": "make_grid",
            "args": {"height": 2, "width": 2, "color": 0},
        },
        "covers": [hex_],
        "source_task": hex_,
        "anti_unification_trace": None,
        "created_at": "2026-05-13T00:00:00",
        "times_reused": 0,
    }


def _legacy_entry_color_mapping(rule_id: int = 1, hex_: str = HEX) -> dict:
    """The pre-iter-14 wrapped shape produced by ``save_rule_to_ltm`` —
    a top-level ``rule`` payload. Used to confirm iter-16 does NOT break
    the existing legacy dispatch."""
    return {
        "id": rule_id,
        "concept": "swap_two_colors",
        "category": "color_transform",
        "rule": {"type": "color_mapping", "mapping": {0: 1, 1: 0}},
        "covers": [hex_],
        "source_task": hex_,
        "created_at": "2026-05-13T00:00:00",
        "times_reused": 0,
    }


def _legacy_entry_identity(rule_id: int = 1, hex_: str = HEX) -> dict:
    """Pre-iter-14 wrapped identity. Should be skipped just like the
    schema-shaped identity rule."""
    return {
        "id": rule_id,
        "concept": "identity",
        "category": "other",
        "rule": {"type": "identity"},
        "covers": [hex_],
        "source_task": hex_,
        "created_at": "2026-05-13T00:00:00",
        "times_reused": 0,
    }


# ──────────────────────────────────────────────────────────────────────────
# Tests — helper surface.
# ──────────────────────────────────────────────────────────────────────────

def test_helpers_exist_on_active_soar_agent() -> None:
    # The iter-16 migration adds these methods to the class. Test their
    # presence so a future refactor that renames them surfaces here.
    for name in (
        "_is_identity_rule",
        "_entry_rule_type",
        "_entry_matches_examples",
        "_apply_entry_to_tests",
        "_predict_with_entry",
    ):
        assert hasattr(ActiveSoarAgent, name), f"missing helper: {name}"
        assert callable(getattr(ActiveSoarAgent, name)), f"not callable: {name}"


def test_pre_iter_16_helper_names_removed() -> None:
    # The dispatchers were renamed (not aliased). If the old names
    # survive, a partial refactor went in — surface that immediately.
    for name in ("_rule_matches_examples", "_apply_rule_to_tests"):
        assert not hasattr(ActiveSoarAgent, name), (
            f"pre-iter-16 helper {name} still present — iter-16 rename incomplete"
        )


# ──────────────────────────────────────────────────────────────────────────
# Tests — _predict_with_entry across both shapes.
# ──────────────────────────────────────────────────────────────────────────

def test_predict_legacy_identity_returns_input_copy() -> None:
    # Regression: legacy "identity" type still produces an input copy.
    a = _agent(_tmp())
    entry = _legacy_entry_identity()
    g = _grid([[1, 2], [3, 4]])
    out = a._predict_with_entry(entry, g)
    assert out == [[1, 2], [3, 4]], f"expected identity copy; got {out!r}"
    # purity: returned list is not the input.raw object
    assert out is not g.raw, "predict must not return the input.raw object"


def test_predict_legacy_color_mapping_works() -> None:
    # Regression: legacy color_mapping dispatch through PredictOperator
    # still produces mapped output. Uses int-keyed mapping (matches the
    # in-memory pipeline shape; legacy on-disk JSON would be str-keyed).
    a = _agent(_tmp())
    entry = _legacy_entry_color_mapping()
    g = _grid([[0, 1], [1, 0]])
    out = a._predict_with_entry(entry, g)
    assert out == [[1, 0], [0, 1]], f"legacy color_mapping broke; got {out!r}"


def test_predict_schema_coloring_paints_cell() -> None:
    # The headline new behavior: a §1 schema entry routes through
    # apply_DSL("coloring", ...) and the saved (0,0) selection is painted.
    a = _agent(_tmp())
    entry = _schema_rule_paint_origin()
    g = _grid([[0, 0, 0], [0, 0, 0]])
    out = a._predict_with_entry(entry, g)
    assert out == [[5, 0, 0], [0, 0, 0]], f"expected (0,0) painted to 5; got {out!r}"
    # purity: input.raw untouched
    assert g.raw == [[0, 0, 0], [0, 0, 0]], "predict mutated input.raw"


def test_predict_schema_coloring_empty_selection_is_no_op() -> None:
    # The identity-shaped schema rule produced by translate_to_schema:
    # selection=[], color=0 — apply_DSL must return an identity copy.
    a = _agent(_tmp())
    entry = _schema_rule_identity()
    g = _grid([[7, 8], [9, 0]])
    out = a._predict_with_entry(entry, g)
    assert out == [[7, 8], [9, 0]], f"empty selection should be no-op; got {out!r}"


def test_predict_schema_make_grid_ignores_input() -> None:
    # Schema rules whose dsl is "make_grid" produce a fresh canvas; the
    # dispatch must omit the input grid (apply_DSL's grid=None branch).
    a = _agent(_tmp())
    entry = _schema_rule_make_grid()
    g = _grid([[5, 5, 5], [5, 5, 5], [5, 5, 5]])  # different shape
    out = a._predict_with_entry(entry, g)
    assert out == [[0, 0], [0, 0]], f"expected fresh 2x2 grid; got {out!r}"


def test_predict_schema_unknown_dsl_returns_none() -> None:
    # action.dsl outside DSL_REGISTRY → None (the rule does not apply
    # here). Matches the legacy applier's graceful-fail semantic.
    a = _agent(_tmp())
    entry = _schema_rule_paint_origin()
    entry["action"]["dsl"] = "no_such_primitive"
    g = _grid([[0, 0], [0, 0]])
    assert a._predict_with_entry(entry, g) is None


def test_predict_schema_oob_selection_returns_none() -> None:
    # OOB coords raise ValueError from coloring; the dispatch turns
    # that into None ("rule does not apply to this grid"). Without
    # this catch, a saved 5x5 rule applied to a 3x3 task would crash
    # the whole solve(). F7 is not engaged: ValueError ≠ RuleSchemaError.
    a = _agent(_tmp())
    entry = _schema_rule_paint_origin()
    entry["action"]["args"] = {"selection": [[10, 10]], "color": 5}
    g = _grid([[0, 0], [0, 0]])
    assert a._predict_with_entry(entry, g) is None


def test_predict_non_dict_entry_returns_none() -> None:
    a = _agent(_tmp())
    g = _grid([[0, 0]])
    for bad in (None, "rule", 42, ["rule"]):
        assert a._predict_with_entry(bad, g) is None


def test_predict_none_input_returns_none() -> None:
    a = _agent(_tmp())
    entry = _schema_rule_paint_origin()
    assert a._predict_with_entry(entry, None) is None


def test_predict_does_not_mutate_entry() -> None:
    # The dispatch must not mutate the entry dict (load_all_rules
    # passes the parsed JSON; mutating it would corrupt later iterations
    # of the fast-path loop within the same solve).
    a = _agent(_tmp())
    entry = _schema_rule_paint_origin()
    snapshot = json.loads(json.dumps(entry))
    g = _grid([[0, 0], [0, 0]])
    a._predict_with_entry(entry, g)
    assert entry == snapshot, "predict mutated the entry dict"


# ──────────────────────────────────────────────────────────────────────────
# Tests — _is_identity_rule across both shapes.
# ──────────────────────────────────────────────────────────────────────────

def test_is_identity_rule_legacy_shape() -> None:
    a = _agent(_tmp())
    assert a._is_identity_rule(_legacy_entry_identity()) is True


def test_is_identity_rule_schema_shape() -> None:
    a = _agent(_tmp())
    assert a._is_identity_rule(_schema_rule_identity()) is True


def test_is_identity_rule_rejects_non_identity_legacy() -> None:
    a = _agent(_tmp())
    assert a._is_identity_rule(_legacy_entry_color_mapping()) is False


def test_is_identity_rule_rejects_non_identity_schema() -> None:
    a = _agent(_tmp())
    assert a._is_identity_rule(_schema_rule_paint_origin()) is False


def test_is_identity_rule_rejects_non_dict() -> None:
    a = _agent(_tmp())
    for bad in (None, "identity", 42, ["identity"]):
        assert a._is_identity_rule(bad) is False


# ──────────────────────────────────────────────────────────────────────────
# Tests — _entry_rule_type across both shapes.
# ──────────────────────────────────────────────────────────────────────────

def test_entry_rule_type_legacy_shape() -> None:
    a = _agent(_tmp())
    assert a._entry_rule_type(_legacy_entry_color_mapping()) == "color_mapping"


def test_entry_rule_type_schema_shape() -> None:
    a = _agent(_tmp())
    # Schema entries surface condition.type — the iter-13 matcher names
    # are the canonical recognition vocabulary.
    assert a._entry_rule_type(_schema_rule_paint_origin()) == "grid_size_preserved"
    assert a._entry_rule_type(_schema_rule_identity()) == "identity_transformation"


def test_entry_rule_type_fallback_unknown() -> None:
    a = _agent(_tmp())
    assert a._entry_rule_type({}) == "unknown"
    assert a._entry_rule_type(None) == "unknown"


# ──────────────────────────────────────────────────────────────────────────
# Tests — _entry_matches_examples + _apply_entry_to_tests.
# ──────────────────────────────────────────────────────────────────────────

def test_entry_matches_examples_schema_accepts_when_action_reproduces_output() -> None:
    a = _agent(_tmp())
    entry = _schema_rule_paint_origin()
    pairs = [
        _pair([[0, 0], [0, 0]], [[5, 0], [0, 0]]),
        _pair([[1, 2], [3, 4]], [[5, 2], [3, 4]]),
    ]
    task = _task(HEX, pairs, [])
    assert a._entry_matches_examples(entry, task) is True


def test_entry_matches_examples_schema_rejects_on_mismatch() -> None:
    a = _agent(_tmp())
    entry = _schema_rule_paint_origin()
    # Output expected at (0,0) is 9, not 5 — rule should not match.
    pairs = [_pair([[0, 0], [0, 0]], [[9, 0], [0, 0]])]
    task = _task(HEX, pairs, [])
    assert a._entry_matches_examples(entry, task) is False


def test_entry_matches_examples_legacy_unchanged() -> None:
    # Regression: legacy color_mapping rule still matches a swap-pair task.
    a = _agent(_tmp())
    entry = _legacy_entry_color_mapping()
    pairs = [_pair([[0, 1], [1, 0]], [[1, 0], [0, 1]])]
    task = _task(HEX, pairs, [])
    assert a._entry_matches_examples(entry, task) is True


def test_entry_matches_examples_skips_pair_with_none_grid() -> None:
    # A pair with a missing input or output grid is skipped (matches
    # pre-iter-16 behavior — the legacy ``_rule_matches_examples`` did
    # the same).
    a = _agent(_tmp())
    entry = _schema_rule_paint_origin()
    pairs = [
        _pair(None, [[5, 0]]),                # input missing → skipped
        _pair([[0, 0]], None),                # output missing → skipped
        _pair([[0, 0]], [[5, 0]]),            # the only pair that counts
    ]
    task = _task(HEX, pairs, [])
    assert a._entry_matches_examples(entry, task) is True


def test_apply_entry_to_tests_schema_produces_predictions() -> None:
    a = _agent(_tmp())
    entry = _schema_rule_paint_origin()
    tests = [
        _pair([[0, 0, 0], [0, 0, 0]], None),
        _pair([[1, 1], [1, 1]], None),
    ]
    task = _task(HEX, [], tests)
    out = a._apply_entry_to_tests(entry, task)
    assert out == [
        [[5, 0, 0], [0, 0, 0]],
        [[5, 1], [1, 1]],
    ], f"unexpected test predictions: {out!r}"


def test_apply_entry_to_tests_returns_none_on_missing_input() -> None:
    a = _agent(_tmp())
    entry = _schema_rule_paint_origin()
    tests = [_pair([[0, 0]], None), _pair(None, None)]  # second has None input
    task = _task(HEX, [], tests)
    assert a._apply_entry_to_tests(entry, task) is None


# ──────────────────────────────────────────────────────────────────────────
# Tests — end-to-end solve() smoke.
# ──────────────────────────────────────────────────────────────────────────

def test_solve_uses_schema_rule_saved_via_save_rule() -> None:
    # The iter-15 → iter-16 wiring proof: save a §1 schema rule via
    # save_rule, build a task that matches it, call solve(). The fast
    # path must consume the rule (last_solve_info.method == "stored_rule")
    # and increment times_reused on disk. Pre-iter-16, this rule would
    # have been silently skipped because entry.get("rule", {}) is {}.
    proc_root = _tmp()
    epi_root = _tmp()
    try:
        # Construct and persist a non-identity schema rule via the
        # canonical writer. No related_rules — sole writer path.
        rule = _schema_rule_paint_origin()
        rule_path = save_rule(rule, procedural_memory_root=proc_root)
        assert os.path.isfile(rule_path)

        a = _agent(proc_root, epi_root)
        examples = [_pair([[0, 0], [0, 0]], [[5, 0], [0, 0]])]
        tests = [_pair([[0, 0, 0], [0, 0, 0]], None)]
        task = _task(HEX, examples, tests)

        predicted = a.solve(task)
        assert predicted == [[[5, 0, 0], [0, 0, 0]]], (
            f"solve should hit fast path and apply schema rule; got {predicted!r}"
        )
        assert a.last_solve_info.get("method") == "stored_rule"
        assert a.last_solve_info.get("rule_type") == "grid_size_preserved"
        assert a.last_solve_info.get("rule_source") == HEX

        # times_reused must have been incremented and persisted.
        with open(rule_path, encoding="utf-8") as fh:
            saved = json.load(fh)
        assert saved["times_reused"] == 1, (
            f"increment_reuse_count did not persist; got {saved['times_reused']!r}"
        )
    finally:
        shutil.rmtree(proc_root, ignore_errors=True)
        shutil.rmtree(epi_root, ignore_errors=True)


def test_solve_skips_schema_identity_rule_on_disk() -> None:
    # A saved schema identity rule must be skipped by the fast path so
    # it does not over-predict identity for non-identity tasks. The
    # slow path runs instead (pipeline) — we only assert the fast path
    # did NOT label the result as "stored_rule".
    proc_root = _tmp()
    epi_root = _tmp()
    try:
        save_rule(_schema_rule_identity(), procedural_memory_root=proc_root)
        a = _agent(proc_root, epi_root)
        # Identity-matching example: input == output. Even though the
        # identity rule would "match" this, the iter-16 guard skips it.
        examples = [_pair([[1, 2], [3, 4]], [[1, 2], [3, 4]])]
        tests = [_pair([[5, 6], [7, 8]], None)]
        task = _task(HEX, examples, tests)
        a.solve(task)
        assert a.last_solve_info.get("method") != "stored_rule", (
            "schema identity rule must be skipped by the fast path"
        )
    finally:
        shutil.rmtree(proc_root, ignore_errors=True)
        shutil.rmtree(epi_root, ignore_errors=True)


# ──────────────────────────────────────────────────────────────────────────
# Driver.
# ──────────────────────────────────────────────────────────────────────────

def _run_all() -> int:
    tests = [
        test_helpers_exist_on_active_soar_agent,
        test_pre_iter_16_helper_names_removed,
        test_predict_legacy_identity_returns_input_copy,
        test_predict_legacy_color_mapping_works,
        test_predict_schema_coloring_paints_cell,
        test_predict_schema_coloring_empty_selection_is_no_op,
        test_predict_schema_make_grid_ignores_input,
        test_predict_schema_unknown_dsl_returns_none,
        test_predict_schema_oob_selection_returns_none,
        test_predict_non_dict_entry_returns_none,
        test_predict_none_input_returns_none,
        test_predict_does_not_mutate_entry,
        test_is_identity_rule_legacy_shape,
        test_is_identity_rule_schema_shape,
        test_is_identity_rule_rejects_non_identity_legacy,
        test_is_identity_rule_rejects_non_identity_schema,
        test_is_identity_rule_rejects_non_dict,
        test_entry_rule_type_legacy_shape,
        test_entry_rule_type_schema_shape,
        test_entry_rule_type_fallback_unknown,
        test_entry_matches_examples_schema_accepts_when_action_reproduces_output,
        test_entry_matches_examples_schema_rejects_on_mismatch,
        test_entry_matches_examples_legacy_unchanged,
        test_entry_matches_examples_skips_pair_with_none_grid,
        test_apply_entry_to_tests_schema_produces_predictions,
        test_apply_entry_to_tests_returns_none_on_missing_input,
        test_solve_uses_schema_rule_saved_via_save_rule,
        test_solve_skips_schema_identity_rule_on_disk,
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
        print("\nall fast-path-schema-rule tests passed.")
    else:
        print(f"\n{rc} test(s) failed.")
    sys.exit(0 if rc == 0 else 1)
