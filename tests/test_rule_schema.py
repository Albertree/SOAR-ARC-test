"""
Tests for the {condition, action} rule-schema spine in agent/memory.py:
translate_to_schema / validate_rule / save_rule_to_ltm / migrate_legacy_rules.

Runnable with `pytest tests/ -q` or directly: `python tests/test_rule_schema.py`.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agent.memory as m  # noqa: E402


def _valid_payload():
    return {"type": "color_mapping", "mapping": {"2": 0, "0": 2}, "confidence": 0.8}


def test_translate_round_trips_operational_payload():
    payload = _valid_payload()
    entry = m.translate_to_schema(payload, rule_id=7, task_hex="easy0001")
    m.validate_rule(entry)
    assert entry["condition"]["type"] == "color_mapping"
    assert entry["action"]["dsl"] == "coloring"
    # the operational payload survives verbatim and is recoverable
    assert entry["action"]["args"] == payload
    assert m._operational_view(entry) == payload


def test_validate_accepts_well_formed_rule():
    entry = m.translate_to_schema(_valid_payload(), rule_id=1, task_hex="08ed6ac7")
    m.validate_rule(entry)  # must not raise


def _expect_error(entry, needle):
    try:
        m.validate_rule(entry)
    except m.RuleSchemaError as e:
        assert needle in str(e), f"wrong error for {needle!r}: {e}"
        return
    raise AssertionError(f"expected RuleSchemaError containing {needle!r}")


def test_validate_rejects_missing_condition():
    entry = m.translate_to_schema(_valid_payload(), rule_id=1, task_hex="easy0001")
    del entry["condition"]
    _expect_error(entry, "missing required key")


def test_validate_rejects_unknown_condition_type():
    entry = m.translate_to_schema(_valid_payload(), rule_id=1, task_hex="easy0001")
    entry["condition"]["type"] = "totally_made_up"
    _expect_error(entry, "unknown condition.type")


def test_validate_rejects_unknown_action_dsl():
    entry = m.translate_to_schema(_valid_payload(), rule_id=1, task_hex="easy0001")
    entry["action"]["dsl"] = "rotate"  # not one of the two frozen primitives
    _expect_error(entry, "unknown action.dsl")


def test_validate_rejects_source_not_in_covers():
    entry = m.translate_to_schema(_valid_payload(), rule_id=1, task_hex="easy0001")
    entry["source_task"] = "easy9999"
    _expect_error(entry, "source_task must appear in covers")


def test_validate_rejects_extra_top_level_key():
    entry = m.translate_to_schema(_valid_payload(), rule_id=1, task_hex="easy0001")
    entry["rule"] = {"type": "color_mapping"}  # the legacy key is forbidden now
    _expect_error(entry, "unexpected top-level key")


def test_save_and_migrate(tmp_path=None):
    import tempfile
    root = tmp_path if tmp_path is not None else tempfile.mkdtemp()
    root = str(root)

    # save a fresh rule -> a schema-valid file on disk
    path = m.save_rule_to_ltm(_valid_payload(), "easy0001", root)
    with open(path, encoding="utf-8") as fh:
        on_disk = json.load(fh)
    assert "condition" in on_disk and "action" in on_disk
    assert "rule" not in on_disk  # no legacy top-level key persisted
    m.validate_rule(on_disk)

    # an equivalent rule for a new task extends covers, no duplicate file
    m.save_rule_to_ltm(_valid_payload(), "easy0003", root)
    files = [f for f in os.listdir(root) if f.startswith("rule_")]
    assert len(files) == 1, files
    with open(os.path.join(root, files[0]), encoding="utf-8") as fh:
        assert set(json.load(fh)["covers"]) == {"easy0001", "easy0003"}

    # a legacy-shape file gets migrated in place and then validates
    legacy = {
        "id": 9, "concept": "x", "category": "color_transform",
        "rule": {"type": "color_mapping", "mapping": {"1": 0}},
        "covers": ["easy000z"], "source_task": "easy000z",
        "created_at": "2026-06-11T00:00:00", "times_reused": 0,
    }
    lpath = os.path.join(root, "rule_009.json")
    with open(lpath, "w", encoding="utf-8") as fh:
        json.dump(legacy, fh)
    migrated = m.migrate_legacy_rules(root)
    assert lpath in migrated
    with open(lpath, encoding="utf-8") as fh:
        m.validate_rule(json.load(fh))


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\n{len(fns)} tests passed")
