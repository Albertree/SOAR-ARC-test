"""Tests for the grid-level *partition-band* dimension reading.

A new grid-level **rectangular** reading under `agent/dsl_expr/selection.py`
(F3-exempt argument vocabulary — no transformation primitive, no new matcher, no
new rule). An input divided by full-line separators into a lattice of regions has
output = a solid rectangle counting those regions (rowbands x colbands), filled
with the content (majority) colour. The §2.1 "grid size = f(input structure)"
concept at *grid* level (no single object). It folds into the existing
`size_to_grid` family (rule_001) as one more value `dim_property` ranges over —
covers rises, rule count holds (BACKLOG_LOOP §2.5-4). Grounds two real ARC-AGI-2
tasks (1190e5a7, 7039b2d7).
"""

from types import SimpleNamespace

from agent.dsl_expr.selection import (
    separator_color_of,
    partition_bands_of,
    most_frequent_color,
    analyze_object_size_grid,
    GRID_RECT_DIM_VOCAB,
)
from agent.dsl_expr.render import render_solid_rect


def _pair(inp, out):
    return SimpleNamespace(
        input_grid=SimpleNamespace(raw=inp),
        output_grid=SimpleNamespace(raw=out),
    )


# A 5x7 grid: separator colour 2 (row 2 full, cols 2 & 5 full), content 4.
# 2 row-bands x 3 col-bands.
GRID_A = [
    [4, 4, 2, 4, 4, 2, 4],
    [4, 4, 2, 4, 4, 2, 4],
    [2, 2, 2, 2, 2, 2, 2],
    [4, 4, 2, 4, 4, 2, 4],
    [4, 4, 2, 4, 4, 2, 4],
]

# An 8x5 grid: separator 8 (rows 2 & 5, col 3), content 1. 3 x 2 bands.
GRID_B = [
    [1, 1, 1, 8, 1],
    [1, 1, 1, 8, 1],
    [8, 8, 8, 8, 8],
    [1, 1, 1, 8, 1],
    [1, 1, 1, 8, 1],
    [8, 8, 8, 8, 8],
    [1, 1, 1, 8, 1],
    [1, 1, 1, 8, 1],
]


def test_separator_color_excludes_content():
    # The separator is the minority full-line colour, not the dominant content.
    assert separator_color_of(GRID_A) == 2
    assert most_frequent_color(GRID_A) == 4
    assert separator_color_of(GRID_B) == 8
    assert most_frequent_color(GRID_B) == 1


def test_partition_bands_counts_regions():
    assert partition_bands_of(GRID_A) == (2, 3)
    assert partition_bands_of(GRID_B) == (3, 2)


def test_partition_bands_abstains_without_separator():
    # A plain grid with a single small object and no full separator line.
    plain = [
        [0, 0, 0, 0],
        [0, 3, 3, 0],
        [0, 0, 0, 0],
    ]
    assert separator_color_of(plain) is None
    assert partition_bands_of(plain) is None


def test_partition_bands_abstains_on_ambiguous_separator():
    # Two distinct non-content colours each form a full row -> ambiguous.
    amb = [
        [7, 7, 7],
        [4, 4, 4],
        [4, 4, 4],
        [2, 2, 2],
    ]
    # content here is 4; both 7 and 2 are full-line non-content colours.
    assert most_frequent_color(amb) == 4
    assert separator_color_of(amb) is None
    assert partition_bands_of(amb) is None


def test_analyzer_learns_partition_bands():
    out_a = [[4, 4, 4], [4, 4, 4]]            # 2x3 fill 4
    out_b = [[1, 1], [1, 1], [1, 1]]          # 3x2 fill 1
    sz = analyze_object_size_grid([_pair(GRID_A, out_a), _pair(GRID_B, out_b)])
    assert sz["dim_property"] == "partition_bands"
    assert sz["solid_output_all"] is True
    assert sz["color_preserved_all"] is True
    # No single-object subject: the dimension is read off the grid structure.
    assert sz["selector"] is None


def test_partition_reading_is_grid_level_rect_vocab():
    assert "partition_bands" in GRID_RECT_DIM_VOCAB
    assert GRID_RECT_DIM_VOCAB["partition_bands"] is partition_bands_of


def test_render_round_trip_on_partition_grid():
    # The render path the predict operator runs: read bands + content off the
    # test input, fill a solid rect via the frozen make_grid primitive.
    h, w = partition_bands_of(GRID_A)
    color = most_frequent_color(GRID_A)
    grid = render_solid_rect(h, w, color)
    assert grid == [[4, 4, 4], [4, 4, 4]]


def test_partition_does_not_fire_on_square_object_task():
    # A genuine per-object square task must keep resolving to its scalar property,
    # not the partition reading (which abstains with no separator line).
    inp = [
        [0, 0, 0, 0],
        [0, 5, 5, 0],
        [0, 5, 5, 0],
        [0, 0, 0, 0],
    ]
    out = [[5, 5], [5, 5]]
    sz = analyze_object_size_grid([_pair(inp, out), _pair(inp, out)])
    assert sz["dim_property"] != "partition_bands"
