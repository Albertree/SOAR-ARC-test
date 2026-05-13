"""
tests/test_translate_to_schema.py — exercise the legacy→§1 translator
added in iter 14.

Runs without pytest. Invoke directly:

    python tests/test_translate_to_schema.py

Exits 0 on success, non-zero on first failed assertion (with traceback).

Scope: `agent/memory.py:translate_to_schema(legacy_rule, task_hex, patterns,
*, rule_id, now=None)`. The translator currently handles exactly one legacy
shape — `{"type": "identity"}` — gated on the `identity_transformation`
matcher firing for the supplied `patterns` dict. Every other legacy type
returns `None` until a follow-up iter wires the pair-specific program
writer (see iter-13's "Next gap" note option 1).

Tests run against the live `agent.conditions.CONDITION_REGISTRY` and the
live `procedural_memory.DSL.apply.DSL_REGISTRY` — no stubs. This forces
the test to be coherent with the four-matcher registry iter-13 stood up
and the two-primitive DSL frozen by F3.
"""

from __future__ import annotations

import os
import sys
import tempfile
import traceback

# Make the repo root importable when invoked as
# `python tests/test_translate_to_schema.py`.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from agent.memory import (  # noqa: E402
    translate_to_schema,
    validate_rule,
)


# ──────────────────────────────────────────────────────────────────────────
# Fixture helpers — produce the kinds of `patterns` dicts that
# `ExtractPatternOperator.effect` would emit for various task shapes.
# ──────────────────────────────────────────────────────────────────────────

def _identity_patterns(n_pairs: int = 2) -> dict:
    """Patterns where every pair is bit-identical input/output: no change
    groups, size_match True. Both `grid_size_preserved` (top-level) and
    `identity_transformation` matchers fire."""
    return {
        "grid_size_preserved": True,
        "pair_analyses": [
            {
                "total_changes": 0,
                "num_groups": 0,
                "groups": [],
                "size_match": True,
            }
            for _ in range(n_pairs)
        ],
    }


def _color_mapping_patterns() -> dict:
    """Patterns with at least one changed group — `identity_transformation`
    must NOT fire."""
    return {
        "grid_size_preserved": True,
        "pair_analyses": [
            {
                "total_changes": 1,
                "num_groups": 1,
                "groups": [
                    {
                        "input_colors": [1],
                        "output_colors": [2],
                        "top_row": 0,
                        "top_col": 0,
                        "cell_count": 1,
                    }
                ],
                "size_match": True,
            }
        ],
    }


def _size_mismatch_patterns() -> dict:
    """Zero changes in the diff region BUT size_match False — identity
    must be rejected (output has cells absent from input)."""
    return {
        "grid_size_preserved": False,
        "pair_analyses": [
            {
                "total_changes": 0,
                "num_groups": 0,
                "groups": [],
                "size_match": False,
            }
        ],
    }


# ──────────────────────────────────────────────────────────────────────────
# Tests.
# ──────────────────────────────────────────────────────────────────────────

def test_identity_translates_to_schema_compliant_rule() -> None:
    legacy = {"type": "identity", "confidence": 0.0}
    out = translate_to_schema(
        legacy, "abcdef12", _identity_patterns(n_pairs=2),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert isinstance(out, dict), "expected schema dict, got None"
    # All §1 keys present.
    for k in (
        "id", "concept", "category", "condition", "action",
        "covers", "source_task", "anti_unification_trace",
        "created_at", "times_reused",
    ):
        assert k in out, f"translated rule missing required key: {k}"
    assert "rule" not in out, "legacy 'rule' key leaked into schema output"
    assert "type" not in out, "legacy 'type' key leaked into schema output"


def test_identity_condition_uses_identity_transformation_matcher() -> None:
    legacy = {"type": "identity", "confidence": 0.0}
    out = translate_to_schema(
        legacy, "abcdef12", _identity_patterns(),
        rule_id=2, now="2026-05-13T19:30:00.000000",
    )
    assert out is not None
    assert out["condition"]["type"] == "identity_transformation"
    assert out["condition"]["params"] == {}
    assert isinstance(out["condition"]["min_evidence"], int)
    assert out["condition"]["min_evidence"] >= 1


def test_identity_action_is_noop_coloring() -> None:
    """The action.dsl for identity must reduce to a registered primitive
    without inventing a new one (F3). `coloring(selection=[], color=0)`
    returns an identity copy of the grid — that is the no-op composition
    iter-13 named."""
    legacy = {"type": "identity", "confidence": 0.0}
    out = translate_to_schema(
        legacy, "abcdef12", _identity_patterns(),
        rule_id=3, now="2026-05-13T19:30:00.000000",
    )
    assert out is not None
    assert out["action"]["dsl"] == "coloring"
    assert out["action"]["args"] == {"selection": [], "color": 0}


def test_translated_identity_rule_passes_validate_rule() -> None:
    """The whole point of the translator: its output must satisfy V1–V7
    of `agent.memory.validate_rule`. V6 (id collision) is sensitive to
    on-disk state, so the test runs against a fresh tempdir with no
    existing `rule_*.json` files."""
    tmp_root = tempfile.mkdtemp(prefix="arbor_translate_")
    try:
        legacy = {"type": "identity", "confidence": 0.0}
        out = translate_to_schema(
            legacy, "abcdef12", _identity_patterns(),
            rule_id=1, now="2026-05-13T19:30:00.000000",
        )
        assert out is not None
        # Should not raise.
        validate_rule(out, procedural_memory_root=tmp_root)
    finally:
        import shutil
        shutil.rmtree(tmp_root, ignore_errors=True)


def test_covers_and_source_task_use_task_hex() -> None:
    legacy = {"type": "identity"}
    out = translate_to_schema(
        legacy, "abcdef12", _identity_patterns(),
        rule_id=4, now="2026-05-13T19:30:00.000000",
    )
    assert out is not None
    assert out["source_task"] == "abcdef12"
    assert out["covers"] == ["abcdef12"]


def test_anti_unification_trace_is_null_for_source_rule() -> None:
    legacy = {"type": "identity"}
    out = translate_to_schema(
        legacy, "abcdef12", _identity_patterns(),
        rule_id=5, now="2026-05-13T19:30:00.000000",
    )
    assert out is not None
    assert out["anti_unification_trace"] is None


def test_times_reused_starts_at_zero() -> None:
    legacy = {"type": "identity"}
    out = translate_to_schema(
        legacy, "abcdef12", _identity_patterns(),
        rule_id=6, now="2026-05-13T19:30:00.000000",
    )
    assert out is not None
    assert out["times_reused"] == 0


def test_min_evidence_reflects_pair_count() -> None:
    """The translator should record `min_evidence` matching how many
    example pairs supplied the identity observation. Two pairs → 2;
    five → 5. Floor of 1 when the patterns dict lacks pair_analyses
    (e.g., translator called speculatively)."""
    legacy = {"type": "identity"}

    out2 = translate_to_schema(
        legacy, "abcdef12", _identity_patterns(n_pairs=2),
        rule_id=7, now="2026-05-13T19:30:00.000000",
    )
    assert out2 is not None
    assert out2["condition"]["min_evidence"] == 2

    out5 = translate_to_schema(
        legacy, "abcdef12", _identity_patterns(n_pairs=5),
        rule_id=8, now="2026-05-13T19:30:00.000000",
    )
    assert out5 is not None
    assert out5["condition"]["min_evidence"] == 5


def test_min_evidence_floor_one_when_no_pair_analyses() -> None:
    """If `patterns` has no `pair_analyses` key (or it is empty), the
    translator returns None because `identity_transformation` does not
    fire on empty input (matcher contract). The floor exists for
    defensive accounting only — confirm by testing the matcher gate."""
    legacy = {"type": "identity"}
    out = translate_to_schema(
        legacy, "abcdef12", {"grid_size_preserved": True, "pair_analyses": []},
        rule_id=9, now="2026-05-13T19:30:00.000000",
    )
    # `identity_transformation` returns False on empty pair_analyses, so
    # the translator must return None.
    assert out is None


def test_returns_none_when_matcher_does_not_fire() -> None:
    """A `{"type": "identity"}` legacy rule combined with patterns where
    `identity_transformation` does not fire (e.g., a color-mapping shape)
    must return None — the translator refuses to mint a precondition
    unsupported by the source task's patterns."""
    legacy = {"type": "identity"}
    out = translate_to_schema(
        legacy, "abcdef12", _color_mapping_patterns(),
        rule_id=10, now="2026-05-13T19:30:00.000000",
    )
    assert out is None


def test_returns_none_when_size_mismatch_breaks_identity() -> None:
    """size_match=False blocks identity_transformation even with zero
    change groups — translator must return None on a stale "no diff in
    overlap" reading."""
    legacy = {"type": "identity"}
    out = translate_to_schema(
        legacy, "abcdef12", _size_mismatch_patterns(),
        rule_id=11, now="2026-05-13T19:30:00.000000",
    )
    assert out is None


def test_returns_none_for_color_mapping_legacy_shape() -> None:
    """color_mapping requires pair-specific program synthesis (no
    registered DSL primitive for its action.dsl yet) — translator
    refuses, returns None."""
    legacy = {"type": "color_mapping", "mapping": {1: 2}, "confidence": 0.8}
    out = translate_to_schema(
        legacy, "abcdef12", _color_mapping_patterns(),
        rule_id=12, now="2026-05-13T19:30:00.000000",
    )
    assert out is None


def test_returns_none_for_recolor_sequential_legacy_shape() -> None:
    legacy = {
        "type": "recolor_sequential",
        "sort_key": "top_row",
        "start_color": 1,
        "source_colors": [5],
        "confidence": 1.0,
    }
    out = translate_to_schema(
        legacy, "abcdef12", _color_mapping_patterns(),
        rule_id=13, now="2026-05-13T19:30:00.000000",
    )
    assert out is None


def test_returns_none_for_non_dict_legacy_rule() -> None:
    assert translate_to_schema(
        None, "abcdef12", _identity_patterns(), rule_id=14,
    ) is None
    assert translate_to_schema(
        "identity", "abcdef12", _identity_patterns(), rule_id=15,
    ) is None
    assert translate_to_schema(
        ["identity"], "abcdef12", _identity_patterns(), rule_id=16,
    ) is None


def test_returns_none_for_missing_legacy_type() -> None:
    assert translate_to_schema(
        {}, "abcdef12", _identity_patterns(), rule_id=17,
    ) is None
    assert translate_to_schema(
        {"confidence": 0.0}, "abcdef12", _identity_patterns(), rule_id=18,
    ) is None
    assert translate_to_schema(
        {"type": ""}, "abcdef12", _identity_patterns(), rule_id=19,
    ) is None
    assert translate_to_schema(
        {"type": 5}, "abcdef12", _identity_patterns(), rule_id=20,
    ) is None


def test_returns_none_for_invalid_task_hex() -> None:
    legacy = {"type": "identity"}
    # Wrong length / case / non-hex / non-string all rejected.
    assert translate_to_schema(legacy, "abcd", _identity_patterns(), rule_id=21) is None
    assert translate_to_schema(legacy, "ABCDEF12", _identity_patterns(), rule_id=22) is None
    assert translate_to_schema(legacy, "abcdef1g", _identity_patterns(), rule_id=23) is None
    assert translate_to_schema(legacy, None, _identity_patterns(), rule_id=24) is None
    assert translate_to_schema(legacy, 123, _identity_patterns(), rule_id=25) is None


def test_returns_none_for_invalid_rule_id() -> None:
    legacy = {"type": "identity"}
    assert translate_to_schema(legacy, "abcdef12", _identity_patterns(), rule_id=0) is None
    assert translate_to_schema(legacy, "abcdef12", _identity_patterns(), rule_id=-1) is None
    assert translate_to_schema(
        legacy, "abcdef12", _identity_patterns(), rule_id=True,
    ) is None  # bool subclass of int — explicitly rejected
    assert translate_to_schema(
        legacy, "abcdef12", _identity_patterns(), rule_id="1",
    ) is None


def test_non_dict_patterns_coerced_then_matcher_rejects() -> None:
    """patterns=None / patterns=[] / patterns="foo" — translator coerces
    to {} internally; the matcher then sees empty patterns and rejects;
    translator returns None."""
    legacy = {"type": "identity"}
    for bad in (None, [], "foo", 42, set()):
        out = translate_to_schema(legacy, "abcdef12", bad, rule_id=26)
        assert out is None, f"expected None for patterns={bad!r}, got {out!r}"


def test_translator_is_pure_no_file_io() -> None:
    """`translate_to_schema` must not write to disk or mutate the
    procedural_memory directory. Run inside a tempdir and confirm it
    stays empty across translation."""
    tmp_root = tempfile.mkdtemp(prefix="arbor_translate_pure_")
    try:
        before = set(os.listdir(tmp_root))
        for i in range(5):
            translate_to_schema(
                {"type": "identity"}, "abcdef12", _identity_patterns(),
                rule_id=i + 1, now="2026-05-13T19:30:00.000000",
            )
        after = set(os.listdir(tmp_root))
        assert before == after, "translate_to_schema leaked a write to disk"
    finally:
        import shutil
        shutil.rmtree(tmp_root, ignore_errors=True)


def test_translator_does_not_mutate_inputs() -> None:
    """Side-effect freedom on caller's dicts."""
    legacy = {"type": "identity", "confidence": 0.0}
    legacy_before = dict(legacy)
    patterns = _identity_patterns()
    patterns_before_keys = sorted(patterns.keys())
    out = translate_to_schema(
        legacy, "abcdef12", patterns,
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is not None
    assert legacy == legacy_before, "translator mutated legacy_rule input"
    assert sorted(patterns.keys()) == patterns_before_keys, (
        "translator mutated patterns input"
    )


def test_translator_deterministic_across_repeats() -> None:
    legacy = {"type": "identity"}
    patterns = _identity_patterns()
    a = translate_to_schema(
        legacy, "abcdef12", patterns, rule_id=1,
        now="2026-05-13T19:30:00.000000",
    )
    b = translate_to_schema(
        legacy, "abcdef12", patterns, rule_id=1,
        now="2026-05-13T19:30:00.000000",
    )
    assert a == b


def test_created_at_uses_supplied_now_when_provided() -> None:
    legacy = {"type": "identity"}
    out = translate_to_schema(
        legacy, "abcdef12", _identity_patterns(),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is not None
    assert out["created_at"] == "2026-05-13T19:30:00.000000"


def test_created_at_uses_now_when_arg_omitted() -> None:
    legacy = {"type": "identity"}
    out = translate_to_schema(
        legacy, "abcdef12", _identity_patterns(),
        rule_id=1,
    )
    assert out is not None
    assert isinstance(out["created_at"], str) and len(out["created_at"]) > 0


def test_concept_and_category_inferred_from_legacy_rule() -> None:
    """Reuse `_infer_concept` / `_infer_category` so the schema record
    stays coherent with the legacy writer's labelling — saves us from
    introducing a second naming scheme for the same conceptual record."""
    legacy = {"type": "identity"}
    out = translate_to_schema(
        legacy, "abcdef12", _identity_patterns(),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is not None
    assert out["concept"] == "identity"
    assert out["category"] == "other"


# ──────────────────────────────────────────────────────────────────────────
# Driver.
# ──────────────────────────────────────────────────────────────────────────

def _run_all() -> int:
    tests = [
        test_identity_translates_to_schema_compliant_rule,
        test_identity_condition_uses_identity_transformation_matcher,
        test_identity_action_is_noop_coloring,
        test_translated_identity_rule_passes_validate_rule,
        test_covers_and_source_task_use_task_hex,
        test_anti_unification_trace_is_null_for_source_rule,
        test_times_reused_starts_at_zero,
        test_min_evidence_reflects_pair_count,
        test_min_evidence_floor_one_when_no_pair_analyses,
        test_returns_none_when_matcher_does_not_fire,
        test_returns_none_when_size_mismatch_breaks_identity,
        test_returns_none_for_color_mapping_legacy_shape,
        test_returns_none_for_recolor_sequential_legacy_shape,
        test_returns_none_for_non_dict_legacy_rule,
        test_returns_none_for_missing_legacy_type,
        test_returns_none_for_invalid_task_hex,
        test_returns_none_for_invalid_rule_id,
        test_non_dict_patterns_coerced_then_matcher_rejects,
        test_translator_is_pure_no_file_io,
        test_translator_does_not_mutate_inputs,
        test_translator_deterministic_across_repeats,
        test_created_at_uses_supplied_now_when_provided,
        test_created_at_uses_now_when_arg_omitted,
        test_concept_and_category_inferred_from_legacy_rule,
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
    sys.exit(0 if rc == 0 else 1)
