"""
object_extract — crop-to-object matcher (BACKLOG_LOOP.md §2.5-1 on the extract
axis: the output is the minimal subgrid bounding *one selected object*, drawn by
the frozen `coloring` primitive applied at each cell of that bbox window on a
`make_grid` canvas — a selection+crop expression, not a new `crop` primitive).

Fires when a single named selector from `SELECTOR_VOCAB` (max_size / min_size /
unique_color / unique_shape / border_object) picks, in *every* example, the
object whose inclusive bounding-box subgrid equals the output exactly, with at
least one pair a genuine crop (output strictly smaller than input). The selector
name is the lifted *argument* — value-, colour-, shape- and size-agnostic — and
is recomputed per test input (P5), so one value-agnostic rule covers the whole
extract family rather than one literal rule per task (the §2.5-3/4 "covers, not
accretion" shape). The §2.5-2b selection lift is the entire content of the rule:
*which* object the crop window is drawn around. Reads the `object_extract` signal
surfaced by ExtractPatternOperator (computed by
agent/dsl_expr/selection.analyze_object_extract), which already verified the
selected object's bbox crop against the COMM between predicted and actual outputs
(P3/P4: grounded in comparison, never assumed).

Stays inert (selector None) whenever no single selector reproduces all pairs with
a genuine crop — in particular on every same-size task and every task whose output
is not exactly one object's bounding box — so it never perturbs the move / recolor
/ sizing / geometric / scale / symmetry-repair families.
"""

from agent.conditions import register


@register("object_extract")
def object_extract(patterns: dict, params: dict | None = None) -> bool:
    """True iff one selector's chosen-object bbox crop reproduces every example
    output (a genuine object extraction) with enough evidence.

    `params.min_evidence` (default 2) guards against committing to a selector from
    a single pair — one pair cannot establish that the selector names the *same*
    object role across the family rather than coincidentally fitting once.
    """
    if not isinstance(patterns, dict):
        return False
    params = params or {}
    min_evidence = params.get("min_evidence", 2)

    sig = patterns.get("object_extract")
    if not isinstance(sig, dict):
        return False
    if not sig.get("valid_all"):
        return False
    if sig.get("selector") is None:
        return False
    return int(sig.get("evidence", 0)) >= min_evidence
