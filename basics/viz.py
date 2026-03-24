"""
viz.py — ANSI color-based KG component visualization utility.
Original color palette: ARC-solver/basics/utils.py  color_text()
Original output method: ARC-solver/basics/utils.py  print_multiple_grids / print_task_view

Design principles (same as original):
  - No labels, separators, indices, or other text
  - Only ANSI color blocks are output
  - When placing multiple grids side by side, only fixed spaces (gap) are inserted between them

Public functions:
    show_task(task)             — Visualize entire task (example + test)
    show_objects(grid)          — Display detected objects from Grid (5 columns)
    show_comparison(a, b)       — Side-by-side comparison of two components (Grid / Object / Pixel)
"""

# ---------------------------------------------------------------------------
# ANSI color palette (original: ARC-solver/basics/utils.py)
# ---------------------------------------------------------------------------

_PALETTE = {
    0:  (0,   0,   0),
    1:  (0,   116, 217),
    2:  (255, 65,  54),
    3:  (46,  204, 64),
    4:  (255, 220, 0),
    5:  (170, 170, 170),
    6:  (240, 18,  190),
    7:  (255, 133, 27),
    8:  (127, 219, 255),
    9:  (135, 12,  37),
    10: (128, 0,   128),
    11: (0,   128, 128),
    12: (101, 67,  33),
    13: (214, 255, 255),
    14: (79,  79,  79),
}
_FALLBACK = (180, 180, 180)


def _cell(color: int) -> str:
    """Single cell → 2-character ANSI background color block."""
    r, g, b = _PALETTE.get(color, _FALLBACK)
    return f"\033[48;2;{r};{g};{b}m  \033[0m"


def _render_row(row: list) -> str:
    """Single row of int list → ANSI string."""
    return "".join(_cell(v) for v in row)


def _blank_row(cols: int) -> str:
    """Empty whitespace row of cols-cell width (for padding grids of different heights)."""
    return " " * (cols * 2)


# ---------------------------------------------------------------------------
# Core output helper (same approach as original print_multiple_grids)
# ---------------------------------------------------------------------------

def _print_side_by_side(grids: list, gap: int = 4):
    """
    Print multiple 2D int arrays side by side.
    Same approach as original print_multiple_grids:
      - No labels or separators
      - Join ANSI strings per row with gap whitespace
      - Shorter grids are padded with blank spaces

    Args:
        grids: list of 2D int arrays
        gap:   number of whitespace characters between grids
    """
    if not grids:
        return
    sep = " " * gap
    cols = [len(g[0]) if g and g[0] else 0 for g in grids]
    max_h = max((len(g) for g in grids if g), default=0)

    for row_idx in range(max_h):
        parts = []
        for grid, w in zip(grids, cols):
            if row_idx < len(grid):
                parts.append(_render_row(grid[row_idx]))
            else:
                parts.append(_blank_row(w))
        print(sep.join(parts))


def _extract_raw(component) -> list:
    """
    Extract 2D int array from Grid / Object / Pixel component.
      Grid  → raw
      Object → colorgrid  (transparent=13)
      Pixel  → [[color]]
    """
    if hasattr(component, "raw"):
        return component.raw
    if hasattr(component, "colorgrid"):
        return component.colorgrid
    if hasattr(component, "color"):
        return [[component.color]]
    return []


# ---------------------------------------------------------------------------
# Public function 1: show_task
# ---------------------------------------------------------------------------

def show_task(task, gap: int = 6):
    """
    Visualize the entire task.
    Example pair: input (left) and output (right) placed side by side, blank line between pairs.
    Test pair:    only input is displayed.

    Same approach as original print_task_view.
    """
    for i, pair in enumerate(task.example_pairs):
        if i > 0:
            print()
        grids = [pair.input_grid.raw]
        if pair.output_grid is not None:
            grids.append(pair.output_grid.raw)
        _print_side_by_side(grids, gap=gap)

    if task.example_pairs:
        print()

    for pair in task.test_pairs:
        _print_side_by_side([pair.input_grid.raw], gap=gap)


# ---------------------------------------------------------------------------
# Public function 2: show_objects
# ---------------------------------------------------------------------------

def show_objects(grid, cols_per_row: int = 5, gap: int = 3):
    """
    Display detected objects from Grid, placing cols_per_row per line side by side.
    Each object is shown as colorgrid (bbox size, transparent=dark gray).
    """
    objects = getattr(grid, "objects", [])
    if not objects:
        return

    for batch_start in range(0, len(objects), cols_per_row):
        batch = objects[batch_start: batch_start + cols_per_row]
        _print_side_by_side([obj.colorgrid for obj in batch], gap=gap)
        print()


# ---------------------------------------------------------------------------
# Public function 3: show_comparison
# ---------------------------------------------------------------------------

def show_comparison(a, b, gap: int = 6):
    """
    Print two components (Grid / Object / Pixel) side by side.
    Used for debugging comparisons.
    """
    raw_a = _extract_raw(a)
    raw_b = _extract_raw(b)
    if not raw_a and not raw_b:
        return
    _print_side_by_side([raw_a, raw_b], gap=gap)
