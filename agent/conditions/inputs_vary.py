"""
inputs_vary — recognise the Slice-1 Inter-Grid (role==G0) contrast step.

This is the *recognition* half of the role==G0 limb of §3's "② Inter-Grid,
Grid-level (role-aligned)" step (arbor-flow raw prose, easy000a paragraph;
SLICE_1_LOOP.md §3 line 119):

    The example *input* grids (G0), compared role-aligned across pairs, are
    DIFF — "색집합이 모두 다르다" (their colour sets all differ). On its own this
    does not say what the output is; the intended flow traverses it as the
    *contrast* to the outputs. It is exactly because the inputs DIFF while the
    outputs are COMM that the answer is read off the (invariant) outputs and
    not the (varying) inputs.

It is the role==G0 counterpart to `all_outputs_comm` (role==G1). Together they
name *both* roles of module C's single Inter-Grid (Grid-level) analysis kind
(SLICE_1_LOOP.md §5):
  · all_outputs_comm : "the example outputs are all common"   (Inter, role==G1)
  · inputs_vary      : "the example inputs all differ"        (Inter, role==G0)

Strictly **value-agnostic** (SLICE_1_LOOP.md §9): it inspects only the COMM/DIFF
*type* of each comparison receipt, never an underlying colour or coordinate
value. It therefore fires identically for easy000a (red) and easy000a2 (green)
and can never hard-code an answer.

The receipts are produced by
`agent/compare_scheduler.py:input_grid_comparisons()`.
"""

from agent.conditions import register


def _result_of(receipt):
    """Return the inner result dict of a compare() receipt (or the receipt
    itself if it is already a bare result). Mirrors `all_outputs_comm`."""
    if not isinstance(receipt, dict):
        return None
    if "result" in receipt and isinstance(receipt["result"], dict):
        return receipt["result"]
    if "type" in receipt:
        return receipt
    return None


def _is_diff(result, required_properties):
    """DIFF verdict for one comparison result.

    With `required_properties` given, every named property in the receipt's
    `category` must be DIFF (lets a caller demand specific properties differ
    while tolerating others). Without it, the overall `type` must be DIFF.
    """
    if not isinstance(result, dict):
        return False
    if required_properties:
        category = result.get("category") or {}
        for prop in required_properties:
            entry = category.get(prop)
            if not isinstance(entry, dict) or entry.get("type") != "DIFF":
                return False
        return True
    return result.get("type") == "DIFF"


@register("inputs_vary")
def match(patterns: dict, params: dict) -> bool:
    """True iff every example-input comparison is DIFF (value-agnostic).

    patterns:
      input_grid_comparisons : list of compare() receipts between example input
                               grids (role-aligned Inter-Grid, role==G0).
    params:
      min_evidence       : minimum number of receipts required (default 1).
                           Guards against firing on zero comparisons — DIFF
                           cannot be concluded from nothing.
      required_properties: optional list of property names that must each be
                           DIFF. If absent, the overall COMM/DIFF type of each
                           receipt is used.
    """
    receipts = patterns.get("input_grid_comparisons") or []
    if not isinstance(receipts, (list, tuple)):
        return False

    min_evidence = params.get("min_evidence", 1)
    required_properties = params.get("required_properties")

    results = [_result_of(r) for r in receipts]
    results = [r for r in results if r is not None]

    if len(results) < min_evidence:
        return False

    return all(_is_diff(r, required_properties) for r in results)
