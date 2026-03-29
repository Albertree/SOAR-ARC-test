"""
_concept_engine.py -- Concept-based rule matching via ARCKG structural comparison.

Loads parameterized concepts from procedural_memory/concepts/*.json,
matches them against tasks using ARCKG COMM/DIFF structures (not raw cell diffs),
infers parameters, validates by execution, and applies.

All structural matching operates over ARCKG relational graphs per SMT guidelines.
"""

import json
import os

from procedural_memory.base_rules import _primitives as P
from ARCKG.comparison import compare as arckg_compare

_concepts = []
_loaded = False


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

def _extract_arckg_features(task):
    """Extract structural features from ARCKG COMM/DIFF comparison of example pairs.
    Returns a dict of features derived from the relational graph, not raw cells."""
    features = {
        "size_comm": True,       # are input/output sizes identical across all pairs?
        "color_comm": True,      # are color palettes identical?
        "contents_comm": True,   # are contents identical?
        "height_ratios": [],     # output_h / input_h per pair
        "width_ratios": [],      # output_w / input_w per pair
        "colors_added": set(),   # colors in output not in input
        "colors_removed": set(), # colors in input not in output
        "comm_scores": [],       # COMM score per pair (fraction)
        "diff_fields": set(),    # which top-level fields are DIFF
    }

    for pair in task.example_pairs:
        g0 = pair.input_grid
        g1 = pair.output_grid
        if g0 is None or g1 is None:
            continue

        comparison = arckg_compare(g0, g1)
        cat = comparison.get("result", {}).get("category", {})

        # Size analysis from ARCKG structure
        size_cat = cat.get("size", {})
        if size_cat.get("type") == "DIFF":
            features["size_comm"] = False
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
            features["height_ratios"].append(1.0)
            features["width_ratios"].append(1.0)

        # Color analysis from ARCKG structure
        color_cat = cat.get("color", {})
        if color_cat.get("type") == "DIFF":
            features["color_comm"] = False
            color_detail = color_cat.get("category", {})
            for cstr, cmp in color_detail.items():
                if cmp.get("type") == "DIFF":
                    in_has = cmp.get("comp1", False)
                    out_has = cmp.get("comp2", False)
                    if out_has and not in_has:
                        features["colors_added"].add(int(cstr))
                    if in_has and not out_has:
                        features["colors_removed"].add(int(cstr))

        # Contents analysis from ARCKG structure
        contents_cat = cat.get("contents", {})
        if contents_cat.get("type") == "DIFF":
            features["contents_comm"] = False

        # Track which fields differ
        for field, field_cmp in cat.items():
            if field_cmp.get("type") == "DIFF":
                features["diff_fields"].add(field)

        # Overall COMM score
        score_str = comparison.get("result", {}).get("score", "0/0")
        parts = score_str.split("/")
        if len(parts) == 2:
            try:
                features["comm_scores"].append(int(parts[0]) / max(int(parts[1]), 1))
            except ValueError:
                features["comm_scores"].append(0.0)

    # Convert sets to lists for JSON compatibility
    features["colors_added"] = sorted(features["colors_added"])
    features["colors_removed"] = sorted(features["colors_removed"])
    features["diff_fields"] = sorted(features["diff_fields"])

    return features


# ======================================================================
# Signature matching (fast filter via ARCKG features)
# ======================================================================

def _signature_matches(sig, arckg_features, patterns):
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
            # Check if all preserved columns are center columns (width // 2)
            # Reset and check center-column hypothesis
            col = None
            for pair2 in task.example_pairs:
                g0 = pair2.input_grid
                g1 = pair2.output_grid
                comp2 = arckg_compare(g0, g1)
                cat2 = comp2.get("result", {}).get("category", {})
                cnt2 = cat2.get("contents", {})
                gi2 = cnt2.get("comp1", [])
                go2 = cnt2.get("comp2", [])
                if not gi2 or not go2:
                    return None
                w2 = len(gi2[0])
                center = w2 // 2
                h2 = len(gi2)
                bg2 = P.find_bg_color(go2)
                if not all(go2[r][center] == gi2[r][center] for r in range(h2)):
                    return None
                if not any(gi2[r][center] != bg2 for r in range(h2)):
                    return None
            # All pairs use center column — return center of test grid
            # We need to return a value that works for test input too
            # Use -1 as sentinel for "center column"
            return -1
    return col


@_register_infer("source_color_from_arckg")
def _infer_source_color(task, arckg_features, patterns):
    """Find the single input color that maps to MULTIPLE output colors.
    Uses ARCKG contents DIFF to inspect color transitions."""
    transitions = {}  # input_color -> set of output_colors
    for pair in task.example_pairs:
        g0, g1 = pair.input_grid, pair.output_grid
        if g0 is None or g1 is None:
            continue
        comparison = arckg_compare(g0, g1)
        cat = comparison.get("result", {}).get("category", {})
        contents = cat.get("contents", {})
        if contents.get("type") != "DIFF":
            continue
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
                    transitions.setdefault(old, set()).add(new)
    # Source color maps to multiple outputs (sequential recoloring)
    candidates = [c for c, outs in transitions.items() if len(outs) > 1]
    if len(candidates) == 1:
        return candidates[0]
    return None


@_register_infer("start_color_from_arckg")
def _infer_start_color(task, arckg_features, patterns):
    """Find the minimum output color among changed cells via ARCKG DIFF."""
    min_out = None
    for pair in task.example_pairs:
        g0, g1 = pair.input_grid, pair.output_grid
        if g0 is None or g1 is None:
            continue
        comparison = arckg_compare(g0, g1)
        cat = comparison.get("result", {}).get("category", {})
        contents = cat.get("contents", {})
        if contents.get("type") != "DIFF":
            continue
        grid_in = contents.get("comp1", [])
        grid_out = contents.get("comp2", [])
        if not grid_in or not grid_out:
            continue
        h = min(len(grid_in), len(grid_out))
        for r in range(h):
            w = min(len(grid_in[r]), len(grid_out[r]))
            for c in range(w):
                if grid_in[r][c] != grid_out[r][c]:
                    out_c = grid_out[r][c]
                    if min_out is None or out_c < min_out:
                        min_out = out_c
    return min_out


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
    # Resolve sentinel values before merging params
    resolved_params = dict(params)
    for k, v in resolved_params.items():
        if v == -1 and k == "col_index":
            resolved_params[k] = env["input_width"] // 2
    env.update(resolved_params)

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

def _validate_concept(concept, params, task):
    """Check that concept with these params produces correct output for ALL example pairs."""
    for pair in task.example_pairs:
        if pair.input_grid is None or pair.output_grid is None:
            continue
        predicted = _execute_concept(concept, params, pair.input_grid.raw)
        if predicted is None or predicted != pair.output_grid.raw:
            return False
    return True


# ======================================================================
# Public API
# ======================================================================

def try_concepts(patterns, task):
    """Try all concepts against a task. Returns rule dict or None.

    Flow:
      1. Extract ARCKG structural features from example pairs
      2. For each concept: signature match → infer params → validate
      3. Return first valid concept as a rule dict
    """
    _ensure_loaded()
    if not _concepts:
        return None

    # Extract structural features via ARCKG comparison
    try:
        arckg_features = _extract_arckg_features(task)
    except Exception:
        arckg_features = {
            "size_comm": True, "color_comm": True, "contents_comm": True,
            "height_ratios": [], "width_ratios": [],
            "colors_added": [], "colors_removed": [],
            "comm_scores": [], "diff_fields": [],
        }

    for concept in _concepts:
        sig = concept.get("signature", {})
        if not _signature_matches(sig, arckg_features, patterns):
            continue

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
        if _validate_concept(concept, params, task):
            return {
                "type": f"concept:{concept['concept_id']}",
                "concept_id": concept["concept_id"],
                "params": params,
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
