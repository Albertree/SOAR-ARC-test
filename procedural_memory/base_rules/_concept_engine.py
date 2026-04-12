"""
_concept_engine.py -- Concept-based rule matching via ARCKG structural comparison.

Loads parameterized concepts from procedural_memory/concepts/*.json,
matches them against tasks using ARCKG COMM/DIFF structures (not raw cell diffs),
infers parameters, validates by execution, and applies.

All structural matching operates over ARCKG relational graphs per SMT guidelines.
"""

import json
import os
import time

from procedural_memory.base_rules import _primitives as P
from ARCKG.comparison import compare as arckg_compare

_concepts = []
_loaded = False
_last_failure_diagnostics = None


def _clear_cache():
    """Reset both _loaded and _concepts. Never reset _loaded alone —
    _ensure_loaded appends, so a solo reset causes duplicates."""
    global _loaded, _concepts, _last_failure_diagnostics
    _loaded = False
    _concepts = []
    _last_failure_diagnostics = None


# ======================================================================
# Loading
# ======================================================================

def _ensure_loaded():
    global _loaded, _concepts
    if _loaded:
        return
    concepts_dir = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "concepts")
    )
    if not os.path.isdir(concepts_dir):
        _loaded = True
        return
    for fname in sorted(os.listdir(concepts_dir)):
        if fname.endswith(".json"):
            path = os.path.join(concepts_dir, fname)
            try:
                with open(path, "r") as f:
                    concept = json.load(f)
                _concepts.append(concept)
            except (json.JSONDecodeError, IOError):
                continue
    _loaded = True


# ======================================================================
# ARCKG-based structural analysis
# ======================================================================

def _extract_arckg_features(task, focus_level: str = "GRID",
                             comparisons: dict = None):
    """Extract structural features from ARCKG COMM/DIFF comparison of example pairs.
    When comparisons is provided (from wm.s1['comparisons']), uses pre-computed results
    instead of re-running arckg_compare."""
    features = {
        "size_comm": True,
        "size_comm_per_pair": [],
        "color_comm": True,
        "color_comm_per_pair": [],
        "contents_comm": True,
        "contents_comm_per_pair": [],
        "height_ratios": [],
        "width_ratios": [],
        "colors_added": set(),
        "colors_removed": set(),
        "comm_scores": [],
        "diff_fields": set(),
    }

    # Build list of inner result dicts to process
    cats = []
    if comparisons:
        for key in sorted(comparisons.keys()):
            entry = comparisons[key]
            arckg_out = entry.get("result", {})
            inner = arckg_out.get("result", {})
            if inner:
                cats.append(inner.get("category", {}))

    if not cats:
        # Fallback: compute fresh
        for pair in task.example_pairs:
            g0 = pair.input_grid
            g1 = pair.output_grid
            if g0 is None or g1 is None:
                continue
            comparison = arckg_compare(g0, g1)
            cats.append(comparison.get("result", {}).get("category", {}))

    for cat in cats:

        # Size analysis from ARCKG structure
        size_cat = cat.get("size", {})
        if size_cat.get("type") == "DIFF":
            features["size_comm_per_pair"].append(False)
            size_detail = size_cat.get("category", {})
            h_diff = size_detail.get("height", {})
            w_diff = size_detail.get("width", {})
            h_in = h_diff.get("comp1", 1) or 1
            h_out = h_diff.get("comp2", 1) or 1
            w_in = w_diff.get("comp1", 1) or 1
            w_out = w_diff.get("comp2", 1) or 1
            features["height_ratios"].append(h_out / h_in)
            features["width_ratios"].append(w_out / w_in)
        else:
            features["size_comm_per_pair"].append(True)
            features["height_ratios"].append(1.0)
            features["width_ratios"].append(1.0)

        # Color analysis from ARCKG structure
        color_cat = cat.get("color", {})
        if color_cat.get("type") == "DIFF":
            features["color_comm_per_pair"].append(False)
            color_detail = color_cat.get("category", {})
            for cstr, cmp in color_detail.items():
                if cmp.get("type") == "DIFF":
                    in_has = cmp.get("comp1", False)
                    out_has = cmp.get("comp2", False)
                    if out_has and not in_has:
                        features["colors_added"].add(int(cstr))
                    if in_has and not out_has:
                        features["colors_removed"].add(int(cstr))
        else:
            features["color_comm_per_pair"].append(True)

        # Contents analysis from ARCKG structure
        contents_cat = cat.get("contents", {})
        if contents_cat.get("type") == "DIFF":
            features["contents_comm_per_pair"].append(False)
        else:
            features["contents_comm_per_pair"].append(True)

        # Track which fields differ
        for field, field_cmp in cat.items():
            if field_cmp.get("type") == "DIFF":
                features["diff_fields"].add(field)

        # Overall COMM score (extracted from inner result, not top-level comparison)
        # When using pre-computed comparisons, we need the score from the cat's parent
        # For now, approximate from category fields
        cat_total = len(cat)
        cat_comm = sum(1 for v in cat.values() if isinstance(v, dict) and v.get("type") == "COMM")
        if cat_total > 0:
            features["comm_scores"].append(cat_comm / cat_total)

    # Object count behavior from Grid.objects (separate from the comparison loop)
    for pair in task.example_pairs:
        g0 = pair.input_grid
        g1 = pair.output_grid
        if g0 is not None and g1 is not None:
            try:
                ic = len(g0.objects) if hasattr(g0, 'objects') and g0.objects is not None else 0
                oc = len(g1.objects) if hasattr(g1, 'objects') and g1.objects is not None else 0
                features.setdefault("object_count_per_pair", []).append((ic, oc))
            except Exception:
                pass

    # Object count behavior aggregate
    obj_pairs = features.get("object_count_per_pair", [])
    if obj_pairs:
        increases = sum(1 for i, o in obj_pairs if o > i)
        decreases = sum(1 for i, o in obj_pairs if o < i)
        preserves = sum(1 for i, o in obj_pairs if o == i)
        majority = max(increases, decreases, preserves)
        if majority == increases:
            features["object_count_behavior"] = "increase"
        elif majority == decreases:
            features["object_count_behavior"] = "decrease"
        else:
            features["object_count_behavior"] = "preserve"
    else:
        features["object_count_behavior"] = None

    # Majority-vote aggregation (>50% of pairs must agree)
    for key in ("size_comm", "color_comm", "contents_comm"):
        per_pair = features.get(f"{key}_per_pair", [])
        if per_pair:
            features[key] = sum(per_pair) > len(per_pair) / 2
        # else: stays True (default — no pairs processed)

    # Convert sets to lists for JSON compatibility
    features["colors_added"] = sorted(features["colors_added"])
    features["colors_removed"] = sorted(features["colors_removed"])
    features["diff_fields"] = sorted(features["diff_fields"])

    # Object-count enrichment at OBJECT level (after descent)
    if focus_level == "OBJECT":
        for pair in task.example_pairs:
            if pair.input_grid and pair.output_grid:
                features.setdefault("object_count_per_pair", []).append((
                    len(pair.input_grid.objects or []),
                    len(pair.output_grid.objects or []),
                ))

    return features


# ======================================================================
# Signature matching (fast filter via ARCKG features)
# ======================================================================

def _signature_matches(sig, arckg_features, patterns,
                        second_order_comm=None, au_invariants=None):
    """Check if a concept's signature matches the ARCKG-derived structural features.
    This is the fast filter — eliminates obviously wrong concepts."""

    # grid_size_preserved — derived from ARCKG size COMM/DIFF
    if sig.get("grid_size_preserved") is not None:
        if sig["grid_size_preserved"] != arckg_features["size_comm"]:
            return False

    # size_ratio — check against ARCKG height/width ratios
    expected_ratio = sig.get("size_ratio")
    if expected_ratio is not None:
        for hr, wr in zip(arckg_features["height_ratios"], arckg_features["width_ratios"]):
            if abs(hr - expected_ratio[0]) > 0.01 or abs(wr - expected_ratio[1]) > 0.01:
                return False

    # color_preserved — from ARCKG color COMM
    if sig.get("color_preserved") is not None:
        if sig["color_preserved"] != arckg_features["color_comm"]:
            return False

    # requires_size_change — contents must differ
    if sig.get("requires_content_diff") is True:
        if arckg_features["contents_comm"]:
            return False

    # min_colors — check input color count
    min_colors = sig.get("min_colors")
    if min_colors is not None:
        # Use patterns data for this (already extracted)
        pair_analyses = patterns.get("pair_analyses", [])
        for analysis in pair_analyses:
            all_input_colors = set()
            for g in analysis.get("groups", []):
                all_input_colors.update(g.get("input_colors", []))
            # Also count unchanged colors — check from task directly
            break  # min_colors is a soft filter, don't be too strict

    # input_constraints
    for constraint in sig.get("input_constraints", []):
        for hr, wr in zip(arckg_features["height_ratios"], arckg_features["width_ratios"]):
            if constraint == "uniform_scale" and (hr != wr or hr < 2):
                return False
            if constraint == "integer_ratio" and (hr != int(hr) or wr != int(wr)):
                return False

    # object_count_behavior
    sig_obj = sig.get("object_count_behavior")
    if sig_obj is not None:
        feat_obj = arckg_features.get("object_count_behavior")
        if feat_obj is not None and sig_obj != feat_obj:
            return False

    # AU invariant checks (when available)
    if au_invariants and isinstance(au_invariants, dict):
        top = au_invariants.get("top_level", {})
        size_inv = top.get("size")
        if size_inv is not None and sig.get("grid_size_preserved") is not None:
            expected = "COMM" if sig["grid_size_preserved"] else "DIFF"
            if size_inv != expected:
                return False
        color_inv = top.get("color")
        if color_inv is not None and sig.get("color_preserved") is not None:
            expected = "COMM" if sig["color_preserved"] else "DIFF"
            if color_inv != expected:
                return False

    return True


# ======================================================================
# Parameter inference — operates on ARCKG DIFF structures
# ======================================================================

_INFER_METHODS = {}


def _register_infer(name):
    def decorator(fn):
        _INFER_METHODS[name] = fn
        return fn
    return decorator


@_register_infer("bg_color")
def _infer_bg_color(task, arckg_features, patterns):
    """Background = most frequent color in input. Must be consistent across pairs."""
    bg = None
    for pair in task.example_pairs:
        b = P.find_bg_color(pair.input_grid.raw)
        if bg is None:
            bg = b
        elif bg != b:
            return None
    return bg


@_register_infer("ratio_hw")
def _infer_ratio_hw(task, arckg_features, patterns):
    """Uniform integer scale factor derived from ARCKG size DIFF."""
    if arckg_features["size_comm"]:
        return None  # no size change
    ratios = arckg_features["height_ratios"]
    w_ratios = arckg_features["width_ratios"]
    if not ratios:
        return None
    # Must be uniform integer ratio, same for h and w
    factor = ratios[0]
    if factor < 2 or factor != int(factor):
        return None
    for hr, wr in zip(ratios, w_ratios):
        if hr != factor or wr != factor:
            return None
    return int(factor)


@_register_infer("color_map_from_arckg")
def _infer_color_map(task, arckg_features, patterns):
    """Build {old: new} color mapping from ARCKG DIFF on contents.
    Inspects the DIFF comp1/comp2 values to find consistent per-cell color changes."""
    mapping = {}
    for pair in task.example_pairs:
        g0 = pair.input_grid
        g1 = pair.output_grid
        if g0 is None or g1 is None:
            continue
        # Use ARCKG comparison to get the DIFF structure
        comparison = arckg_compare(g0, g1)
        cat = comparison.get("result", {}).get("category", {})
        contents = cat.get("contents", {})
        if contents.get("type") != "DIFF":
            continue
        # Extract color transitions from comp1/comp2 (the raw grids in DIFF)
        grid_in = contents.get("comp1", [])
        grid_out = contents.get("comp2", [])
        if not grid_in or not grid_out:
            continue
        h = min(len(grid_in), len(grid_out))
        for r in range(h):
            w = min(len(grid_in[r]), len(grid_out[r]))
            for c in range(w):
                old, new = grid_in[r][c], grid_out[r][c]
                if old != new:
                    if old in mapping and mapping[old] != new:
                        return None  # inconsistent
                    mapping[old] = new
    return mapping if mapping else None


@_register_infer("non_bg_single")
def _infer_non_bg_single(task, arckg_features, patterns):
    """The single non-bg color. Derived from ARCKG color structure."""
    color = None
    for pair in task.example_pairs:
        bg = P.find_bg_color(pair.input_grid.raw)
        non_bg = set()
        for row in pair.input_grid.raw:
            for v in row:
                if v != bg:
                    non_bg.add(v)
        if len(non_bg) != 1:
            return None
        c = non_bg.pop()
        if color is None:
            color = c
        elif color != c:
            return None
    return color


@_register_infer("column_index_from_arckg")
def _infer_column_index(task, arckg_features, patterns):
    """Find which column is preserved in output. Uses ARCKG contents DIFF
    to identify the column that remains unchanged between comp1 and comp2."""
    col = None
    for pair in task.example_pairs:
        g0 = pair.input_grid
        g1 = pair.output_grid
        comparison = arckg_compare(g0, g1)
        cat = comparison.get("result", {}).get("category", {})
        contents = cat.get("contents", {})

        # If contents are COMM, all columns are preserved — not useful
        if contents.get("type") == "COMM":
            return None

        grid_in = contents.get("comp1", [])
        grid_out = contents.get("comp2", [])
        if not grid_in or not grid_out:
            return None
        h = min(len(grid_in), len(grid_out))
        w_in = len(grid_in[0]) if grid_in else 0
        w_out = len(grid_out[0]) if grid_out else 0
        if w_in != w_out:
            return None

        bg = P.find_bg_color(grid_out)
        preserved_cols = []
        for c in range(w_in):
            if all(grid_out[r][c] == grid_in[r][c] for r in range(h)):
                if any(grid_in[r][c] != bg for r in range(h)):
                    preserved_cols.append(c)
        if len(preserved_cols) != 1:
            return None
        if col is None:
            col = preserved_cols[0]
        elif col != preserved_cols[0]:
            return None
    return col


@_register_infer("from_examples")
def _infer_from_examples(task, arckg_features, patterns):
    """Placeholder — actual brute-force handled by the engine."""
    return None


# ======================================================================
# Brute-force parameter resolution
# ======================================================================

def _brute_force_resolve(concept, known_params, unresolved, task):
    """Try candidate values for unresolved params. Execute concept and validate."""
    if len(unresolved) > 2:
        return None  # too many unknowns

    # Generate candidates per param
    param_candidates = {}
    for pname, pdef in unresolved:
        ptype = pdef.get("type", "int")
        if ptype == "color":
            param_candidates[pname] = list(range(10))
        elif ptype == "int":
            param_candidates[pname] = list(range(1, 31))
        elif ptype == "position":
            # Use first example's grid dims
            pair = task.example_pairs[0]
            h, w = len(pair.input_grid.raw), len(pair.input_grid.raw[0])
            param_candidates[pname] = list(range(max(h, w)))
        elif ptype == "str":
            param_candidates[pname] = pdef.get("candidates", [])
        else:
            return None

    # Single param brute force
    if len(unresolved) == 1:
        pname = unresolved[0][0]
        for val in param_candidates[pname]:
            test_params = dict(known_params)
            test_params[pname] = val
            if _validate_concept(concept, test_params, task):
                return {pname: val}
        return None

    # Two param brute force (capped at 300 combinations)
    names = [u[0] for u in unresolved]
    cands_0 = param_candidates[names[0]]
    cands_1 = param_candidates[names[1]]
    count = 0
    for v0 in cands_0:
        for v1 in cands_1:
            count += 1
            if count > 300:
                return None
            test_params = dict(known_params)
            test_params[names[0]] = v0
            test_params[names[1]] = v1
            if _validate_concept(concept, test_params, task):
                return {names[0]: v0, names[1]: v1}
    return None


# ======================================================================
# Step execution
# ======================================================================

def _execute_concept(concept, params, input_grid_raw):
    """Execute concept steps on a raw grid. Returns output grid or None."""
    env = {"input": input_grid_raw}
    env["input_height"] = len(input_grid_raw)
    env["input_width"] = len(input_grid_raw[0]) if input_grid_raw else 0
    env.update(params)

    for step in concept["steps"]:
        primitive_name = step["primitive"]
        fn = getattr(P, primitive_name, None)
        if fn is None:
            return None

        # Resolve args — $ref lookups from env
        resolved_args = {}
        for arg_name, arg_val in step["args"].items():
            if isinstance(arg_val, str) and arg_val.startswith("$"):
                ref = arg_val[1:]
                if ref not in env:
                    return None
                resolved_args[arg_name] = env[ref]
            else:
                resolved_args[arg_name] = arg_val

        try:
            result = fn(**resolved_args)
        except Exception:
            return None

        env[step["output"]] = result

    # Resolve final result
    result_ref = concept.get("result", "")
    if isinstance(result_ref, str) and result_ref.startswith("$"):
        return env.get(result_ref[1:])
    return None


# ======================================================================
# Validation
# ======================================================================

def _partial_score(predicted, expected):
    """Fraction of cells correct (0.0-1.0). Returns 0.0 if shapes differ."""
    if predicted is None or expected is None:
        return 0.0
    if len(predicted) != len(expected) or not predicted or not expected:
        return 0.0
    if len(predicted[0]) != len(expected[0]):
        return 0.0
    total = len(predicted) * len(predicted[0])
    if total == 0:
        return 0.0
    correct = sum(
        1 for r in range(len(predicted))
        for c in range(len(predicted[0]))
        if predicted[r][c] == expected[r][c]
    )
    return correct / total


def _validate_concept(concept, params, task, verbose=False):
    """Check that concept with these params produces correct output for ALL example pairs.
    When verbose=True, returns (False, diagnostic_dict) on failure instead of bare False."""
    for i, pair in enumerate(task.example_pairs):
        if pair.input_grid is None or pair.output_grid is None:
            continue
        predicted = _execute_concept(concept, params, pair.input_grid.raw)
        if predicted is None:
            if verbose:
                return False, {
                    "concept_id": concept["concept_id"],
                    "pair_index": i,
                    "reason": "execution_returned_none",
                    "partial_score": 0.0,
                }
            return False
        if predicted != pair.output_grid.raw:
            if verbose:
                expected = pair.output_grid.raw
                wrong = [(r, c, predicted[r][c], expected[r][c])
                         for r in range(len(predicted))
                         for c in range(len(predicted[0]))
                         if predicted[r][c] != expected[r][c]]
                total = len(predicted) * len(predicted[0])
                return False, {
                    "concept_id": concept["concept_id"],
                    "pair_index": i,
                    "reason": "output_mismatch",
                    "total_cells": total,
                    "wrong_cells": len(wrong),
                    "partial_score": (total - len(wrong)) / total if total else 0.0,
                    "wrong_cell_sample": wrong[:5],
                }
            return False
    if verbose:
        return True, None
    return True


# ======================================================================
# Public API
# ======================================================================

def try_concepts(patterns, task, focus_level: str = "GRID",
                 comparisons: dict = None, second_order_comm: list = None,
                 au_invariants: dict = None):
    """Try all concepts against a task. Returns rule dict or None.

    Flow:
      1. Extract ARCKG structural features from example pairs
      2. For each concept: signature match → infer params → validate
      3. Return first valid concept as a rule dict
    """
    _ensure_loaded()
    if not _concepts:
        return None

    # Extract structural features — use pre-computed comparisons if available
    try:
        arckg_features = _extract_arckg_features(
            task, focus_level=focus_level, comparisons=comparisons
        )
    except Exception:
        arckg_features = {
            "size_comm": True, "color_comm": True, "contents_comm": True,
            "height_ratios": [], "width_ratios": [],
            "colors_added": [], "colors_removed": [],
            "comm_scores": [], "diff_fields": [],
        }

    global _last_failure_diagnostics
    best_near_miss = None
    concepts_tried = 0

    for concept in _concepts:
        sig = concept.get("signature", {})
        if not _signature_matches(sig, arckg_features, patterns,
                                   second_order_comm=second_order_comm,
                                   au_invariants=au_invariants):
            continue

        concepts_tried += 1

        # Infer parameters
        params = {}
        all_resolved = True
        brute_force_params = []

        for pname, pdef in concept.get("parameters", {}).items():
            infer_method = pdef.get("infer")
            if infer_method and infer_method != "from_examples":
                fn = _INFER_METHODS.get(infer_method)
                if fn:
                    value = fn(task, arckg_features, patterns)
                    if value is not None:
                        params[pname] = value
                        continue
            if pdef.get("default") is not None:
                params[pname] = pdef["default"]
                continue
            if infer_method == "from_examples":
                brute_force_params.append((pname, pdef))
                continue
            all_resolved = False
            break

        if not all_resolved:
            continue

        # Handle brute-force parameters
        if brute_force_params:
            resolved = _brute_force_resolve(concept, params, brute_force_params, task)
            if resolved is None:
                continue
            params.update(resolved)

        # Validate: execute concept on all example pairs
        valid, diag = _validate_concept(concept, params, task, verbose=True)
        if valid:
            _last_failure_diagnostics = None
            return {
                "type": f"concept:{concept['concept_id']}",
                "concept_id": concept["concept_id"],
                "params": params,
                "confidence": 1.0,
            }

        if diag is not None:
            score = diag.get("partial_score", 0.0)
            if best_near_miss is None or score > best_near_miss.get("partial_score", 0.0):
                best_near_miss = diag

    _last_failure_diagnostics = {
        "concepts_tried": concepts_tried,
        "best_near_miss": best_near_miss,
    }
    return None


def try_single_concept(task, concept_id: str):
    """Try a single concept by ID against a task without requiring the SOAR pipeline.
    Used by the stored-rule fast path to re-infer params at reuse time.
    Returns a full rule dict with re-inferred params, or None."""
    _ensure_loaded()
    try:
        arckg_features = _extract_arckg_features(task)
    except Exception:
        arckg_features = {
            "size_comm": True, "color_comm": True, "contents_comm": True,
            "height_ratios": [], "width_ratios": [],
            "colors_added": [], "colors_removed": [],
            "comm_scores": [], "diff_fields": [],
        }
    patterns = {}

    for concept in _concepts:
        if concept["concept_id"] != concept_id:
            continue
        sig = concept.get("signature", {})
        if not _signature_matches(sig, arckg_features, patterns):
            return None
        params = {}
        all_resolved = True
        brute_force_params = []
        for pname, pdef in concept.get("parameters", {}).items():
            infer_method = pdef.get("infer")
            if infer_method and infer_method != "from_examples":
                fn = _INFER_METHODS.get(infer_method)
                if fn:
                    value = fn(task, arckg_features, patterns)
                    if value is not None:
                        params[pname] = value
                        continue
            if pdef.get("default") is not None:
                params[pname] = pdef["default"]
                continue
            if infer_method == "from_examples":
                brute_force_params.append((pname, pdef))
                continue
            all_resolved = False
            break
        if not all_resolved:
            return None
        if brute_force_params:
            resolved = _brute_force_resolve(concept, params, brute_force_params, task)
            if resolved is None:
                return None
            params.update(resolved)
        if _validate_concept(concept, params, task):
            return {
                "type": f"concept:{concept_id}",
                "concept_id": concept_id,
                "params": params,
                "confidence": 1.0,
            }
        return None
    return None


def _extract_arckg_features_for_composition(raw_pairs: list) -> dict:
    """Extract ARCKG features from (input_raw, output_raw) tuples.
    Lightweight version for concept B signature matching in composition search."""
    features = {
        "size_comm": True, "color_comm": True, "contents_comm": True,
        "height_ratios": [], "width_ratios": [],
        "colors_added": [], "colors_removed": [],
        "comm_scores": [], "diff_fields": set(),
        "object_count_behavior": None,
        "size_comm_per_pair": [], "color_comm_per_pair": [], "contents_comm_per_pair": [],
    }
    for inp, out in raw_pairs:
        h_in, w_in = len(inp), (len(inp[0]) if inp else 0)
        h_out, w_out = len(out), (len(out[0]) if out else 0)
        size_same = (h_in == h_out and w_in == w_out)
        features["size_comm_per_pair"].append(size_same)
        if not size_same:
            features["size_comm"] = False
        features["height_ratios"].append(h_out / max(h_in, 1))
        features["width_ratios"].append(w_out / max(w_in, 1))
        in_colors = {v for row in inp for v in row}
        out_colors = {v for row in out for v in row}
        color_same = (in_colors == out_colors)
        features["color_comm_per_pair"].append(color_same)
        if not color_same:
            features["color_comm"] = False
            for c in sorted(out_colors - in_colors):
                if c not in features["colors_added"]:
                    features["colors_added"].append(c)
            for c in sorted(in_colors - out_colors):
                if c not in features["colors_removed"]:
                    features["colors_removed"].append(c)
        contents_same = (inp == out)
        features["contents_comm_per_pair"].append(contents_same)
        if not contents_same:
            features["contents_comm"] = False
    features["diff_fields"] = sorted(features["diff_fields"])
    return features


def try_two_step_composition(patterns, task, time_budget_sec: float = 2.0):
    """Try all pairs (A, B) where applying A then B maps inputs to outputs.
    Gated by partial_score > 0.8 and a hard time budget. Ephemeral — not saved."""
    _ensure_loaded()
    if not _concepts:
        return None

    global _last_failure_diagnostics
    if _last_failure_diagnostics:
        nm = _last_failure_diagnostics.get("best_near_miss")
        best_score = nm.get("partial_score", 0.0) if nm else 0.0
        if best_score < 0.8:
            return None

    start = time.time()

    try:
        arckg_features = _extract_arckg_features(task)
    except Exception:
        arckg_features = {
            "size_comm": True, "color_comm": True, "contents_comm": True,
            "height_ratios": [], "width_ratios": [],
            "colors_added": [], "colors_removed": [],
            "comm_scores": [], "diff_fields": [],
        }

    example_pairs = [p for p in task.example_pairs
                     if p.input_grid is not None and p.output_grid is not None]
    if not example_pairs:
        return None

    for concept_a in _concepts:
        if time.time() - start > time_budget_sec:
            return None

        params_a = {}
        valid_a = True
        brute_a = []
        for pname, pdef in concept_a.get("parameters", {}).items():
            infer = pdef.get("infer")
            if infer and infer != "from_examples":
                fn = _INFER_METHODS.get(infer)
                if fn:
                    val = fn(task, arckg_features, patterns)
                    if val is not None:
                        params_a[pname] = val
                        continue
            if pdef.get("default") is not None:
                params_a[pname] = pdef["default"]
                continue
            if infer == "from_examples":
                brute_a.append((pname, pdef))
                continue
            valid_a = False
            break
        if not valid_a:
            continue
        if brute_a:
            resolved = _brute_force_resolve(concept_a, params_a, brute_a, task)
            if resolved is None:
                continue
            params_a.update(resolved)

        intermediates = []
        for pair in example_pairs:
            mid = _execute_concept(concept_a, params_a, pair.input_grid.raw)
            if mid is None:
                break
            intermediates.append((mid, pair.output_grid.raw))
        if len(intermediates) != len(example_pairs):
            continue

        b_features = _extract_arckg_features_for_composition(intermediates)

        for concept_b in _concepts:
            if time.time() - start > time_budget_sec:
                return None
            if not _signature_matches(concept_b.get("signature", {}), b_features, {}):
                continue

            params_b = {}
            valid_b = True
            brute_b = []
            for pname, pdef in concept_b.get("parameters", {}).items():
                infer = pdef.get("infer")
                if infer == "bg_color":
                    params_b[pname] = P.find_bg_color(intermediates[0][0])
                    continue
                if infer == "non_bg_single":
                    non_bg = P.unique_colors(intermediates[0][0], exclude_bg=True)
                    if len(non_bg) == 1:
                        params_b[pname] = non_bg[0]
                    else:
                        valid_b = False
                        break
                    continue
                if pdef.get("default") is not None:
                    params_b[pname] = pdef["default"]
                    continue
                if pdef.get("type") == "color":
                    brute_b.append((pname, pdef))
                    continue
                valid_b = False
                break
            if not valid_b:
                continue

            if brute_b:
                solved = True
                for pname, pdef in brute_b:
                    found = False
                    for color_val in range(10):
                        test_p = dict(params_b)
                        test_p[pname] = color_val
                        if all(_execute_concept(concept_b, test_p, m) == e
                               for m, e in intermediates):
                            params_b[pname] = color_val
                            found = True
                            break
                    if not found:
                        solved = False
                        break
                if not solved:
                    continue

            if all(_execute_concept(concept_b, params_b, m) == e
                   for m, e in intermediates):
                return {
                    "type": f"composition:{concept_a['concept_id']}+{concept_b['concept_id']}",
                    "concept_id_a": concept_a["concept_id"],
                    "params_a": params_a,
                    "concept_id_b": concept_b["concept_id"],
                    "params_b": params_b,
                    "confidence": 1.0,
                }

    return None


def apply_concept(rule, input_grid):
    """Apply a concept rule to an input grid. Called by rule_engine.apply()."""
    concept_id = rule.get("concept_id")
    params = rule.get("params", {})

    _ensure_loaded()
    concept = None
    for c in _concepts:
        if c["concept_id"] == concept_id:
            concept = c
            break

    if concept is None:
        return None

    return _execute_concept(concept, params, input_grid.raw)
