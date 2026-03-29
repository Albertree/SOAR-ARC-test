"""component_size_recolor — recolor connected components by size rank (largest=1, next=2, ...)."""

from procedural_memory.base_rules._helpers import find_components

RULE_TYPE = "component_size_recolor"
CATEGORY = "detect"


def _get_components_and_sizes(grid, color):
    """Get connected components and their sizes for a given color."""
    comps = find_components(grid, color)
    return comps


def try_rule(patterns, task):
    """Detect: one color's components are recolored by size rank in the output."""
    if not task or not task.example_pairs:
        return None

    for pair in task.example_pairs:
        g0 = pair.input_grid
        g1 = pair.output_grid
        if g0 is None or g1 is None:
            return None
        if g0.height != g1.height or g0.width != g1.width:
            return None

    # Find a source color that exists in input but not output
    from collections import Counter
    first_in = task.example_pairs[0].input_grid.raw
    first_out = task.example_pairs[0].output_grid.raw
    h = len(first_in)
    w = len(first_in[0]) if first_in else 0

    in_colors = set()
    out_colors = set()
    for r in range(h):
        for c in range(w):
            in_colors.add(first_in[r][c])
            out_colors.add(first_out[r][c])

    # Source color: present in input, absent in output
    candidates = in_colors - out_colors
    # Filter out background (most common color)
    bg_counts = Counter()
    for row in first_in:
        for v in row:
            bg_counts[v] += 1
    bg_color = bg_counts.most_common(1)[0][0]
    candidates.discard(bg_color)

    if not candidates:
        return None

    for src_color in candidates:
        # Find components in first input
        comps = _get_components_and_sizes(first_in, src_color)
        if len(comps) < 2:
            continue

        # Get unique sizes sorted descending
        sizes = sorted(set(len(c) for c in comps), reverse=True)
        if len(sizes) < 2:
            continue

        # Build size -> rank color mapping from first output
        size_to_color = {}
        valid = True
        for comp in comps:
            sz = len(comp)
            rank = sizes.index(sz)
            color_idx = rank + 1  # 1-based
            # Check what color this component has in output
            r0, c0 = comp[0]
            out_color = first_out[r0][c0]
            if out_color == bg_color or out_color == src_color:
                valid = False
                break
            if sz in size_to_color:
                if size_to_color[sz] != out_color:
                    valid = False
                    break
            else:
                size_to_color[sz] = out_color

            # Verify all cells of this component have the same output color
            for r, c in comp:
                if first_out[r][c] != out_color:
                    valid = False
                    break
            if not valid:
                break

        if not valid or not size_to_color:
            continue

        # Check that rank ordering matches: larger size -> smaller color number
        sorted_sizes = sorted(size_to_color.keys(), reverse=True)
        expected_colors = list(range(1, len(sorted_sizes) + 1))
        actual_colors = [size_to_color[s] for s in sorted_sizes]
        if actual_colors != expected_colors:
            continue

        # Verify on all other pairs
        all_valid = True
        for pair in task.example_pairs[1:]:
            raw_in = pair.input_grid.raw
            raw_out = pair.output_grid.raw
            p_comps = _get_components_and_sizes(raw_in, src_color)
            if len(p_comps) < 2:
                all_valid = False
                break
            p_sizes = sorted(set(len(c) for c in p_comps), reverse=True)
            for comp in p_comps:
                sz = len(comp)
                rank = p_sizes.index(sz)
                expected_c = rank + 1
                for r, c in comp:
                    if raw_out[r][c] != expected_c:
                        all_valid = False
                        break
                if not all_valid:
                    break
            if not all_valid:
                break

        if all_valid:
            return {
                "type": RULE_TYPE,
                "source_color": src_color,
                "bg_color": bg_color,
                "confidence": 1.0,
            }

    return None


def apply_rule(rule, input_grid):
    """Apply: find components of source color, recolor by size rank."""
    raw = input_grid.raw
    src_color = rule["source_color"]

    comps = _get_components_and_sizes(raw, src_color)
    if not comps:
        return None

    output = [row[:] for row in raw]

    # Rank by unique sizes descending
    sizes = sorted(set(len(c) for c in comps), reverse=True)

    for comp in comps:
        sz = len(comp)
        rank = sizes.index(sz)
        new_color = rank + 1
        for r, c in comp:
            output[r][c] = new_color

    return output
