"""
tests/test_next_rule_id.py — exercise the iter-15 helper
``agent.memory.next_rule_id``. The helper feeds the ``rule_id`` argument
of ``translate_to_schema`` immediately before ``save_rule`` is invoked
from ``agent/active_agent.py:solve()``; an off-by-one or a "len(files)+1"
shape would trip V6 (id collision) the first time a rule is removed
between sessions.

Runs without pytest:

    python tests/test_next_rule_id.py

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

from agent.memory import next_rule_id  # noqa: E402


def _tmp() -> str:
    return tempfile.mkdtemp(prefix="next_rule_id_test_")


def _touch_rule(root: str, n: int, *, width: int = 3) -> str:
    """Drop a minimal rule file under ``root`` named ``rule_{n:0{width}d}.json``."""
    name = f"rule_{n:0{width}d}.json"
    path = os.path.join(root, name)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"id": n}, fh)
    return path


# ──────────────────────────────────────────────────────────────────────────
# Tests.
# ──────────────────────────────────────────────────────────────────────────

def test_returns_one_when_directory_is_missing() -> None:
    root = _tmp()
    try:
        shutil.rmtree(root)
        assert not os.path.isdir(root)
        assert next_rule_id(root) == 1
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_returns_one_when_directory_is_empty() -> None:
    root = _tmp()
    try:
        assert os.path.isdir(root) and not os.listdir(root)
        assert next_rule_id(root) == 1
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_returns_two_after_first_rule_written() -> None:
    root = _tmp()
    try:
        _touch_rule(root, 1)
        assert next_rule_id(root) == 2
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_returns_max_plus_one_with_contiguous_ids() -> None:
    root = _tmp()
    try:
        for i in range(1, 6):
            _touch_rule(root, i)
        assert next_rule_id(root) == 6
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_returns_max_plus_one_with_holes() -> None:
    # The gap-tolerant contract: monotonic ids survive deletions.
    root = _tmp()
    try:
        _touch_rule(root, 1)
        _touch_rule(root, 4)
        _touch_rule(root, 7)
        assert next_rule_id(root) == 8
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_ignores_non_rule_files() -> None:
    root = _tmp()
    try:
        _touch_rule(root, 1)
        # neighbouring files that must not perturb the count
        with open(os.path.join(root, "rule_template.txt"), "w") as fh:
            fh.write("not json")
        with open(os.path.join(root, "ruleset_002.json"), "w") as fh:
            fh.write("{}")
        with open(os.path.join(root, "README.md"), "w") as fh:
            fh.write("# x")
        os.makedirs(os.path.join(root, "rule_999"), exist_ok=False)  # subdir, no .json
        assert next_rule_id(root) == 2
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_ignores_rule_with_non_integer_stem() -> None:
    root = _tmp()
    try:
        _touch_rule(root, 3)
        # malformed but rule_*.json shaped — must not crash, must not promote
        with open(os.path.join(root, "rule_abc.json"), "w") as fh:
            fh.write("{}")
        with open(os.path.join(root, "rule_007a.json"), "w") as fh:
            fh.write("{}")
        with open(os.path.join(root, "rule_.json"), "w") as fh:
            fh.write("{}")
        assert next_rule_id(root) == 4
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_ignores_rule_with_zero_or_negative_stem() -> None:
    # rule_000.json could exist by typo; V6 requires id >= 1, so ignore.
    root = _tmp()
    try:
        with open(os.path.join(root, "rule_000.json"), "w") as fh:
            fh.write("{}")
        # negatives can only appear if hand-written; tolerate without crash
        with open(os.path.join(root, "rule_-1.json"), "w") as fh:
            fh.write("{}")
        assert next_rule_id(root) == 1
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_tolerates_wider_zero_padding() -> None:
    # A future migration emitting rule_0042.json must not collide with
    # an existing rule_042.json that is already on disk.
    root = _tmp()
    try:
        _touch_rule(root, 42, width=4)  # rule_0042.json
        assert next_rule_id(root) == 43
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_returns_int_type() -> None:
    root = _tmp()
    try:
        _touch_rule(root, 5)
        n = next_rule_id(root)
        assert isinstance(n, int) and not isinstance(n, bool)
        assert n == 6
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_does_not_mutate_directory() -> None:
    root = _tmp()
    try:
        _touch_rule(root, 1)
        _touch_rule(root, 2)
        before = sorted(os.listdir(root))
        next_rule_id(root)
        next_rule_id(root)
        next_rule_id(root)
        after = sorted(os.listdir(root))
        assert before == after
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_deterministic_across_repeats() -> None:
    root = _tmp()
    try:
        _touch_rule(root, 1)
        _touch_rule(root, 3)
        first = next_rule_id(root)
        second = next_rule_id(root)
        assert first == second == 4
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_yields_id_passing_save_rule_v6_collision_check() -> None:
    # End-to-end harmony: the value next_rule_id returns must be the very
    # next id that save_rule will accept without raising V6.
    root = _tmp()
    try:
        _touch_rule(root, 1)
        _touch_rule(root, 2)
        nid = next_rule_id(root)
        target = os.path.join(root, f"rule_{nid:03d}.json")
        assert not os.path.exists(target), \
            f"next_rule_id returned {nid}, but {target} already exists"
        assert nid == 3
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ──────────────────────────────────────────────────────────────────────────
# Driver.
# ──────────────────────────────────────────────────────────────────────────

def _run_all() -> int:
    tests = [
        test_returns_one_when_directory_is_missing,
        test_returns_one_when_directory_is_empty,
        test_returns_two_after_first_rule_written,
        test_returns_max_plus_one_with_contiguous_ids,
        test_returns_max_plus_one_with_holes,
        test_ignores_non_rule_files,
        test_ignores_rule_with_non_integer_stem,
        test_ignores_rule_with_zero_or_negative_stem,
        test_tolerates_wider_zero_padding,
        test_returns_int_type,
        test_does_not_mutate_directory,
        test_deterministic_across_repeats,
        test_yields_id_passing_save_rule_v6_collision_check,
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
        print("\nall next_rule_id tests passed.")
    else:
        print(f"\n{rc} test(s) failed.")
    sys.exit(0 if rc == 0 else 1)
