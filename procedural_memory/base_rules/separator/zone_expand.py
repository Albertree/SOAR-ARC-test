"""zone_expand — marker rows expand to fill Voronoi zones along a spine column."""

from collections import Counter

RULE_TYPE = "zone_expand"
CATEGORY = "separator"


def _find_spine_column(grid, bg):
    """Find the column with the most concentrated non-bg color (the spine)."""
    h = len(grid)
    w = len(grid[0])
    best_col = None
    best_count = 0
    best_color = None

    for c in range(w):
        non_bg = [grid[r][c] for r in range(h) if grid[r][c] != bg]
        if len(non_bg) < h // 2:
            continue
        counts = Counter(non_bg)
        if counts:
            color, count = counts.most_common(1)[0]
            if count > best_count:
                best_count = count
                best_col = c
                best_color = color

    if best_col is not None:
        return best_col, best_color
    return None, None


def _find_markers(grid, spine_col, spine_color, bg):
    """Find marker rows: uniform non-bg color with a different value at the spine."""
    h = len(grid)
    w = len(grid[0])
    markers = []

    for r in range(h):
        if grid[r][spine_col] == spine_color:
            continue  # not a marker row

        non_spine = [grid[r][c] for c in range(w) if c != spine_col]
        unique = set(non_spine)
        if len(unique) == 1:
            marker_color = non_spine[0]
            if marker_color != bg and marker_color != spine_color:
                markers.append((r, marker_color))

    return markers


def _build_output(grid, h, w, spine_col, spine_color, markers, crossing_color):
    """Build the zone-expanded output grid."""
    result = [[0] * w for _ in range(h)]
    marker_set = {r: color for r, color in markers}

    for r in range(h):
        if r in marker_set:
            # Marker row: crossing_color everywhere, spine_color at spine
            for c in range(w):
                result[r][c] = crossing_color if c != spine_col else spine_color
        else:
            # Find nearest marker(s)
            min_dist = h + 1
            nearest_colors = []
            for mr, mc in markers:
                d = abs(r - mr)
                if d < min_dist:
                    min_dist = d
                    nearest_colors = [mc]
                elif d == min_dist:
                    nearest_colors.append(mc)

            unique_nearest = set(nearest_colors)
            if len(unique_nearest) > 1:
                # Tie between different colors → boundary row (all crossing)
                for c in range(w):
                    result[r][c] = crossing_color
            else:
                fill_color = nearest_colors[0]
                for c in range(w):
                    result[r][c] = fill_color if c != spine_col else crossing_color

    return result


def try_rule(patterns, task):
    """Detect: grid with spine column and colored marker rows that expand."""
    pairs = task.example_pairs
    if not pairs:
        return None

    inp0 = pairs[0].input_grid.raw
    h, w = len(inp0), len(inp0[0])

    # Background = most common color
    all_vals = [inp0[r][c] for r in range(h) for c in range(w)]
    bg = Counter(all_vals).most_common(1)[0][0]

    spine_col, spine_color = _find_spine_column(inp0, bg)
    if spine_col is None:
        return None

    markers = _find_markers(inp0, spine_col, spine_color, bg)
    if len(markers) < 2:
        return None

    crossing_color = inp0[markers[0][0]][spine_col]

    # Verify across all training pairs
    for pair in pairs:
        inp = pair.input_grid.raw
        out = pair.output_grid.raw
        ph, pw = len(inp), len(inp[0])

        pall = [inp[r][c] for r in range(ph) for c in range(pw)]
        pbg = Counter(pall).most_common(1)[0][0]
        if pbg != bg:
            return None

        sc, s_color = _find_spine_column(inp, bg)
        if sc is None or s_color != spine_color:
            return None

        mkrs = _find_markers(inp, sc, s_color, bg)
        if len(mkrs) < 2:
            return None

        cc = inp[mkrs[0][0]][sc]
        if cc != crossing_color:
            return None

        result = _build_output(inp, ph, pw, sc, s_color, mkrs, cc)
        if result != out:
            return None

    return {
        "type": RULE_TYPE,
        "spine_color": spine_color,
        "bg": bg,
        "crossing_color": crossing_color,
        "confidence": 1.0,
    }


def apply_rule(rule, input_grid):
    """Apply zone expansion to the input grid."""
    raw = input_grid.raw
    h, w = len(raw), len(raw[0])
    bg = rule["bg"]
    spine_color = rule["spine_color"]
    crossing_color = rule["crossing_color"]

    spine_col, _ = _find_spine_column(raw, bg)
    if spine_col is None:
        return None

    markers = _find_markers(raw, spine_col, spine_color, bg)
    if not markers:
        return None

    return _build_output(raw, h, w, spine_col, spine_color, markers, crossing_color)
