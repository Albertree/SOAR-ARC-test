"""Tests for agent.memory.validate_rule / RuleSchemaError.

validate_rule is ARBOR's in-process guard against the dead-memory failure mode
(a rule the fast path cannot look up). It enforces CLAUDE.md §3.2's hard
requirements 1-2 plus docs/RULE_FORMAT.md V4, raising RuleSchemaError *before*
a malformed entry can be written to disk — the same boundary INVARIANTS §1 F4
enforces post-hoc by auto-revert.

Standalone runner (no pytest dependency): `python tests/test_validate_rule.py`.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent.memory import RuleSchemaError, validate_rule, save_rule_to_ltm, save_rule


def _valid_entry():
    """A minimal entry shaped exactly like what save_rule_to_ltm builds, using
    the only registered names a Slice-1 rule actually carries (rule_003)."""
    return {
        "id": 1,
        "concept": "copy_common_example_output",
        "category": "other",
        "condition": {"type": "all_outputs_comm", "params": {}, "min_evidence": 1},
        "action": {"dsl": "make_grid", "args": {}},
        "rule": {"type": "copy_common_output", "confidence": 1.0},
        "covers": ["easy000a", "easy000a2"],
        "source_task": "easy000a",
        "anti_unification_trace": None,
        "created_at": "2026-05-29T20:02:33.463388",
        "times_reused": 0,
    }


def _assert_raises(fn, needle=None):
    try:
        fn()
    except RuleSchemaError as e:
        if needle is not None:
            assert needle in str(e), f"expected {needle!r} in {e!r}"
        return
    raise AssertionError("expected RuleSchemaError, none raised")


# --- the live rule passes -------------------------------------------------

def test_live_rule_shape_validates():
    # The shape of the only live rule (rule_003) must pass untouched, or the
    # Slice-1 solve path would break.
    validate_rule(_valid_entry())  # must not raise


def test_subclass_of_valueerror():
    assert issubclass(RuleSchemaError, ValueError)


# --- (1) {condition, action} pair present and non-empty -------------------

def test_missing_condition_raises():
    e = _valid_entry(); del e["condition"]
    _assert_raises(lambda: validate_rule(e), "condition")


def test_empty_condition_raises():
    e = _valid_entry(); e["condition"] = {}
    _assert_raises(lambda: validate_rule(e), "condition")


def test_missing_action_raises():
    e = _valid_entry(); del e["action"]
    _assert_raises(lambda: validate_rule(e), "action")


def test_empty_action_raises():
    e = _valid_entry(); e["action"] = {}
    _assert_raises(lambda: validate_rule(e), "action")


def test_blank_condition_type_raises():
    e = _valid_entry(); e["condition"]["type"] = ""
    _assert_raises(lambda: validate_rule(e), "condition.type")


def test_blank_action_dsl_raises():
    e = _valid_entry(); e["action"]["dsl"] = ""
    _assert_raises(lambda: validate_rule(e), "action.dsl")


def test_non_dict_entry_raises():
    _assert_raises(lambda: validate_rule(["not", "a", "dict"]), "dict")


# --- (2) referenced names must resolve in their registries ----------------

def test_unknown_condition_type_raises():
    e = _valid_entry(); e["condition"]["type"] = "no_such_matcher"
    _assert_raises(lambda: validate_rule(e), "unknown condition.type")


def test_unknown_action_dsl_raises():
    # A hand-coded transformation name (e.g. "rotate") that is NOT one of the
    # two frozen primitives is dead memory: it can never dispatch.
    e = _valid_entry(); e["action"]["dsl"] = "rotate"
    _assert_raises(lambda: validate_rule(e), "unknown action.dsl")


def test_each_registered_condition_type_validates():
    # Every live matcher name must be accepted (no false negatives).
    from agent.conditions import CONDITION_REGISTRY
    for name in CONDITION_REGISTRY:
        e = _valid_entry(); e["condition"]["type"] = name
        validate_rule(e)  # must not raise


# --- (3) source_task in covers (RULE_FORMAT V4) ---------------------------

def test_source_task_not_in_covers_raises():
    e = _valid_entry(); e["source_task"] = "ffffffff"
    _assert_raises(lambda: validate_rule(e), "source_task")


def test_empty_covers_raises():
    e = _valid_entry(); e["covers"] = []
    _assert_raises(lambda: validate_rule(e), "covers")


# --- save_rule_to_ltm refuses an invalid new entry ------------------------

def test_save_rule_alias_is_same_function():
    assert save_rule is save_rule_to_ltm


def test_save_rule_to_ltm_writes_valid_rule(tmp_root=None):
    # A copy_common_output rule (-> all_outputs_comm / make_grid) is valid and
    # must be written; assert a rule_*.json appears.
    with tempfile.TemporaryDirectory() as d:
        path = save_rule_to_ltm(
            {"type": "copy_common_output", "confidence": 1.0},
            "easy000a",
            procedural_memory_root=d,
        )
        assert os.path.isfile(path), "valid rule should be written"
        assert path.endswith(".json")


def test_save_rule_to_ltm_rejects_dead_memory_rule():
    # A rule whose type maps to no registered matcher must be refused at save
    # time, not silently written as dead memory. _build_condition turns an
    # unknown rule type into "<type>_pattern", which is unregistered.
    with tempfile.TemporaryDirectory() as d:
        _assert_raises(
            lambda: save_rule_to_ltm(
                {"type": "totally_unknown_transform"}, "easy000a",
                procedural_memory_root=d,
            ),
            "unknown condition.type",
        )
        # nothing should have been written
        leftover = [f for f in os.listdir(d) if f.startswith("rule_")]
        assert leftover == [], f"dead-memory rule leaked to disk: {leftover}"


if __name__ == "__main__":
    funcs = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in funcs:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {fn.__name__}: {e}")
        except Exception as e:  # noqa: BLE001 — surface unexpected errors loudly
            failed += 1
            print(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(funcs) - failed}/{len(funcs)} passed")
    sys.exit(1 if failed else 0)
