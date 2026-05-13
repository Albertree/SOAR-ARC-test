"""
tests/test_translate_to_schema.py — exercise the legacy→§1 translator
added in iter 14, extended with the make_grid branch in iter 21.

Runs without pytest. Invoke directly:

    python tests/test_translate_to_schema.py

Exits 0 on success, non-zero on first failed assertion (with traceback).

Scope: `agent/memory.py:translate_to_schema(legacy_rule, task_hex, patterns,
*, rule_id, now=None)`. As of iter 21 the translator handles two legacy→§1
shape pairs, both gated on the source `legacy_type == "identity"` (the slow
path's fallback shape when none of its hand-coded matchers fire):

  * identity_transformation fires  → no-op `coloring(selection=[], color=0)`
    rule. The iter-14 happy path.
  * grid_size_changed + output_dimensions_constant + output_color_uniform
    all fire → `make_grid(height=H, width=W, color=K)` rule. The iter-21
    upgrade — the first non-identity rule shape any iter has been able to
    mint without anti-unification or polymorphic args. H, W come from any
    pair's `output_height` / `output_width` (iter-20 pins them constant);
    K from any group's `output_colors[0]` (iter-18 pins it constant).

Every other legacy type / matcher combination returns `None` until a
follow-up iter wires anti-unification or extends the matcher chain.

Tests run against the live `agent.conditions.CONDITION_REGISTRY` and the
live `procedural_memory.DSL.apply.DSL_REGISTRY` — no stubs. This forces
the test to be coherent with the eight-matcher registry as of iter 20
(grid_size_preserved / consistent_color_mapping / sequential_recoloring /
identity_transformation / grid_size_changed / output_color_uniform /
input_color_uniform / output_dimensions_constant) and the two-primitive
DSL frozen by F3.
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
# Iter 21 — make_grid(H, W, K) branch.
#
# Shape: legacy `{"type": "identity"}` + the conjunction of `grid_size_changed`
# + `output_dimensions_constant` + `output_color_uniform` all firing →
# `condition.type = "output_dimensions_constant"`, `action.dsl = "make_grid"`
# with `args = {"height": H, "width": W, "color": K}`. H and W from any pair's
# `output_height` / `output_width`; K from any change group's `output_colors[0]`.
# ──────────────────────────────────────────────────────────────────────────

def _make_grid_patterns(n_pairs: int = 2, out_h: int = 5, out_w: int = 5,
                        out_color: int = 7,
                        in_h: int = 3, in_w: int = 3) -> dict:
    """Patterns mimicking a make_grid task. Input is `in_h × in_w` of mixed
    colours; output is `out_h × out_w` of a single colour `out_color`. The
    diff over the overlap region produces at least one change group whose
    `output_colors` is `[out_color]`. `size_match` is False (the iter-17
    matcher's gate). `output_height` / `output_width` are the iter-20 keys.
    """
    pair_analyses = []
    for i in range(n_pairs):
        # One change group in overlap, painting input != out_color cells to out_color.
        # Use a single group with `output_colors=[out_color]` to satisfy the
        # iter-18 uniformity contract.
        pair_analyses.append({
            "total_changes": 1,
            "num_groups": 1,
            "groups": [
                {
                    "input_colors": [i],  # vary across pairs — uniformity is on output side
                    "output_colors": [out_color],
                    "top_row": 0,
                    "top_col": 0,
                    "cell_count": 1,
                }
            ],
            "size_match": False,
            "input_height": in_h,
            "input_width": in_w,
            "output_height": out_h,
            "output_width": out_w,
        })
    return {
        "grid_size_preserved": False,
        "pair_analyses": pair_analyses,
    }


def test_make_grid_branch_fires_when_all_three_matchers_fire() -> None:
    """The smoke test: a `legacy={"type": "identity"}` rule + a patterns
    dict that fires grid_size_changed + output_dimensions_constant +
    output_color_uniform should produce a schema rule whose
    `action.dsl == "make_grid"`. Confirms the iter-21 wiring."""
    legacy = {"type": "identity", "confidence": 0.0}
    out = translate_to_schema(
        legacy, "abcdef12",
        _make_grid_patterns(n_pairs=2, out_h=5, out_w=5, out_color=7),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is not None, "expected make_grid schema rule, got None"
    assert out["action"]["dsl"] == "make_grid"
    assert out["action"]["args"] == {"height": 5, "width": 5, "color": 7}


def test_make_grid_condition_type_is_output_dimensions_constant() -> None:
    """The make_grid branch picks the strictest of the three gating
    matchers (`output_dimensions_constant`) as `condition.type` because
    that matcher directly pins (H, W) in `action.args`. Documented in
    `translate_to_schema`'s iter-21 docstring section."""
    legacy = {"type": "identity"}
    out = translate_to_schema(
        legacy, "abcdef12", _make_grid_patterns(),
        rule_id=2, now="2026-05-13T19:30:00.000000",
    )
    assert out is not None
    assert out["condition"]["type"] == "output_dimensions_constant"
    assert out["condition"]["params"] == {}
    assert isinstance(out["condition"]["min_evidence"], int)
    assert out["condition"]["min_evidence"] >= 1


def test_make_grid_rule_passes_validate_rule() -> None:
    """The translator's output must satisfy V1–V7. V2 checks
    `condition.type` is registered (output_dimensions_constant is, iter
    20); V3 checks `action.dsl` is registered (make_grid is, iter 3)."""
    tmp_root = tempfile.mkdtemp(prefix="arbor_translate_makegrid_")
    try:
        legacy = {"type": "identity"}
        out = translate_to_schema(
            legacy, "abcdef12", _make_grid_patterns(),
            rule_id=1, now="2026-05-13T19:30:00.000000",
        )
        assert out is not None
        validate_rule(out, procedural_memory_root=tmp_root)
    finally:
        import shutil
        shutil.rmtree(tmp_root, ignore_errors=True)


def test_make_grid_dimensions_match_pair_analysis() -> None:
    """H and W are extracted from any pair's output_height / output_width.
    The iter-20 matcher guarantees they are constant across pairs, so any
    pair's values work; verify the extracted (H, W) equal those values."""
    legacy = {"type": "identity"}
    out = translate_to_schema(
        legacy, "abcdef12",
        _make_grid_patterns(n_pairs=3, out_h=7, out_w=4, out_color=2),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is not None
    assert out["action"]["args"]["height"] == 7
    assert out["action"]["args"]["width"] == 4
    assert out["action"]["args"]["color"] == 2


def test_make_grid_color_matches_uniform_output_color() -> None:
    """K is extracted from any change group's `output_colors[0]`. The
    iter-18 matcher guarantees uniformity across all groups in all
    pairs, so any pick equals K."""
    legacy = {"type": "identity"}
    for k in (0, 1, 5, 9):
        out = translate_to_schema(
            legacy, "abcdef12",
            _make_grid_patterns(out_color=k),
            rule_id=1, now="2026-05-13T19:30:00.000000",
        )
        assert out is not None, f"make_grid branch should fire for K={k}"
        assert out["action"]["args"]["color"] == k


def test_make_grid_covers_and_source_task_use_task_hex() -> None:
    legacy = {"type": "identity"}
    out = translate_to_schema(
        legacy, "deadbeef", _make_grid_patterns(),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is not None
    assert out["source_task"] == "deadbeef"
    assert out["covers"] == ["deadbeef"]


def test_make_grid_anti_unification_trace_is_null_for_source_rule() -> None:
    legacy = {"type": "identity"}
    out = translate_to_schema(
        legacy, "abcdef12", _make_grid_patterns(),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is not None
    assert out["anti_unification_trace"] is None


def test_make_grid_times_reused_starts_at_zero() -> None:
    legacy = {"type": "identity"}
    out = translate_to_schema(
        legacy, "abcdef12", _make_grid_patterns(),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is not None
    assert out["times_reused"] == 0


def test_make_grid_min_evidence_reflects_pair_count() -> None:
    legacy = {"type": "identity"}
    out2 = translate_to_schema(
        legacy, "abcdef12", _make_grid_patterns(n_pairs=2),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out2 is not None
    assert out2["condition"]["min_evidence"] == 2

    out4 = translate_to_schema(
        legacy, "abcdef12", _make_grid_patterns(n_pairs=4),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out4 is not None
    assert out4["condition"]["min_evidence"] == 4


def test_make_grid_concept_and_category_are_constant_make_grid_labels() -> None:
    """The make_grid branch coins its own concept/category labels rather
    than going through `_infer_concept` (which would label it "identity"
    since the legacy_type is the fallback). The chosen labels are
    `make_constant_grid` / `geometric_transform` — the latter matches
    `_infer_category`'s existing bucket for geometric shape rules."""
    legacy = {"type": "identity"}
    out = translate_to_schema(
        legacy, "abcdef12", _make_grid_patterns(),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is not None
    assert out["concept"] == "make_constant_grid"
    assert out["category"] == "geometric_transform"


def test_make_grid_branch_returns_none_when_color_uniform_fails() -> None:
    """Two distinct output colours across pairs — output_color_uniform
    does NOT fire, so the make_grid branch is not entered, translator
    returns None."""
    legacy = {"type": "identity"}
    patterns = _make_grid_patterns(n_pairs=2, out_color=3)
    # Mutate the second pair's group to a different output colour.
    patterns["pair_analyses"][1]["groups"][0]["output_colors"] = [4]
    out = translate_to_schema(
        legacy, "abcdef12", patterns,
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is None


def test_make_grid_branch_returns_none_when_dimensions_vary() -> None:
    """Output dimensions vary across pairs — output_dimensions_constant
    does NOT fire, so the make_grid branch is not entered."""
    legacy = {"type": "identity"}
    patterns = _make_grid_patterns(n_pairs=2)
    patterns["pair_analyses"][1]["output_height"] = 6  # was 5
    out = translate_to_schema(
        legacy, "abcdef12", patterns,
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is None


def test_make_grid_branch_returns_none_when_size_preserved_everywhere() -> None:
    """size_match=True everywhere — grid_size_changed does NOT fire (it
    requires at least one False), so the make_grid branch is not entered.
    Note: with size_match=True AND zero change groups would trigger the
    identity branch; we use non-empty groups here to make the only
    blocker grid_size_changed."""
    legacy = {"type": "identity"}
    patterns = _make_grid_patterns(n_pairs=2)
    for pa in patterns["pair_analyses"]:
        pa["size_match"] = True
    out = translate_to_schema(
        legacy, "abcdef12", patterns,
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    # With size_match=True everywhere + uniform output colour + constant dims,
    # this still does not match any defined branch — return None.
    assert out is None


def test_make_grid_branch_returns_none_when_zero_groups() -> None:
    """If every pair has zero change groups, identity_transformation may
    fire (if size_match=True) OR neither identity nor make_grid fires (if
    size_match=False — output_color_uniform requires non-empty groups).
    Verify the zero-group + size_match=False case returns None: the
    overlap is identical but dims differ, which is upstream ambiguity, not
    a translatable rule."""
    legacy = {"type": "identity"}
    patterns = _make_grid_patterns()
    for pa in patterns["pair_analyses"]:
        pa["groups"] = []
        pa["num_groups"] = 0
        pa["total_changes"] = 0
    out = translate_to_schema(
        legacy, "abcdef12", patterns,
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is None


def test_make_grid_branch_returns_none_when_legacy_type_is_not_identity() -> None:
    """The make_grid branch is gated on `legacy_type == "identity"`
    (the slow path's fallback shape). A legacy color_mapping rule even
    paired with make_grid-shape patterns must return None — the slow
    path produced a different rule shape and the translator does not
    overwrite it."""
    legacy = {"type": "color_mapping", "mapping": {1: 7}, "confidence": 0.9}
    out = translate_to_schema(
        legacy, "abcdef12", _make_grid_patterns(),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is None


def test_make_grid_branch_pure_no_file_io() -> None:
    """Same purity contract as the identity branch: no disk writes."""
    tmp_root = tempfile.mkdtemp(prefix="arbor_translate_makegrid_pure_")
    try:
        before = set(os.listdir(tmp_root))
        for i in range(5):
            translate_to_schema(
                {"type": "identity"}, "abcdef12", _make_grid_patterns(),
                rule_id=i + 1, now="2026-05-13T19:30:00.000000",
            )
        after = set(os.listdir(tmp_root))
        assert before == after, "make_grid branch leaked a write to disk"
    finally:
        import shutil
        shutil.rmtree(tmp_root, ignore_errors=True)


def test_make_grid_branch_does_not_mutate_inputs() -> None:
    legacy = {"type": "identity"}
    legacy_before = dict(legacy)
    patterns = _make_grid_patterns()
    patterns_pa_count_before = len(patterns["pair_analyses"])
    patterns_first_keys_before = sorted(patterns["pair_analyses"][0].keys())
    out = translate_to_schema(
        legacy, "abcdef12", patterns,
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is not None
    assert legacy == legacy_before, "translator mutated legacy_rule"
    assert len(patterns["pair_analyses"]) == patterns_pa_count_before
    assert sorted(patterns["pair_analyses"][0].keys()) == patterns_first_keys_before


def test_make_grid_branch_deterministic_across_repeats() -> None:
    legacy = {"type": "identity"}
    patterns = _make_grid_patterns()
    a = translate_to_schema(
        legacy, "abcdef12", patterns, rule_id=1,
        now="2026-05-13T19:30:00.000000",
    )
    b = translate_to_schema(
        legacy, "abcdef12", patterns, rule_id=1,
        now="2026-05-13T19:30:00.000000",
    )
    assert a == b


def test_make_grid_rule_round_trip_through_apply_DSL() -> None:
    """End-to-end: a translated make_grid rule, when applied via the
    iter-3 DSL primitive, produces exactly the H×W canvas of K the
    patterns dict described. This is what the fast-path
    `_predict_with_entry` does at runtime — if this test passes, the
    iter-21 wiring is end-to-end coherent."""
    from procedural_memory.DSL.apply import apply_DSL  # local import
    legacy = {"type": "identity"}
    out = translate_to_schema(
        legacy, "abcdef12",
        _make_grid_patterns(n_pairs=2, out_h=4, out_w=3, out_color=8),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is not None
    args = out["action"]["args"]
    grid = apply_DSL("make_grid", **args)
    assert grid == [[8, 8, 8], [8, 8, 8], [8, 8, 8], [8, 8, 8]]


# ──────────────────────────────────────────────────────────────────────────
# Iter 25 — single-cell uniform-paint branch.
#
# Shape: legacy `{"type": "identity"}` + the conjunction of
# `single_cell_change_per_pair` + `output_color_uniform` +
# `input_dimensions_constant` + `grid_size_preserved` all firing →
# `condition.type = "single_cell_change_per_pair"`, `action.dsl = "coloring"`
# with `args = {"selection": [[r, c]], "color": K}`. (r, c) is each pair's
# single-cell group's `(top_row, top_col)`; the defensive helper requires
# the coord to be bit-identical across pairs (the matcher conjunction pins
# cardinality but not position). K from any group's `output_colors[0]`
# (iter-18 pins it constant).
# ──────────────────────────────────────────────────────────────────────────

def _single_cell_patterns(n_pairs: int = 2, r: int = 1, c: int = 2,
                          k: int = 7, in_h: int = 3, in_w: int = 3) -> dict:
    """Patterns mimicking a single-cell uniform-paint task. Every pair has
    one change group consisting of one changed cell at (r, c) → colour k.
    `size_match` is True per pair (input dims == output dims); per-pair
    `input_height`/`input_width`/`output_height`/`output_width` set to
    (in_h, in_w) so iter-22 input_dimensions_constant fires. The
    iter-1 top-level `grid_size_preserved` flag is True."""
    pair_analyses = []
    for i in range(n_pairs):
        # Vary input_colors across pairs — output_color_uniform is on output side.
        pair_analyses.append({
            "total_changes": 1,
            "num_groups": 1,
            "groups": [
                {
                    "input_colors": [i],
                    "output_colors": [k],
                    "top_row": r,
                    "top_col": c,
                    "cell_count": 1,
                }
            ],
            "size_match": True,
            "input_height": in_h,
            "input_width": in_w,
            "output_height": in_h,
            "output_width": in_w,
        })
    return {
        "grid_size_preserved": True,
        "pair_analyses": pair_analyses,
    }


def test_single_cell_branch_fires_when_all_four_matchers_fire() -> None:
    """Smoke: legacy={"type": "identity"} + patterns firing iter
    1 / 18 / 22 / 24 should produce a schema rule whose
    `action.dsl == "coloring"` with a single-coord selection."""
    legacy = {"type": "identity", "confidence": 0.0}
    out = translate_to_schema(
        legacy, "abcdef12",
        _single_cell_patterns(n_pairs=2, r=1, c=2, k=7),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is not None, "expected single-cell schema rule, got None"
    assert out["action"]["dsl"] == "coloring"
    assert out["action"]["args"] == {"selection": [[1, 2]], "color": 7}


def test_single_cell_condition_type_is_single_cell_change_per_pair() -> None:
    """The single-cell branch picks `single_cell_change_per_pair` as
    `condition.type` — the strictest of the four gating matchers (and
    the one that directly pins the action's selection cardinality)."""
    legacy = {"type": "identity"}
    out = translate_to_schema(
        legacy, "abcdef12", _single_cell_patterns(),
        rule_id=2, now="2026-05-13T19:30:00.000000",
    )
    assert out is not None
    assert out["condition"]["type"] == "single_cell_change_per_pair"
    assert out["condition"]["params"] == {}
    assert isinstance(out["condition"]["min_evidence"], int)
    assert out["condition"]["min_evidence"] >= 1


def test_single_cell_rule_passes_validate_rule() -> None:
    """The translator's output must satisfy V1–V7. V2 checks
    `condition.type` is registered (single_cell_change_per_pair is, iter
    24); V3 checks `action.dsl` is registered (coloring is, iter 3)."""
    tmp_root = tempfile.mkdtemp(prefix="arbor_translate_singlecell_")
    try:
        legacy = {"type": "identity"}
        out = translate_to_schema(
            legacy, "abcdef12", _single_cell_patterns(),
            rule_id=1, now="2026-05-13T19:30:00.000000",
        )
        assert out is not None
        validate_rule(out, procedural_memory_root=tmp_root)
    finally:
        import shutil
        shutil.rmtree(tmp_root, ignore_errors=True)


def test_single_cell_coord_matches_pair_analysis() -> None:
    """The (r, c) coord is extracted from any pair's group's
    (top_row, top_col). The defensive helper additionally requires the
    coord to be bit-identical across pairs; iter the values to verify
    the extraction is correct, not stuck on a constant."""
    legacy = {"type": "identity"}
    for r_val, c_val in ((0, 0), (2, 1), (4, 4)):
        out = translate_to_schema(
            legacy, "abcdef12",
            _single_cell_patterns(n_pairs=3, r=r_val, c=c_val, k=5,
                                  in_h=5, in_w=5),
            rule_id=1, now="2026-05-13T19:30:00.000000",
        )
        assert out is not None, f"single-cell branch should fire for ({r_val},{c_val})"
        assert out["action"]["args"]["selection"] == [[r_val, c_val]]


def test_single_cell_color_matches_uniform_output_color() -> None:
    """K is extracted from any group's `output_colors[0]`. iter-18
    pins uniformity; the helper additionally checks the value is in the
    coloring primitive's valid colour set (0..9 or 13)."""
    legacy = {"type": "identity"}
    for k in (0, 1, 5, 9, 13):
        out = translate_to_schema(
            legacy, "abcdef12",
            _single_cell_patterns(k=k),
            rule_id=1, now="2026-05-13T19:30:00.000000",
        )
        assert out is not None, f"single-cell branch should fire for K={k}"
        assert out["action"]["args"]["color"] == k


def test_single_cell_covers_and_source_task_use_task_hex() -> None:
    legacy = {"type": "identity"}
    out = translate_to_schema(
        legacy, "deadbeef", _single_cell_patterns(),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is not None
    assert out["source_task"] == "deadbeef"
    assert out["covers"] == ["deadbeef"]


def test_single_cell_anti_unification_trace_is_null_for_source_rule() -> None:
    legacy = {"type": "identity"}
    out = translate_to_schema(
        legacy, "abcdef12", _single_cell_patterns(),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is not None
    assert out["anti_unification_trace"] is None


def test_single_cell_times_reused_starts_at_zero() -> None:
    legacy = {"type": "identity"}
    out = translate_to_schema(
        legacy, "abcdef12", _single_cell_patterns(),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is not None
    assert out["times_reused"] == 0


def test_single_cell_min_evidence_reflects_pair_count() -> None:
    legacy = {"type": "identity"}
    out2 = translate_to_schema(
        legacy, "abcdef12", _single_cell_patterns(n_pairs=2),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out2 is not None
    assert out2["condition"]["min_evidence"] == 2

    out5 = translate_to_schema(
        legacy, "abcdef12", _single_cell_patterns(n_pairs=5),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out5 is not None
    assert out5["condition"]["min_evidence"] == 5


def test_single_cell_concept_and_category_are_paint_single_cell_labels() -> None:
    """The single-cell branch coins its own concept/category labels
    rather than going through `_infer_concept` (which would label it
    `identity` since the legacy_type is the fallback). The labels are
    `paint_single_cell` / `color_transform` — the latter matches
    `_infer_category`'s colour bucket pattern."""
    legacy = {"type": "identity"}
    out = translate_to_schema(
        legacy, "abcdef12", _single_cell_patterns(),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is not None
    assert out["concept"] == "paint_single_cell"
    assert out["category"] == "color_transform"


def test_single_cell_branch_returns_none_when_color_uniform_fails() -> None:
    """Two distinct output colours across pairs — output_color_uniform
    does NOT fire, so the single-cell branch is not entered."""
    legacy = {"type": "identity"}
    patterns = _single_cell_patterns(n_pairs=2, k=3)
    patterns["pair_analyses"][1]["groups"][0]["output_colors"] = [4]
    out = translate_to_schema(
        legacy, "abcdef12", patterns,
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is None


def test_single_cell_branch_returns_none_when_input_dims_vary() -> None:
    """Input dimensions vary across pairs — input_dimensions_constant
    does NOT fire, so the single-cell branch is not entered (the
    stored literal coord would not generalise to a heterogeneous-input
    test task)."""
    legacy = {"type": "identity"}
    patterns = _single_cell_patterns(n_pairs=2, in_h=3, in_w=3)
    patterns["pair_analyses"][1]["input_height"] = 4  # was 3
    patterns["pair_analyses"][1]["input_width"] = 4
    patterns["pair_analyses"][1]["output_height"] = 4
    patterns["pair_analyses"][1]["output_width"] = 4
    out = translate_to_schema(
        legacy, "abcdef12", patterns,
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is None


def test_single_cell_branch_returns_none_when_size_changed() -> None:
    """At least one pair has size_match=False — grid_size_preserved
    does NOT fire (its top-level flag would be False), so the
    single-cell branch is not entered. Note this case ALSO blocks
    iter-21's make_grid branch since cell_count == 1 fires
    single_cell_change_per_pair, but make_grid additionally requires
    output_dimensions_constant which is not guaranteed when size
    varies."""
    legacy = {"type": "identity"}
    patterns = _single_cell_patterns(n_pairs=2)
    patterns["pair_analyses"][1]["size_match"] = False
    patterns["pair_analyses"][1]["output_height"] = 4  # break shape
    patterns["grid_size_preserved"] = False
    out = translate_to_schema(
        legacy, "abcdef12", patterns,
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is None


def test_single_cell_branch_returns_none_when_multi_cell_group() -> None:
    """The group has more than one cell — single_cell_change_per_pair
    does NOT fire (it requires cell_count == 1). single_change_group_per_pair
    might fire but is not part of the iter-25 gate; the single-cell
    branch returns None."""
    legacy = {"type": "identity"}
    patterns = _single_cell_patterns(n_pairs=2)
    patterns["pair_analyses"][0]["groups"][0]["cell_count"] = 2
    out = translate_to_schema(
        legacy, "abcdef12", patterns,
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is None


def test_single_cell_branch_returns_none_when_multiple_groups() -> None:
    """A pair has more than one group — single_cell_change_per_pair
    does NOT fire (it requires num_groups == 1). The single-cell
    branch returns None even if every group is itself a single cell."""
    legacy = {"type": "identity"}
    patterns = _single_cell_patterns(n_pairs=2)
    patterns["pair_analyses"][0]["num_groups"] = 2
    patterns["pair_analyses"][0]["groups"].append({
        "input_colors": [5],
        "output_colors": [7],
        "top_row": 2,
        "top_col": 2,
        "cell_count": 1,
    })
    out = translate_to_schema(
        legacy, "abcdef12", patterns,
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is None


def test_single_cell_branch_returns_none_when_coord_differs_across_pairs() -> None:
    """The defensive `_extract_single_cell_paint_args` helper enforces
    coord stability across pairs even though the matcher conjunction
    does not. Pair 0 changes (0, 0); pair 1 changes (2, 1). Every
    matcher in the gate still fires (cardinality, colour, input dims,
    size_match), but the helper returns None because the stored
    literal coord would not generalise."""
    legacy = {"type": "identity"}
    patterns = _single_cell_patterns(n_pairs=2, r=0, c=0)
    patterns["pair_analyses"][1]["groups"][0]["top_row"] = 2
    patterns["pair_analyses"][1]["groups"][0]["top_col"] = 1
    out = translate_to_schema(
        legacy, "abcdef12", patterns,
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is None


def test_single_cell_branch_returns_none_when_legacy_type_is_not_identity() -> None:
    """The single-cell branch is gated on `legacy_type == "identity"`
    (the slow path's fallback shape). A color_mapping legacy rule even
    paired with single-cell-shape patterns must return None."""
    legacy = {"type": "color_mapping", "mapping": {1: 7}, "confidence": 0.9}
    out = translate_to_schema(
        legacy, "abcdef12", _single_cell_patterns(),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is None


def test_single_cell_branch_returns_none_when_color_out_of_palette() -> None:
    """The helper additionally rejects an output colour outside
    `range(10) | {13}` (the coloring primitive's valid set), even when
    output_color_uniform fires (it only checks uniformity, not domain).
    Foreclosing here prevents a malformed rule that validate_rule would
    happily save but coloring would later reject."""
    legacy = {"type": "identity"}
    patterns = _single_cell_patterns(n_pairs=2, k=11)
    out = translate_to_schema(
        legacy, "abcdef12", patterns,
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is None


def test_single_cell_branch_pure_no_file_io() -> None:
    """Same purity contract as the identity / make_grid branches."""
    tmp_root = tempfile.mkdtemp(prefix="arbor_translate_singlecell_pure_")
    try:
        before = set(os.listdir(tmp_root))
        for i in range(5):
            translate_to_schema(
                {"type": "identity"}, "abcdef12", _single_cell_patterns(),
                rule_id=i + 1, now="2026-05-13T19:30:00.000000",
            )
        after = set(os.listdir(tmp_root))
        assert before == after, "single-cell branch leaked a write to disk"
    finally:
        import shutil
        shutil.rmtree(tmp_root, ignore_errors=True)


def test_single_cell_branch_does_not_mutate_inputs() -> None:
    legacy = {"type": "identity"}
    legacy_before = dict(legacy)
    patterns = _single_cell_patterns()
    patterns_pa_count_before = len(patterns["pair_analyses"])
    patterns_first_keys_before = sorted(patterns["pair_analyses"][0].keys())
    out = translate_to_schema(
        legacy, "abcdef12", patterns,
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is not None
    assert legacy == legacy_before, "translator mutated legacy_rule"
    assert len(patterns["pair_analyses"]) == patterns_pa_count_before
    assert sorted(patterns["pair_analyses"][0].keys()) == patterns_first_keys_before


def test_single_cell_branch_deterministic_across_repeats() -> None:
    legacy = {"type": "identity"}
    patterns = _single_cell_patterns()
    a = translate_to_schema(
        legacy, "abcdef12", patterns, rule_id=1,
        now="2026-05-13T19:30:00.000000",
    )
    b = translate_to_schema(
        legacy, "abcdef12", patterns, rule_id=1,
        now="2026-05-13T19:30:00.000000",
    )
    assert a == b


def test_single_cell_rule_round_trip_through_apply_DSL() -> None:
    """End-to-end: a translated single-cell coloring rule, when applied
    via the iter-3 DSL primitive, paints exactly the (r, c) cell with
    colour K on a test input. This is the path `_predict_with_entry`
    runs at runtime — if this test passes the iter-25 wiring is
    end-to-end coherent."""
    from procedural_memory.DSL.apply import apply_DSL  # local import
    legacy = {"type": "identity"}
    out = translate_to_schema(
        legacy, "abcdef12",
        _single_cell_patterns(n_pairs=2, r=1, c=2, k=8, in_h=3, in_w=3),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is not None
    args = out["action"]["args"]
    test_input = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
    painted = apply_DSL("coloring", test_input, **args)
    assert painted == [[0, 0, 0], [0, 0, 8], [0, 0, 0]]
    # Source grid not mutated (purity).
    assert test_input == [[0, 0, 0], [0, 0, 0], [0, 0, 0]]


def test_single_cell_branch_strict_mutual_exclusion_with_identity() -> None:
    """The iter-25 branch and the iter-14 identity branch are reachable
    only on disjoint patterns dicts: single_cell_change_per_pair
    requires num_groups == 1 per pair, identity_transformation requires
    num_groups == 0. Verify both endpoints: identity patterns produce
    an identity-shape rule (action `coloring(selection=[], color=0)`);
    single-cell patterns produce a single-coord rule. Neither shape can
    accidentally produce the other's output."""
    legacy = {"type": "identity"}
    # Identity patterns → identity-shape rule.
    out_id = translate_to_schema(
        legacy, "abcdef12", _identity_patterns(n_pairs=2),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out_id is not None
    assert out_id["condition"]["type"] == "identity_transformation"
    assert out_id["action"]["args"]["selection"] == []
    # Single-cell patterns → single-coord rule.
    out_sc = translate_to_schema(
        legacy, "abcdef12", _single_cell_patterns(n_pairs=2, r=1, c=2, k=7),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out_sc is not None
    assert out_sc["condition"]["type"] == "single_cell_change_per_pair"
    assert out_sc["action"]["args"]["selection"] == [[1, 2]]


def test_single_cell_branch_strict_mutual_exclusion_with_make_grid() -> None:
    """The iter-25 branch and the iter-21 make_grid branch are reachable
    only on disjoint patterns dicts: grid_size_preserved (this iter)
    requires every per-pair size_match True AND top-level
    `grid_size_preserved` True; grid_size_changed (iter 21) requires at
    least one per-pair size_match False. They are exact partitioners of
    the dimensional axis. Verify both endpoints: a make_grid patterns
    dict produces a make_grid rule; a single-cell patterns dict produces
    a coloring rule; never the other way."""
    legacy = {"type": "identity"}
    # make_grid patterns → make_grid-shape rule.
    out_mg = translate_to_schema(
        legacy, "abcdef12", _make_grid_patterns(out_color=7),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out_mg is not None
    assert out_mg["action"]["dsl"] == "make_grid"
    # Single-cell patterns → coloring-shape rule.
    out_sc = translate_to_schema(
        legacy, "abcdef12", _single_cell_patterns(),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out_sc is not None
    assert out_sc["action"]["dsl"] == "coloring"


# ──────────────────────────────────────────────────────────────────────────
# Iter 27 — multi-cell single-blob coloring branch
#   legacy {"type": "identity"} + patterns firing
#   multi_cell_change_group_per_pair (iter 26) + output_color_uniform
#   (iter 18) + input_dimensions_constant (iter 22) + grid_size_preserved
#   (iter 1) → `coloring(grid, [(r1,c1), ..., (rN,cN)], K)` rule. The
#   coord list is each pair's single group's `positions` field (iter 27's
#   `_analyze_pair` extension), serialized in row-major sorted order. The
#   defensive helper requires the position SET to be bit-identical across
#   pairs (the matcher conjunction pins cardinality range and colour
#   uniformity but not blob position). K from any group's
#   `output_colors[0]`.
# ──────────────────────────────────────────────────────────────────────────

def _multi_cell_patterns(n_pairs: int = 2,
                         positions: list | None = None,
                         k: int = 7, in_h: int = 4, in_w: int = 4) -> dict:
    """Patterns mimicking a multi-cell single-blob uniform-paint task.
    Every pair has one change group consisting of `len(positions)` ≥ 2
    cells at the given coords → colour k. `size_match` is True per pair;
    per-pair `input_height`/`input_width`/`output_height`/`output_width`
    set to (in_h, in_w) so iter-22 input_dimensions_constant fires. The
    iter-1 top-level `grid_size_preserved` flag is True.
    """
    if positions is None:
        positions = [(1, 1), (1, 2)]
    cells = [(int(r), int(c)) for r, c in positions]
    top_row = min(r for r, _ in cells)
    top_col = min(c for _, c in cells)
    sorted_positions = sorted(cells)
    pair_analyses = []
    for i in range(n_pairs):
        pair_analyses.append({
            "total_changes": len(cells),
            "num_groups": 1,
            "groups": [
                {
                    "input_colors": [i],
                    "output_colors": [k],
                    "top_row": top_row,
                    "top_col": top_col,
                    "cell_count": len(cells),
                    "positions": [tuple(p) for p in sorted_positions],
                }
            ],
            "size_match": True,
            "input_height": in_h,
            "input_width": in_w,
            "output_height": in_h,
            "output_width": in_w,
        })
    return {
        "grid_size_preserved": True,
        "pair_analyses": pair_analyses,
    }


def test_multi_cell_branch_fires_when_all_four_matchers_fire() -> None:
    """Smoke: legacy={"type": "identity"} + patterns firing iter
    1 / 18 / 22 / 26 should produce a schema rule whose
    `action.dsl == "coloring"` with a multi-coord selection."""
    legacy = {"type": "identity", "confidence": 0.0}
    out = translate_to_schema(
        legacy, "abcdef12",
        _multi_cell_patterns(n_pairs=2, positions=[(1, 1), (1, 2)], k=7),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is not None, "expected multi-cell schema rule, got None"
    assert out["action"]["dsl"] == "coloring"
    assert out["action"]["args"] == {
        "selection": [[1, 1], [1, 2]], "color": 7,
    }


def test_multi_cell_condition_type_is_multi_cell_change_group_per_pair() -> None:
    """The multi-cell branch picks `multi_cell_change_group_per_pair` as
    `condition.type` — the strictest of the four gating matchers."""
    legacy = {"type": "identity"}
    out = translate_to_schema(
        legacy, "abcdef12", _multi_cell_patterns(),
        rule_id=2, now="2026-05-13T19:30:00.000000",
    )
    assert out is not None
    assert out["condition"]["type"] == "multi_cell_change_group_per_pair"
    assert out["condition"]["params"] == {}
    assert isinstance(out["condition"]["min_evidence"], int)
    assert out["condition"]["min_evidence"] >= 1


def test_multi_cell_rule_passes_validate_rule() -> None:
    """The translator's output must satisfy V1–V7. V2 checks
    `condition.type` is registered (multi_cell_change_group_per_pair is,
    iter 26); V3 checks `action.dsl` is registered (coloring is, iter
    3)."""
    tmp_root = tempfile.mkdtemp(prefix="arbor_translate_multicell_")
    try:
        legacy = {"type": "identity"}
        out = translate_to_schema(
            legacy, "abcdef12", _multi_cell_patterns(),
            rule_id=1, now="2026-05-13T19:30:00.000000",
        )
        assert out is not None
        validate_rule(out, procedural_memory_root=tmp_root)
    finally:
        import shutil
        shutil.rmtree(tmp_root, ignore_errors=True)


def test_multi_cell_positions_match_pair_analysis() -> None:
    """The selection list is extracted from each pair's group's
    `positions`. The defensive helper additionally requires the set to be
    bit-identical across pairs; iter through several positions to verify
    the extraction is correct, not stuck on a constant."""
    legacy = {"type": "identity"}
    cases = [
        [(0, 0), (0, 1)],
        [(0, 0), (1, 0), (2, 0)],
        [(1, 1), (1, 2), (2, 1), (2, 2)],
    ]
    for blob in cases:
        out = translate_to_schema(
            legacy, "abcdef12",
            _multi_cell_patterns(n_pairs=3, positions=blob, k=5,
                                 in_h=5, in_w=5),
            rule_id=1, now="2026-05-13T19:30:00.000000",
        )
        assert out is not None, f"multi-cell branch should fire for {blob}"
        expected = [[r, c] for (r, c) in sorted(blob)]
        assert out["action"]["args"]["selection"] == expected


def test_multi_cell_positions_are_row_major_sorted() -> None:
    """The translator must produce a deterministic row-major sorted
    selection list regardless of the order positions appear in the
    fixture, because anti-unification (and stored-rule lookup) requires
    deterministic serialization."""
    legacy = {"type": "identity"}
    # Same blob, different input orderings — translator must produce
    # identical output.
    patterns_a = _multi_cell_patterns(positions=[(0, 0), (0, 1), (1, 0)])
    patterns_b = _multi_cell_patterns(positions=[(1, 0), (0, 1), (0, 0)])
    out_a = translate_to_schema(
        legacy, "abcdef12", patterns_a, rule_id=1,
        now="2026-05-13T19:30:00.000000",
    )
    out_b = translate_to_schema(
        legacy, "abcdef12", patterns_b, rule_id=1,
        now="2026-05-13T19:30:00.000000",
    )
    assert out_a is not None and out_b is not None
    assert out_a["action"]["args"]["selection"] == \
        out_b["action"]["args"]["selection"] == [[0, 0], [0, 1], [1, 0]]


def test_multi_cell_color_matches_uniform_output_color() -> None:
    """K is extracted from any group's `output_colors[0]`. iter-18 pins
    uniformity; the helper additionally checks the value is in the
    coloring primitive's valid colour set (0..9 or 13)."""
    legacy = {"type": "identity"}
    for k in (0, 1, 5, 9, 13):
        out = translate_to_schema(
            legacy, "abcdef12",
            _multi_cell_patterns(k=k),
            rule_id=1, now="2026-05-13T19:30:00.000000",
        )
        assert out is not None, f"multi-cell branch should fire for K={k}"
        assert out["action"]["args"]["color"] == k


def test_multi_cell_covers_and_source_task_use_task_hex() -> None:
    legacy = {"type": "identity"}
    out = translate_to_schema(
        legacy, "deadbeef", _multi_cell_patterns(),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is not None
    assert out["source_task"] == "deadbeef"
    assert out["covers"] == ["deadbeef"]


def test_multi_cell_anti_unification_trace_is_null_for_source_rule() -> None:
    legacy = {"type": "identity"}
    out = translate_to_schema(
        legacy, "abcdef12", _multi_cell_patterns(),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is not None
    assert out["anti_unification_trace"] is None


def test_multi_cell_times_reused_starts_at_zero() -> None:
    legacy = {"type": "identity"}
    out = translate_to_schema(
        legacy, "abcdef12", _multi_cell_patterns(),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is not None
    assert out["times_reused"] == 0


def test_multi_cell_min_evidence_reflects_pair_count() -> None:
    legacy = {"type": "identity"}
    out2 = translate_to_schema(
        legacy, "abcdef12", _multi_cell_patterns(n_pairs=2),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out2 is not None
    assert out2["condition"]["min_evidence"] == 2

    out4 = translate_to_schema(
        legacy, "abcdef12", _multi_cell_patterns(n_pairs=4),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out4 is not None
    assert out4["condition"]["min_evidence"] == 4


def test_multi_cell_concept_and_category_are_paint_blob_labels() -> None:
    """The multi-cell branch coins its own concept/category labels rather
    than going through `_infer_concept`. The labels are `paint_blob` /
    `color_transform`."""
    legacy = {"type": "identity"}
    out = translate_to_schema(
        legacy, "abcdef12", _multi_cell_patterns(),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is not None
    assert out["concept"] == "paint_blob"
    assert out["category"] == "color_transform"


def test_multi_cell_branch_returns_none_when_color_uniform_fails() -> None:
    """Two distinct output colours across pairs — output_color_uniform
    does NOT fire."""
    legacy = {"type": "identity"}
    patterns = _multi_cell_patterns(n_pairs=2, k=3)
    patterns["pair_analyses"][1]["groups"][0]["output_colors"] = [4]
    out = translate_to_schema(
        legacy, "abcdef12", patterns,
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is None


def test_multi_cell_branch_returns_none_when_input_dims_vary() -> None:
    """Input dimensions vary across pairs — input_dimensions_constant
    does NOT fire, so the multi-cell branch is not entered (the stored
    literal coord list would not generalise to a heterogeneous-input
    test task)."""
    legacy = {"type": "identity"}
    patterns = _multi_cell_patterns(n_pairs=2, in_h=4, in_w=4)
    patterns["pair_analyses"][1]["input_height"] = 5
    patterns["pair_analyses"][1]["input_width"] = 5
    patterns["pair_analyses"][1]["output_height"] = 5
    patterns["pair_analyses"][1]["output_width"] = 5
    out = translate_to_schema(
        legacy, "abcdef12", patterns,
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is None


def test_multi_cell_branch_returns_none_when_size_changed() -> None:
    """At least one pair has size_match=False — grid_size_preserved does
    NOT fire (top-level flag also False). Also break the second pair's
    output dimensions so the iter-21 make_grid branch does not silently
    fire instead (it gates on `grid_size_changed` + `output_dimensions_
    constant` which would otherwise both hold). This isolates the
    iter-27 branch refusal."""
    legacy = {"type": "identity"}
    patterns = _multi_cell_patterns(n_pairs=2)
    patterns["pair_analyses"][1]["size_match"] = False
    patterns["pair_analyses"][1]["output_height"] = 5  # break output_dim constancy
    patterns["grid_size_preserved"] = False
    out = translate_to_schema(
        legacy, "abcdef12", patterns,
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is None


def test_multi_cell_branch_returns_none_when_single_cell_group() -> None:
    """A single-cell group fires iter 24, not iter 26 —
    multi_cell_change_group_per_pair requires cell_count >= 2 (strict
    mutual exclusion with iter 24's matcher)."""
    legacy = {"type": "identity"}
    out = translate_to_schema(
        legacy, "abcdef12",
        _single_cell_patterns(n_pairs=2, r=1, c=2, k=7),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    # This fires iter 25's branch (single-cell), not iter 27's.
    assert out is not None
    assert out["condition"]["type"] == "single_cell_change_per_pair"


def test_multi_cell_branch_returns_none_when_multiple_groups() -> None:
    """A pair has more than one group — multi_cell_change_group_per_pair
    requires num_groups == 1 per pair."""
    legacy = {"type": "identity"}
    patterns = _multi_cell_patterns(n_pairs=2)
    # Add a second group with two cells to the first pair.
    patterns["pair_analyses"][0]["num_groups"] = 2
    patterns["pair_analyses"][0]["groups"].append({
        "input_colors": [9],
        "output_colors": [7],
        "top_row": 3,
        "top_col": 3,
        "cell_count": 2,
        "positions": [(3, 3), (3, 4)],
    })
    patterns["pair_analyses"][0]["total_changes"] = 4
    out = translate_to_schema(
        legacy, "abcdef12", patterns,
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is None


def test_multi_cell_branch_returns_none_when_blob_differs_across_pairs() -> None:
    """The defensive `_extract_multi_cell_paint_args` helper enforces that
    the blob's coord set is bit-identical across all training pairs. The
    iter-26 matcher does NOT enforce this — it pins cardinality range
    only."""
    legacy = {"type": "identity"}
    patterns = _multi_cell_patterns(n_pairs=2, positions=[(0, 0), (0, 1)])
    # Pair 1 has the same cell_count but in a different location.
    patterns["pair_analyses"][1]["groups"][0]["positions"] = [(2, 1), (2, 2)]
    patterns["pair_analyses"][1]["groups"][0]["top_row"] = 2
    patterns["pair_analyses"][1]["groups"][0]["top_col"] = 1
    out = translate_to_schema(
        legacy, "abcdef12", patterns,
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is None


def test_multi_cell_branch_returns_none_when_legacy_type_is_not_identity() -> None:
    """The translator dispatches on legacy_type == 'identity' (the slow
    path's fallback). A color_mapping legacy rule shape, even with
    multi-cell patterns, must NOT trigger the multi-cell branch."""
    legacy = {"type": "color_mapping", "mapping": {1: 2}, "confidence": 0.8}
    out = translate_to_schema(
        legacy, "abcdef12", _multi_cell_patterns(),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is None


def test_multi_cell_branch_returns_none_when_color_out_of_palette() -> None:
    """K outside the coloring primitive's valid set (0..9 or 13) — the
    helper rejects rather than minting a malformed rule that
    `validate_rule` would happily save but `coloring` would later reject."""
    legacy = {"type": "identity"}
    patterns = _multi_cell_patterns(n_pairs=2, k=11)
    out = translate_to_schema(
        legacy, "abcdef12", patterns,
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is None


def test_multi_cell_branch_returns_none_when_positions_missing() -> None:
    """Defensive: a pre-iter-27 `_analyze_pair` output (no `positions`
    field) must produce None — the extractor refuses rather than
    fabricating a coord list."""
    legacy = {"type": "identity"}
    patterns = _multi_cell_patterns(n_pairs=2)
    # Strip the positions field — simulates a stale or partially-built
    # patterns dict.
    del patterns["pair_analyses"][0]["groups"][0]["positions"]
    out = translate_to_schema(
        legacy, "abcdef12", patterns,
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is None


def test_multi_cell_branch_returns_none_when_positions_length_mismatches_cell_count() -> None:
    """Defensive: if `positions` has a different length than `cell_count`,
    the extractor refuses — the patterns dict is internally inconsistent."""
    legacy = {"type": "identity"}
    patterns = _multi_cell_patterns(n_pairs=2)
    # Inflate cell_count without growing positions: contradicts the
    # iter-27 _analyze_pair contract (len(positions) == cell_count).
    patterns["pair_analyses"][0]["groups"][0]["cell_count"] = 5
    out = translate_to_schema(
        legacy, "abcdef12", patterns,
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is None


def test_multi_cell_branch_pure_no_file_io() -> None:
    """`translate_to_schema` is pure — never writes to disk. Verify the
    cwd contains no new files after a multi-cell translation."""
    legacy = {"type": "identity"}
    with tempfile.TemporaryDirectory() as td:
        cwd = os.getcwd()
        try:
            os.chdir(td)
            before = set(os.listdir("."))
            translate_to_schema(
                legacy, "abcdef12", _multi_cell_patterns(),
                rule_id=1, now="2026-05-13T19:30:00.000000",
            )
            after = set(os.listdir("."))
        finally:
            os.chdir(cwd)
        assert before == after, "translate_to_schema must not touch disk"


def test_multi_cell_branch_does_not_mutate_inputs() -> None:
    """Purity: input legacy + patterns must be unchanged after call."""
    legacy = {"type": "identity"}
    patterns = _multi_cell_patterns()
    legacy_copy = dict(legacy)
    import copy as _copy
    patterns_copy = _copy.deepcopy(patterns)
    translate_to_schema(
        legacy, "abcdef12", patterns, rule_id=1,
        now="2026-05-13T19:30:00.000000",
    )
    assert legacy == legacy_copy
    assert patterns == patterns_copy


def test_multi_cell_branch_deterministic_across_repeats() -> None:
    """Same inputs → same output, always."""
    legacy = {"type": "identity"}
    patterns = _multi_cell_patterns()
    a = translate_to_schema(
        legacy, "abcdef12", patterns, rule_id=1,
        now="2026-05-13T19:30:00.000000",
    )
    b = translate_to_schema(
        legacy, "abcdef12", patterns, rule_id=1,
        now="2026-05-13T19:30:00.000000",
    )
    assert a == b


def test_multi_cell_rule_round_trip_through_apply_DSL() -> None:
    """End-to-end: a translated multi-cell coloring rule, when applied
    via the iter-3 DSL primitive, paints exactly the blob's cells with
    colour K on a test input."""
    from procedural_memory.DSL.apply import apply_DSL  # local import
    legacy = {"type": "identity"}
    out = translate_to_schema(
        legacy, "abcdef12",
        _multi_cell_patterns(n_pairs=2,
                             positions=[(0, 1), (1, 1), (1, 2)],
                             k=4, in_h=3, in_w=3),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is not None
    args = out["action"]["args"]
    test_input = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
    painted = apply_DSL("coloring", test_input, **args)
    assert painted == [[0, 4, 0], [0, 4, 4], [0, 0, 0]]
    # Source grid not mutated (purity).
    assert test_input == [[0, 0, 0], [0, 0, 0], [0, 0, 0]]


def test_multi_cell_branch_strict_mutual_exclusion_with_single_cell() -> None:
    """The iter-27 branch and the iter-25 branch are reachable only on
    disjoint patterns dicts: multi_cell_change_group_per_pair requires
    cell_count >= 2 per pair; single_cell_change_per_pair requires
    cell_count == 1. Verify both endpoints — neither patterns dict can
    accidentally produce the other's output."""
    legacy = {"type": "identity"}
    out_sc = translate_to_schema(
        legacy, "abcdef12", _single_cell_patterns(n_pairs=2, r=1, c=2, k=7),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out_sc is not None
    assert out_sc["condition"]["type"] == "single_cell_change_per_pair"
    assert out_sc["action"]["args"]["selection"] == [[1, 2]]

    out_mc = translate_to_schema(
        legacy, "abcdef12",
        _multi_cell_patterns(n_pairs=2, positions=[(0, 0), (0, 1)], k=7),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out_mc is not None
    assert out_mc["condition"]["type"] == "multi_cell_change_group_per_pair"
    assert out_mc["action"]["args"]["selection"] == [[0, 0], [0, 1]]


def test_multi_cell_branch_strict_mutual_exclusion_with_identity() -> None:
    """The iter-27 branch and the iter-14 identity branch are reachable
    only on disjoint patterns dicts: multi_cell requires num_groups == 1
    per pair, identity requires num_groups == 0."""
    legacy = {"type": "identity"}
    out_id = translate_to_schema(
        legacy, "abcdef12", _identity_patterns(n_pairs=2),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out_id is not None
    assert out_id["condition"]["type"] == "identity_transformation"

    out_mc = translate_to_schema(
        legacy, "abcdef12", _multi_cell_patterns(n_pairs=2),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out_mc is not None
    assert out_mc["condition"]["type"] == "multi_cell_change_group_per_pair"


def test_multi_cell_branch_strict_mutual_exclusion_with_make_grid() -> None:
    """The iter-27 branch and the iter-21 make_grid branch are reachable
    only on disjoint patterns dicts: grid_size_preserved (this iter's
    gate) requires every per-pair size_match True AND top-level
    `grid_size_preserved` True; grid_size_changed (iter 21's gate)
    requires at least one per-pair size_match False."""
    legacy = {"type": "identity"}
    out_mg = translate_to_schema(
        legacy, "abcdef12", _make_grid_patterns(out_color=7),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out_mg is not None
    assert out_mg["action"]["dsl"] == "make_grid"

    out_mc = translate_to_schema(
        legacy, "abcdef12", _multi_cell_patterns(),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out_mc is not None
    assert out_mc["action"]["dsl"] == "coloring"


def test_multi_cell_live_analyze_pair_emits_positions_field() -> None:
    """Round-trip: the live `ExtractPatternOperator._analyze_pair` MUST
    emit a `positions` field per group as of iter 27 — that is the
    iter-27 `active_operators.py` extension this translator branch
    consumes. A future regression that drops the field would silently
    cause every multi-cell branch invocation to return None; this test
    is the canonical guard against that."""
    # Local import to avoid pulling active_operators at module load time.
    from agent.active_operators import ExtractPatternOperator

    class _Grid:
        def __init__(self, raw):
            self.raw = raw
            self.height = len(raw)
            self.width = len(raw[0]) if raw else 0

    # 1x2 horizontal blob: cells (0, 0) and (0, 1) flip from 0 → 5.
    raw_in = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
    raw_out = [[5, 5, 0], [0, 0, 0], [0, 0, 0]]
    op = ExtractPatternOperator()
    analysis = op._analyze_pair(_Grid(raw_in), _Grid(raw_out))
    assert analysis["num_groups"] == 1, \
        f"live _analyze_pair produced num_groups={analysis['num_groups']}"
    group = analysis["groups"][0]
    assert "positions" in group, \
        "iter 27 contract: live _analyze_pair must emit 'positions' per group"
    assert group["positions"] == [(0, 0), (0, 1)], \
        f"positions should be row-major-sorted blob coords; got {group['positions']!r}"


# ──────────────────────────────────────────────────────────────────────────
# Iter 29 — multi-blob coloring branch
#   legacy {"type": "identity"} + patterns firing
#   multi_group_per_pair (iter 28) + output_color_uniform (iter 18) +
#   input_dimensions_constant (iter 22) + grid_size_preserved (iter 1)
#   → `coloring(grid, [(r1,c1), ..., (rM,cM)], K)` rule. The selection is
#   the row-major-sorted UNION of every blob's `positions` field across
#   the first pair's groups; the defensive helper requires this unioned
#   set to be bit-identical across pairs. K from any group's
#   `output_colors[0]`.
# ──────────────────────────────────────────────────────────────────────────

def _multi_blob_patterns(n_pairs: int = 2,
                         blob_positions: list | None = None,
                         k: int = 7, in_h: int = 5, in_w: int = 5) -> dict:
    """Patterns mimicking a multi-blob uniform-paint task. Every pair has
    `len(blob_positions)` change groups; `blob_positions[i]` is a list of
    (r, c) coords for the i-th blob. `size_match` is True per pair;
    per-pair `input_height`/`input_width`/`output_height`/`output_width`
    set to (in_h, in_w) so iter-22 input_dimensions_constant fires. The
    iter-1 top-level `grid_size_preserved` flag is True. Every blob's
    `output_colors` is `[k]`. `input_colors` varies per pair to avoid
    accidentally pinning `input_color_uniform` (iter 19).
    """
    if blob_positions is None:
        blob_positions = [[(0, 0), (0, 1)], [(3, 3)]]
    blob_canon = [sorted([(int(r), int(c)) for r, c in blob]) for blob in blob_positions]
    pair_analyses = []
    for i in range(n_pairs):
        groups = []
        total = 0
        for j, blob in enumerate(blob_canon):
            top_row = min(r for r, _ in blob)
            top_col = min(c for _, c in blob)
            groups.append({
                "input_colors": [i + j],
                "output_colors": [k],
                "top_row": top_row,
                "top_col": top_col,
                "cell_count": len(blob),
                "positions": [tuple(p) for p in blob],
            })
            total += len(blob)
        pair_analyses.append({
            "total_changes": total,
            "num_groups": len(blob_canon),
            "groups": groups,
            "size_match": True,
            "input_height": in_h,
            "input_width": in_w,
            "output_height": in_h,
            "output_width": in_w,
        })
    return {
        "grid_size_preserved": True,
        "pair_analyses": pair_analyses,
    }


def test_multi_blob_branch_fires_when_all_four_matchers_fire() -> None:
    """Smoke: legacy={"type": "identity"} + patterns firing iter
    1 / 18 / 22 / 28 should produce a schema rule whose
    `action.dsl == "coloring"` with the row-major-sorted union of all
    blob coords as `selection`."""
    legacy = {"type": "identity", "confidence": 0.0}
    out = translate_to_schema(
        legacy, "abcdef12",
        _multi_blob_patterns(n_pairs=2,
                             blob_positions=[[(0, 0), (0, 1)], [(3, 3)]],
                             k=7),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is not None, "expected multi-blob schema rule, got None"
    assert out["action"]["dsl"] == "coloring"
    assert out["action"]["args"] == {
        "selection": [[0, 0], [0, 1], [3, 3]], "color": 7,
    }


def test_multi_blob_condition_type_is_multi_group_per_pair() -> None:
    """The multi-blob branch picks `multi_group_per_pair` as
    `condition.type` — the strictest of the four gating matchers and the
    one that directly pins the per-pair group-count regime."""
    legacy = {"type": "identity"}
    out = translate_to_schema(
        legacy, "abcdef12", _multi_blob_patterns(),
        rule_id=2, now="2026-05-13T19:30:00.000000",
    )
    assert out is not None
    assert out["condition"]["type"] == "multi_group_per_pair"
    assert out["condition"]["params"] == {}
    assert isinstance(out["condition"]["min_evidence"], int)
    assert out["condition"]["min_evidence"] >= 1


def test_multi_blob_rule_passes_validate_rule() -> None:
    """The translator's output must satisfy V1–V7. V2 checks
    `condition.type` is registered (multi_group_per_pair is, iter 28);
    V3 checks `action.dsl` is registered (coloring is, iter 3)."""
    tmp_root = tempfile.mkdtemp(prefix="arbor_translate_multiblob_")
    try:
        legacy = {"type": "identity"}
        out = translate_to_schema(
            legacy, "abcdef12", _multi_blob_patterns(),
            rule_id=1, now="2026-05-13T19:30:00.000000",
        )
        assert out is not None
        validate_rule(out, procedural_memory_root=tmp_root)
    finally:
        import shutil
        shutil.rmtree(tmp_root, ignore_errors=True)


def test_multi_blob_positions_are_row_major_sorted_union() -> None:
    """The selection is the row-major-sorted union of every blob's
    positions, even when input order is scrambled. Anti-unification (and
    stored-rule lookup) requires deterministic serialization."""
    legacy = {"type": "identity"}
    # Same blobs, different orderings.
    patterns_a = _multi_blob_patterns(
        blob_positions=[[(3, 3)], [(0, 0), (0, 1)]],
    )
    patterns_b = _multi_blob_patterns(
        blob_positions=[[(0, 1), (0, 0)], [(3, 3)]],
    )
    out_a = translate_to_schema(
        legacy, "abcdef12", patterns_a, rule_id=1,
        now="2026-05-13T19:30:00.000000",
    )
    out_b = translate_to_schema(
        legacy, "abcdef12", patterns_b, rule_id=1,
        now="2026-05-13T19:30:00.000000",
    )
    assert out_a is not None and out_b is not None
    assert out_a["action"]["args"]["selection"] == \
        out_b["action"]["args"]["selection"] == [[0, 0], [0, 1], [3, 3]]


def test_multi_blob_color_matches_uniform_output_color() -> None:
    """K is extracted from any group's `output_colors[0]`. iter-18 pins
    uniformity; the helper additionally checks the value is in the
    coloring primitive's valid colour set (0..9 or 13)."""
    legacy = {"type": "identity"}
    for k in (0, 1, 5, 9, 13):
        out = translate_to_schema(
            legacy, "abcdef12",
            _multi_blob_patterns(k=k),
            rule_id=1, now="2026-05-13T19:30:00.000000",
        )
        assert out is not None, f"multi-blob branch should fire for K={k}"
        assert out["action"]["args"]["color"] == k


def test_multi_blob_covers_and_source_task_use_task_hex() -> None:
    legacy = {"type": "identity"}
    out = translate_to_schema(
        legacy, "deadbeef", _multi_blob_patterns(),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is not None
    assert out["source_task"] == "deadbeef"
    assert out["covers"] == ["deadbeef"]


def test_multi_blob_anti_unification_trace_is_null_for_source_rule() -> None:
    legacy = {"type": "identity"}
    out = translate_to_schema(
        legacy, "abcdef12", _multi_blob_patterns(),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is not None
    assert out["anti_unification_trace"] is None


def test_multi_blob_times_reused_starts_at_zero() -> None:
    legacy = {"type": "identity"}
    out = translate_to_schema(
        legacy, "abcdef12", _multi_blob_patterns(),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is not None
    assert out["times_reused"] == 0


def test_multi_blob_min_evidence_reflects_pair_count() -> None:
    legacy = {"type": "identity"}
    out2 = translate_to_schema(
        legacy, "abcdef12", _multi_blob_patterns(n_pairs=2),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out2 is not None
    assert out2["condition"]["min_evidence"] == 2

    out4 = translate_to_schema(
        legacy, "abcdef12", _multi_blob_patterns(n_pairs=4),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out4 is not None
    assert out4["condition"]["min_evidence"] == 4


def test_multi_blob_concept_and_category_are_paint_blobs_labels() -> None:
    """The multi-blob branch coins its own concept/category labels
    rather than going through `_infer_concept`. The labels are
    `paint_blobs` / `color_transform` — pluralised counterpart to the
    iter-27 `paint_blob` (single-blob) labels."""
    legacy = {"type": "identity"}
    out = translate_to_schema(
        legacy, "abcdef12", _multi_blob_patterns(),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is not None
    assert out["concept"] == "paint_blobs"
    assert out["category"] == "color_transform"


def test_multi_blob_branch_returns_none_when_color_uniform_fails() -> None:
    """Two distinct output colours across blobs — output_color_uniform
    does NOT fire."""
    legacy = {"type": "identity"}
    patterns = _multi_blob_patterns(n_pairs=2, k=3)
    patterns["pair_analyses"][0]["groups"][1]["output_colors"] = [4]
    out = translate_to_schema(
        legacy, "abcdef12", patterns,
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is None


def test_multi_blob_branch_returns_none_when_input_dims_vary() -> None:
    """Input dimensions vary across pairs — input_dimensions_constant
    does NOT fire, so the multi-blob branch is not entered."""
    legacy = {"type": "identity"}
    patterns = _multi_blob_patterns(n_pairs=2, in_h=5, in_w=5)
    patterns["pair_analyses"][1]["input_height"] = 6
    patterns["pair_analyses"][1]["input_width"] = 6
    patterns["pair_analyses"][1]["output_height"] = 6
    patterns["pair_analyses"][1]["output_width"] = 6
    out = translate_to_schema(
        legacy, "abcdef12", patterns,
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is None


def test_multi_blob_branch_returns_none_when_size_changed() -> None:
    """At least one pair has size_match=False — grid_size_preserved does
    NOT fire (top-level flag also False). Break the second pair's output
    dimensions so the iter-21 make_grid branch does not silently fire
    instead."""
    legacy = {"type": "identity"}
    patterns = _multi_blob_patterns(n_pairs=2)
    patterns["pair_analyses"][1]["size_match"] = False
    patterns["pair_analyses"][1]["output_height"] = 6  # break output_dim constancy
    patterns["grid_size_preserved"] = False
    out = translate_to_schema(
        legacy, "abcdef12", patterns,
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is None


def test_multi_blob_branch_returns_none_when_single_group() -> None:
    """A pair with `num_groups == 1` fires iter 25 / 27, not iter 28's
    matcher — multi_group_per_pair strictly requires num_groups >= 2
    (strict mutual exclusion with iters 23 / 24 / 26)."""
    legacy = {"type": "identity"}
    # A single-blob multi-cell patterns dict fires iter 27, not iter 29.
    out = translate_to_schema(
        legacy, "abcdef12",
        _multi_cell_patterns(n_pairs=2, positions=[(1, 1), (1, 2)], k=7),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is not None
    assert out["condition"]["type"] == "multi_cell_change_group_per_pair"


def test_multi_blob_branch_returns_none_when_blob_set_differs_across_pairs() -> None:
    """The defensive `_extract_multi_blob_paint_args` helper enforces
    that the unioned position set is bit-identical across all training
    pairs. The iter-28 matcher does NOT enforce this — it pins
    cardinality regime only."""
    legacy = {"type": "identity"}
    patterns = _multi_blob_patterns(
        n_pairs=2,
        blob_positions=[[(0, 0), (0, 1)], [(3, 3)]],
    )
    # Pair 1 has same blob count but different coords for the second blob.
    patterns["pair_analyses"][1]["groups"][1]["positions"] = [(4, 4)]
    patterns["pair_analyses"][1]["groups"][1]["top_row"] = 4
    patterns["pair_analyses"][1]["groups"][1]["top_col"] = 4
    out = translate_to_schema(
        legacy, "abcdef12", patterns,
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is None


def test_multi_blob_branch_returns_none_when_legacy_type_is_not_identity() -> None:
    """The translator dispatches on legacy_type == 'identity'. A
    color_mapping legacy rule shape, even with multi-blob patterns, must
    NOT trigger this branch."""
    legacy = {"type": "color_mapping", "mapping": {1: 2}, "confidence": 0.8}
    out = translate_to_schema(
        legacy, "abcdef12", _multi_blob_patterns(),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is None


def test_multi_blob_branch_returns_none_when_color_out_of_palette() -> None:
    """K outside the coloring primitive's valid set (0..9 or 13) — the
    helper rejects rather than minting a malformed rule that
    `validate_rule` would happily save but `coloring` would later reject."""
    legacy = {"type": "identity"}
    patterns = _multi_blob_patterns(n_pairs=2, k=11)
    out = translate_to_schema(
        legacy, "abcdef12", patterns,
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is None


def test_multi_blob_branch_returns_none_when_positions_missing() -> None:
    """Defensive: a pre-iter-27 `_analyze_pair` output (no `positions`
    field) on one of the blobs must produce None — the extractor
    refuses rather than fabricating a coord list."""
    legacy = {"type": "identity"}
    patterns = _multi_blob_patterns(n_pairs=2)
    del patterns["pair_analyses"][0]["groups"][0]["positions"]
    out = translate_to_schema(
        legacy, "abcdef12", patterns,
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is None


def test_multi_blob_branch_returns_none_when_positions_length_mismatches_cell_count() -> None:
    """Defensive: if any blob's `positions` length differs from its
    `cell_count`, the extractor refuses — the patterns dict is
    internally inconsistent."""
    legacy = {"type": "identity"}
    patterns = _multi_blob_patterns(n_pairs=2)
    patterns["pair_analyses"][0]["groups"][0]["cell_count"] = 99
    out = translate_to_schema(
        legacy, "abcdef12", patterns,
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is None


def test_multi_blob_branch_returns_none_when_blobs_share_a_cell() -> None:
    """Defensive: two blobs sharing a coord means the connectivity
    computation is corrupt — strict refusal rather than silent
    deduplication. (A correctly-emitted patterns dict by iter-1's
    `_analyze_pair` cannot produce this case; the test guards against
    a future regression.)"""
    legacy = {"type": "identity"}
    patterns = _multi_blob_patterns(
        n_pairs=2,
        blob_positions=[[(0, 0), (0, 1)], [(0, 1), (0, 2)]],
    )
    out = translate_to_schema(
        legacy, "abcdef12", patterns,
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is None


def test_multi_blob_branch_pure_no_file_io() -> None:
    """`translate_to_schema` is pure — never writes to disk."""
    legacy = {"type": "identity"}
    with tempfile.TemporaryDirectory() as td:
        cwd = os.getcwd()
        try:
            os.chdir(td)
            before = set(os.listdir("."))
            translate_to_schema(
                legacy, "abcdef12", _multi_blob_patterns(),
                rule_id=1, now="2026-05-13T19:30:00.000000",
            )
            after = set(os.listdir("."))
        finally:
            os.chdir(cwd)
        assert before == after, "translate_to_schema must not touch disk"


def test_multi_blob_branch_does_not_mutate_inputs() -> None:
    """Purity: input legacy + patterns must be unchanged after call."""
    legacy = {"type": "identity"}
    patterns = _multi_blob_patterns()
    legacy_copy = dict(legacy)
    import copy as _copy
    patterns_copy = _copy.deepcopy(patterns)
    translate_to_schema(
        legacy, "abcdef12", patterns, rule_id=1,
        now="2026-05-13T19:30:00.000000",
    )
    assert legacy == legacy_copy
    assert patterns == patterns_copy


def test_multi_blob_branch_deterministic_across_repeats() -> None:
    """Same inputs → same output, always."""
    legacy = {"type": "identity"}
    patterns = _multi_blob_patterns()
    a = translate_to_schema(
        legacy, "abcdef12", patterns, rule_id=1,
        now="2026-05-13T19:30:00.000000",
    )
    b = translate_to_schema(
        legacy, "abcdef12", patterns, rule_id=1,
        now="2026-05-13T19:30:00.000000",
    )
    assert a == b


def test_multi_blob_rule_round_trip_through_apply_DSL() -> None:
    """End-to-end: a translated multi-blob coloring rule, when applied
    via the iter-3 DSL primitive, paints exactly the unioned cells with
    colour K on a test input."""
    from procedural_memory.DSL.apply import apply_DSL  # local import
    legacy = {"type": "identity"}
    out = translate_to_schema(
        legacy, "abcdef12",
        _multi_blob_patterns(n_pairs=2,
                             blob_positions=[[(0, 0)], [(2, 2)]],
                             k=4, in_h=3, in_w=3),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out is not None
    args = out["action"]["args"]
    test_input = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
    painted = apply_DSL("coloring", test_input, **args)
    assert painted == [[4, 0, 0], [0, 0, 0], [0, 0, 4]]
    assert test_input == [[0, 0, 0], [0, 0, 0], [0, 0, 0]]


def test_multi_blob_branch_strict_mutual_exclusion_with_identity() -> None:
    """Iter-29 vs iter-14: multi_group_per_pair requires num_groups >= 2,
    identity_transformation requires num_groups == 0 — disjoint on the
    group-count axis."""
    legacy = {"type": "identity"}
    out_id = translate_to_schema(
        legacy, "abcdef12", _identity_patterns(n_pairs=2),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out_id is not None
    assert out_id["condition"]["type"] == "identity_transformation"

    out_mb = translate_to_schema(
        legacy, "abcdef12", _multi_blob_patterns(),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out_mb is not None
    assert out_mb["condition"]["type"] == "multi_group_per_pair"


def test_multi_blob_branch_strict_mutual_exclusion_with_single_cell() -> None:
    """Iter-29 vs iter-25: multi_group_per_pair requires num_groups >= 2,
    single_cell_change_per_pair requires num_groups == 1 — disjoint on
    the group-count axis."""
    legacy = {"type": "identity"}
    out_sc = translate_to_schema(
        legacy, "abcdef12", _single_cell_patterns(n_pairs=2, r=1, c=2, k=7),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out_sc is not None
    assert out_sc["condition"]["type"] == "single_cell_change_per_pair"

    out_mb = translate_to_schema(
        legacy, "abcdef12", _multi_blob_patterns(),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out_mb is not None
    assert out_mb["condition"]["type"] == "multi_group_per_pair"


def test_multi_blob_branch_strict_mutual_exclusion_with_multi_cell() -> None:
    """Iter-29 vs iter-27: multi_group_per_pair requires num_groups >= 2,
    multi_cell_change_group_per_pair requires num_groups == 1 — disjoint
    on the group-count axis (despite both matchers's names containing
    'multi-', they recognise orthogonal cardinality sub-axes)."""
    legacy = {"type": "identity"}
    out_mc = translate_to_schema(
        legacy, "abcdef12",
        _multi_cell_patterns(n_pairs=2, positions=[(0, 0), (0, 1)], k=7),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out_mc is not None
    assert out_mc["condition"]["type"] == "multi_cell_change_group_per_pair"

    out_mb = translate_to_schema(
        legacy, "abcdef12", _multi_blob_patterns(),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out_mb is not None
    assert out_mb["condition"]["type"] == "multi_group_per_pair"


def test_multi_blob_branch_strict_mutual_exclusion_with_make_grid() -> None:
    """Iter-29 vs iter-21: grid_size_preserved (this iter's gate)
    requires every per-pair size_match True; grid_size_changed (iter
    21's gate) requires at least one per-pair size_match False."""
    legacy = {"type": "identity"}
    out_mg = translate_to_schema(
        legacy, "abcdef12", _make_grid_patterns(out_color=7),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out_mg is not None
    assert out_mg["action"]["dsl"] == "make_grid"

    out_mb = translate_to_schema(
        legacy, "abcdef12", _multi_blob_patterns(),
        rule_id=1, now="2026-05-13T19:30:00.000000",
    )
    assert out_mb is not None
    assert out_mb["action"]["dsl"] == "coloring"
    assert out_mb["condition"]["type"] == "multi_group_per_pair"


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
        # Iter 21 — make_grid(H, W, K) branch.
        test_make_grid_branch_fires_when_all_three_matchers_fire,
        test_make_grid_condition_type_is_output_dimensions_constant,
        test_make_grid_rule_passes_validate_rule,
        test_make_grid_dimensions_match_pair_analysis,
        test_make_grid_color_matches_uniform_output_color,
        test_make_grid_covers_and_source_task_use_task_hex,
        test_make_grid_anti_unification_trace_is_null_for_source_rule,
        test_make_grid_times_reused_starts_at_zero,
        test_make_grid_min_evidence_reflects_pair_count,
        test_make_grid_concept_and_category_are_constant_make_grid_labels,
        test_make_grid_branch_returns_none_when_color_uniform_fails,
        test_make_grid_branch_returns_none_when_dimensions_vary,
        test_make_grid_branch_returns_none_when_size_preserved_everywhere,
        test_make_grid_branch_returns_none_when_zero_groups,
        test_make_grid_branch_returns_none_when_legacy_type_is_not_identity,
        test_make_grid_branch_pure_no_file_io,
        test_make_grid_branch_does_not_mutate_inputs,
        test_make_grid_branch_deterministic_across_repeats,
        test_make_grid_rule_round_trip_through_apply_DSL,
        # Iter 25 — single-cell uniform-paint branch.
        test_single_cell_branch_fires_when_all_four_matchers_fire,
        test_single_cell_condition_type_is_single_cell_change_per_pair,
        test_single_cell_rule_passes_validate_rule,
        test_single_cell_coord_matches_pair_analysis,
        test_single_cell_color_matches_uniform_output_color,
        test_single_cell_covers_and_source_task_use_task_hex,
        test_single_cell_anti_unification_trace_is_null_for_source_rule,
        test_single_cell_times_reused_starts_at_zero,
        test_single_cell_min_evidence_reflects_pair_count,
        test_single_cell_concept_and_category_are_paint_single_cell_labels,
        test_single_cell_branch_returns_none_when_color_uniform_fails,
        test_single_cell_branch_returns_none_when_input_dims_vary,
        test_single_cell_branch_returns_none_when_size_changed,
        test_single_cell_branch_returns_none_when_multi_cell_group,
        test_single_cell_branch_returns_none_when_multiple_groups,
        test_single_cell_branch_returns_none_when_coord_differs_across_pairs,
        test_single_cell_branch_returns_none_when_legacy_type_is_not_identity,
        test_single_cell_branch_returns_none_when_color_out_of_palette,
        test_single_cell_branch_pure_no_file_io,
        test_single_cell_branch_does_not_mutate_inputs,
        test_single_cell_branch_deterministic_across_repeats,
        test_single_cell_rule_round_trip_through_apply_DSL,
        test_single_cell_branch_strict_mutual_exclusion_with_identity,
        test_single_cell_branch_strict_mutual_exclusion_with_make_grid,
        # Iter 27 — multi-cell single-blob coloring branch.
        test_multi_cell_branch_fires_when_all_four_matchers_fire,
        test_multi_cell_condition_type_is_multi_cell_change_group_per_pair,
        test_multi_cell_rule_passes_validate_rule,
        test_multi_cell_positions_match_pair_analysis,
        test_multi_cell_positions_are_row_major_sorted,
        test_multi_cell_color_matches_uniform_output_color,
        test_multi_cell_covers_and_source_task_use_task_hex,
        test_multi_cell_anti_unification_trace_is_null_for_source_rule,
        test_multi_cell_times_reused_starts_at_zero,
        test_multi_cell_min_evidence_reflects_pair_count,
        test_multi_cell_concept_and_category_are_paint_blob_labels,
        test_multi_cell_branch_returns_none_when_color_uniform_fails,
        test_multi_cell_branch_returns_none_when_input_dims_vary,
        test_multi_cell_branch_returns_none_when_size_changed,
        test_multi_cell_branch_returns_none_when_single_cell_group,
        test_multi_cell_branch_returns_none_when_multiple_groups,
        test_multi_cell_branch_returns_none_when_blob_differs_across_pairs,
        test_multi_cell_branch_returns_none_when_legacy_type_is_not_identity,
        test_multi_cell_branch_returns_none_when_color_out_of_palette,
        test_multi_cell_branch_returns_none_when_positions_missing,
        test_multi_cell_branch_returns_none_when_positions_length_mismatches_cell_count,
        test_multi_cell_branch_pure_no_file_io,
        test_multi_cell_branch_does_not_mutate_inputs,
        test_multi_cell_branch_deterministic_across_repeats,
        test_multi_cell_rule_round_trip_through_apply_DSL,
        test_multi_cell_branch_strict_mutual_exclusion_with_single_cell,
        test_multi_cell_branch_strict_mutual_exclusion_with_identity,
        test_multi_cell_branch_strict_mutual_exclusion_with_make_grid,
        test_multi_cell_live_analyze_pair_emits_positions_field,
        # Iter 29 — multi-blob coloring branch.
        test_multi_blob_branch_fires_when_all_four_matchers_fire,
        test_multi_blob_condition_type_is_multi_group_per_pair,
        test_multi_blob_rule_passes_validate_rule,
        test_multi_blob_positions_are_row_major_sorted_union,
        test_multi_blob_color_matches_uniform_output_color,
        test_multi_blob_covers_and_source_task_use_task_hex,
        test_multi_blob_anti_unification_trace_is_null_for_source_rule,
        test_multi_blob_times_reused_starts_at_zero,
        test_multi_blob_min_evidence_reflects_pair_count,
        test_multi_blob_concept_and_category_are_paint_blobs_labels,
        test_multi_blob_branch_returns_none_when_color_uniform_fails,
        test_multi_blob_branch_returns_none_when_input_dims_vary,
        test_multi_blob_branch_returns_none_when_size_changed,
        test_multi_blob_branch_returns_none_when_single_group,
        test_multi_blob_branch_returns_none_when_blob_set_differs_across_pairs,
        test_multi_blob_branch_returns_none_when_legacy_type_is_not_identity,
        test_multi_blob_branch_returns_none_when_color_out_of_palette,
        test_multi_blob_branch_returns_none_when_positions_missing,
        test_multi_blob_branch_returns_none_when_positions_length_mismatches_cell_count,
        test_multi_blob_branch_returns_none_when_blobs_share_a_cell,
        test_multi_blob_branch_pure_no_file_io,
        test_multi_blob_branch_does_not_mutate_inputs,
        test_multi_blob_branch_deterministic_across_repeats,
        test_multi_blob_rule_round_trip_through_apply_DSL,
        test_multi_blob_branch_strict_mutual_exclusion_with_identity,
        test_multi_blob_branch_strict_mutual_exclusion_with_single_cell,
        test_multi_blob_branch_strict_mutual_exclusion_with_multi_cell,
        test_multi_blob_branch_strict_mutual_exclusion_with_make_grid,
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
