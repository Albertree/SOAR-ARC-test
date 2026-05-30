"""Regression: save_rule_to_ltm must not clobber an existing rule_NNN.json.

The new-rule id was assigned as len(existing)+1, which collides with an id still
in use whenever the id set is non-contiguous (e.g. the dir holds rule_001.json
and rule_003.json -> len==2 -> id 3 -> rewrites rule_003.json, silently
destroying the survivor -> P1 coverage regression, no error). The id is now
max(existing index)+1, which is always free regardless of gaps.

Standalone runner (no pytest dependency):
    python tests/test_next_rule_id_no_clobber.py
"""

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent.memory import save_rule_to_ltm

_passed = 0
_failed = 0


def check(label, cond):
    global _passed, _failed
    if cond:
        _passed += 1
        print(f"  ok   {label}")
    else:
        _failed += 1
        print(f"  FAIL {label}")


def _survivor(idx, rtype):
    """A complete-enough stored entry; only json-loaded for the equivalence
    scan, never re-validated, so its condition.type need not resolve."""
    return {
        "id": idx,
        "rule": {"type": rtype},
        "covers": [f"task{idx}"],
        "source_task": f"task{idx}",
    }


def test_non_contiguous_ids_do_not_clobber():
    with tempfile.TemporaryDirectory() as d:
        # Non-contiguous set: rule_001 + rule_003 (rule_002 was deleted). With
        # the old len()+1 numbering a new save lands on id 3 and clobbers
        # rule_003.json; max-based numbering picks id 4.
        for idx, rtype in ((1, "identity"), (3, "recolor_sequential")):
            with open(os.path.join(d, f"rule_{idx:03d}.json"), "w",
                      encoding="utf-8") as fh:
                json.dump(_survivor(idx, rtype), fh)

        # A genuinely new (non-equivalent) Slice-1-shaped payload -> new file.
        new_rule = {"type": "copy_common_output", "confidence": 1.0}
        path = save_rule_to_ltm(new_rule, "easy000a", procedural_memory_root=d)

        check("returned path is rule_004.json", path.endswith("rule_004.json"))
        check("survivor rule_003.json still exists",
              os.path.exists(os.path.join(d, "rule_003.json")))
        with open(os.path.join(d, "rule_003.json"), encoding="utf-8") as fh:
            survivor = json.load(fh)
        check("survivor rule_003 content intact (not clobbered)",
              survivor.get("rule", {}).get("type") == "recolor_sequential")
        with open(path, encoding="utf-8") as fh:
            saved = json.load(fh)
        check("new rule id is 4", saved.get("id") == 4)


def test_empty_dir_still_starts_at_one():
    with tempfile.TemporaryDirectory() as d:
        path = save_rule_to_ltm({"type": "copy_common_output", "confidence": 1.0},
                                "easy000a", procedural_memory_root=d)
        check("first rule in empty dir is rule_001.json",
              path.endswith("rule_001.json"))


if __name__ == "__main__":
    test_non_contiguous_ids_do_not_clobber()
    test_empty_dir_still_starts_at_one()
    print(f"\ntest_next_rule_id_no_clobber: {_passed} passed, {_failed} failed")
    sys.exit(1 if _failed else 0)
