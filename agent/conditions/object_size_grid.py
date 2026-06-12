"""
object_size_grid — recognition matcher for the §2.1 "grid size is a function of
an object's property" concept (BACKLOG_LOOP.md R1, madeup phase).

The orthogonal sibling of the object-move matchers. Those all *keep* the object's
shape and key on *where* it lands (constant target/offset/corner/resize). This
one fires for the converse axis: the output is a **solid fill** whose dimensions
are a *property of an input object* and whose colour is the object's colour. The
learned argument is the *property expression* feeding the frozen `make_grid`
dimension(s) — a scalar reading sizes a *square* (`size_of(unique_object(in))`),
the rectangular reading sizes an `h × w` *rectangle* (`bbox_extent(unique_object
(in))`, the §2.1 non-square case) — not a literal, so the rule stays
value-agnostic in the object's colour, size, shape and position.

It abstains unless the analysis (agent/dsl_expr/selection.analyze_object_size_grid)
found a consistent dimension reading across every pair, the output is a solid
fill in every pair, and the output colour matches the object's colour — keeping
it disjoint from the move readings (whose outputs are not solid fills). The output
need no longer be *square*: the analysis re-imposes squareness per scalar reading
and only the rectangular `bbox_extent` reading admits `h ≠ w`, so widening the
matcher to solid (not solid-square) fills does not bleed into the scalar readings.
Adding a matcher grows the *recognition* vocabulary only (P5); it introduces no
new transformation (F3-exempt).
"""

from agent.conditions import register


@register("object_size_grid")
def object_size_grid(patterns: dict, params: dict | None = None) -> bool:
    """True iff every example renders a solid square whose side equals a learned
    scalar property of the single input object and whose colour is that object's
    colour, with enough evidence.

    `params.min_evidence` (default 2) guards against firing on a single pair —
    one example cannot establish that the dimension *property* (rather than a
    coincidental constant size) drives the output.
    """
    if not isinstance(patterns, dict):
        return False
    params = params or {}
    min_evidence = params.get("min_evidence", 2)

    sz = patterns.get("object_size_grid")
    if not isinstance(sz, dict):
        return False
    if sz.get("dim_property") is None:
        return False
    # `single_object_all` is *not* required: the analysis admits three subject
    # forms for the dimension property (§2.5-2b "which subject feeds the dimension
    # argument" axis) — (1) the single object (per-object property), (2) the object
    # *set* (a grid-level property such as object_count, §2.1 "object count ≠ 1"),
    # and (3) a *selected* object among several (`size_of(max_size(objects(in)))`,
    # carried by `sz["selector"]`). A learned dim_property already implies one of
    # these subjects was found and is consistent across every pair; solid-square
    # output + the colour COMM (grounded on whichever subject won) keep this
    # disjoint from the move readings (whose outputs are not solid fills), so
    # admitting the extra subjects widens the family without bleeding into the move
    # families.
    if not (sz.get("solid_output_all")
            and sz.get("color_preserved_all")):
        return False
    return len(sz.get("per_pair") or []) >= min_evidence
