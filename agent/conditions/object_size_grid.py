"""
object_size_grid — recognition matcher for the §2.1 "grid size is a function of
an object's property" concept (BACKLOG_LOOP.md R1, madeup phase).

The orthogonal sibling of the object-move matchers. Those all *keep* the object's
shape and key on *where* it lands (constant target/offset/corner/resize). This
one fires for the converse axis: the output is a **solid square** whose side is a
*scalar property of an input object* (its cell-count) and whose colour is the
object's colour. The learned argument is the *property expression* feeding the
frozen `make_grid` dimension (`size_of(unique_object(in))`), not a literal — so
the rule stays value-agnostic in the object's colour, size, shape and position.

It abstains unless the analysis (agent/dsl_expr/selection.analyze_object_size_grid)
found a consistent dimension property across every pair, the output is a solid
square in every pair, and the output colour matches the object's colour — keeping
it disjoint from the move readings (whose outputs are not solid fills). Adding a
matcher grows the *recognition* vocabulary only (P5); it introduces no new
transformation (F3-exempt).
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
    # `single_object_all` is *not* required: the dimension property may be a
    # grid-level one (object_count) whose subject is the object *set*, not one
    # object (§2.1 "object count ≠ 1"). A learned dim_property already implies the
    # right subject was found and is consistent; solid-square output + the colour
    # COMM keep this disjoint from the move readings (whose outputs are not solid
    # fills), so dropping the single-object gate widens the family without
    # bleeding into the move families.
    if not (sz.get("solid_output_all")
            and sz.get("color_preserved_all")):
        return False
    return len(sz.get("per_pair") or []) >= min_evidence
