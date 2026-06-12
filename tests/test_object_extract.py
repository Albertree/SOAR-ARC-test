"""Tests for the *object-extract* family (crop the grid to one selected object's
bounding box).

A new transformation family expressed as an *argument expression* over the frozen
`make_grid` + `coloring` primitives (render the bbox window of a selected object
via `render_grid_via_primitives`) — F3-exempt (no new DSL primitive: the *selector*
naming which object the crop is drawn around is the argument, not a new `def`).
Mirrors the geometric/scale/symmetry families: it reuses the existing recognition
vocabulary (`SELECTOR_VOCAB`), adds an analyzer (`analyze_object_extract`), a
matcher (`agent/conditions/object_extract`), and renders the cropped window with
the shared `bbox_subgrid` crop so recognition and rendering agree by construction.

The selector is the §2.5-2b selection lift (max_size / unique_shape / …), the
cross-pair COMM that consistently picks the extracted object, recomputed off each
test input's own objects at predict time (P5). Grounds three real ARC-AGI-2 tasks
(1cf80156, be94b721 max_size; 88a62173 unique_shape) plus the madeup
extract-largest task.
"""

from types import SimpleNamespace

from agent.dsl_expr.selection import (
    analyze_object_extract,
    bbox_subgrid,
    objects_of,
    SELECTOR_VOCAB,
)
from agent.dsl_expr.render import render_grid_via_primitives
from agent.conditions import match as match_condition


def _pair(inp, out):
    return SimpleNamespace(
        input_grid=SimpleNamespace(raw=inp),
        output_grid=SimpleNamespace(raw=out),
    )


# A two-pair extract-largest example (value-agnostic: different palettes / sizes).
# Background 0; a big solid rectangle is the largest object, a lone pixel a
# distractor placed outside the rectangle's bbox.
# (the distractor pixel is kept clear of the rectangle's 8-neighbourhood so the
# two stay distinct objects under 8-connectivity).
P1_IN = [
    [0, 0, 0, 0, 0, 0, 0],
    [0, 3, 3, 3, 0, 0, 0],
    [0, 3, 3, 3, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 4, 0],
    [0, 0, 0, 0, 0, 0, 0],
]
P1_OUT = [[3, 3, 3], [3, 3, 3]]

P2_IN = [
    [0, 0, 0, 0, 0, 1],
    [0, 0, 0, 0, 0, 0],
    [0, 6, 6, 0, 0, 0],
    [0, 6, 6, 0, 0, 0],
    [0, 6, 6, 0, 0, 0],
    [0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0],
]
P2_OUT = [[6, 6], [6, 6], [6, 6]]


def test_bbox_subgrid_crops_to_cells():
    grid = [
        [0, 0, 0, 0],
        [0, 7, 7, 0],
        [0, 7, 7, 0],
        [0, 0, 0, 0],
    ]
    cells = [(1, 1), (1, 2), (2, 1), (2, 2)]
    assert bbox_subgrid(grid, cells) == [[7, 7], [7, 7]]


def test_bbox_subgrid_empty_is_none():
    assert bbox_subgrid([[0]], []) is None


def test_analyze_learns_max_size_selector():
    sig = analyze_object_extract([_pair(P1_IN, P1_OUT), _pair(P2_IN, P2_OUT)])
    assert sig["valid_all"] is True
    assert sig["selector"] == "max_size"
    assert sig["evidence"] == 2


def test_matcher_fires_on_extract():
    sig = analyze_object_extract([_pair(P1_IN, P1_OUT), _pair(P2_IN, P2_OUT)])
    assert match_condition("object_extract", {"object_extract": sig},
                           {"min_evidence": 2}) is True


def test_render_equals_selected_object_bbox():
    # Recompute the selector, apply to P2's input, and render the cropped window;
    # it must equal the expected output (render ↔ recognition agree).
    sig = analyze_object_extract([_pair(P1_IN, P1_OUT), _pair(P2_IN, P2_OUT)])
    selector = SELECTOR_VOCAB[sig["selector"]]
    obj = selector(objects_of(P2_IN), P2_IN)
    window = bbox_subgrid(P2_IN, obj["cells"])
    assert render_grid_via_primitives(window) == P2_OUT


def test_abstains_on_single_pair():
    # One pair cannot establish the selector role across the family.
    sig = analyze_object_extract([_pair(P1_IN, P1_OUT)])
    assert sig["selector"] is None
    assert match_condition("object_extract", {"object_extract": sig},
                           {"min_evidence": 2}) is False


def test_inert_on_identity():
    # Output == input (no crop) must not be claimed as an extraction.
    g = [[0, 5], [5, 0]]
    sig = analyze_object_extract([_pair(g, g), _pair(g, g)])
    assert sig["selector"] is None


def test_inert_on_same_size_recolor():
    # A same-size colour change is not an object crop — the family abstains so it
    # never perturbs the recolor families.
    a = [[0, 2, 0], [0, 2, 0]]
    b = [[0, 3, 0], [0, 3, 0]]
    sig = analyze_object_extract([_pair(a, b), _pair(a, b)])
    assert sig["selector"] is None


def test_abstains_when_selector_ambiguous_at_extreme():
    # Two objects tied for largest → max_size returns None → no consistent
    # selector → the family abstains (honest, no wrong crop).
    inp = [
        [3, 3, 0, 0, 4, 4],
        [3, 3, 0, 0, 4, 4],
    ]
    out = [[3, 3], [3, 3]]
    sig = analyze_object_extract([_pair(inp, out), _pair(inp, out)])
    assert sig["selector"] is None
