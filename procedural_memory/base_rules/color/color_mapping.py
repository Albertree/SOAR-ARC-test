"""color_mapping -- each input color consistently maps to one output color."""

RULE_TYPE = "color_mapping"
CATEGORY = "color"


def try_rule(patterns, task):
    """Detect pattern: each input color maps to exactly one output color."""
    pair_analyses = patterns.get("pair_analyses", [])
    if not pair_analyses or not patterns.get("grid_size_preserved"):
        return None

    color_map = {}
    for analysis in pair_analyses:
        for group in analysis["groups"]:
            for ic in group["input_colors"]:
                for oc in group["output_colors"]:
                    if ic not in color_map:
                        color_map[ic] = set()
                    color_map[ic].add(oc)

    simple_map = {}
    for ic, ocs in color_map.items():
        if len(ocs) != 1:
            return None
        simple_map[ic] = list(ocs)[0]

    if simple_map:
        return {
            "type": RULE_TYPE,
            "mapping": simple_map,
            "confidence": 0.8,
        }

    return None


def apply_rule(rule, input_grid):
    """Apply color_mapping rule to input grid."""
    raw = input_grid.raw
    mapping = rule.get("mapping", {})

    output = []
    for row in raw:
        output.append([mapping.get(cell, cell) for cell in row])
    return output
