"""
all_outputs_comm — recognise the Slice-1 deciding signal.

This is the *recognition* half of the intended easy000a / easy000a2 mechanism
(SLICE_1_LOOP.md §3, §8; arbor-flow raw prose, easy000a paragraph):

    Every example output grid (G1) is identical, so a role-aligned Inter-Grid
    comparison of the example G1s is COMM on every property
    {size, color, contents}. When that holds, the test output is the *common*
    G1 — copied, not computed. (G0/input is irrelevant in this slice because
    the output is fixed.)

The matcher consumes the comparison *receipts* produced by ARCKG.compare()
(ARCKG/comparison.py): a receipt is `{"id": ..., "result": {"type": "COMM"|
"DIFF", "score": "n/total", "category": {...}}}`, or just the inner `result`
dict.

It is strictly **value-agnostic** (SLICE_1_LOOP.md §9): it only ever looks at
the COMM/DIFF *type* of each comparison, never at the underlying colour or
coordinate values. So it fires identically for easy000a (fixed red output) and
easy000a2 (fixed green output) — it cannot hard-code an answer.
"""

from agent.conditions import register


def _result_of(receipt):
    """Return the inner result dict of a compare() receipt (or the receipt
    itself if it is already a bare result)."""
    if not isinstance(receipt, dict):
        return None
    if "result" in receipt and isinstance(receipt["result"], dict):
        return receipt["result"]
    if "type" in receipt:
        return receipt
    return None


def _is_comm(result, required_properties):
    """COMM verdict for one comparison result.

    With `required_properties` given, every named property in the receipt's
    `category` must be COMM (overall type ignored — lets a caller demand only
    {size, color, contents} while tolerating extra properties). Without it,
    the overall `type` must be COMM.
    """
    if not isinstance(result, dict):
        return False
    if required_properties:
        category = result.get("category") or {}
        for prop in required_properties:
            entry = category.get(prop)
            if not isinstance(entry, dict) or entry.get("type") != "COMM":
                return False
        return True
    return result.get("type") == "COMM"


@register("all_outputs_comm")
def match(patterns: dict, params: dict) -> bool:
    """True iff all example-output comparisons are COMM (value-agnostic).

    patterns:
      output_grid_comparisons : list of compare() receipts between example
                                output grids (role-aligned Inter-Grid, role==G1).
    params:
      min_evidence       : minimum number of receipts required (default 1).
                           Guards against firing on zero comparisons.
      required_properties: optional list of property names that must each be
                           COMM (e.g. ["size", "color", "contents"]). If absent,
                           the overall COMM/DIFF type of each receipt is used.
    """
    receipts = patterns.get("output_grid_comparisons") or []
    if not isinstance(receipts, (list, tuple)):
        return False

    min_evidence = params.get("min_evidence", 1)
    required_properties = params.get("required_properties")

    results = [_result_of(r) for r in receipts]
    results = [r for r in results if r is not None]

    if len(results) < min_evidence:
        return False

    return all(_is_comm(r, required_properties) for r in results)
