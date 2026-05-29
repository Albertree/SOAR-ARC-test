"""
intra_pair_grids_differ — recognise the Slice-1 Intra-Pair (Grid-level) step.

This is the *recognition* half of the §3 ① step (arbor-flow raw prose, easy000a
paragraph; SLICE_1_LOOP.md §3 ①, §5):

    Within one pair, the two sibling grids are the input (G0) and the output
    (G1). Comparing them (Intra-Pair, Grid-level) yields DIFF — the output
    differs from the input. On its own this is *info-poor* (it does not by
    itself say what the output should be), but the intended flow passes through
    it before the deciding Inter-Grid comparison ("당위: 그래도 흐름상 거쳐감").

It is the **Intra** counterpart to `all_outputs_comm` (the **Inter** decider).
Together they name the two GRID-level analysis kinds of module C's contract
(SLICE_1_LOOP.md §5 — exactly two kinds, Intra-/Inter-[Level]):
  · intra_pair_grids_differ : "input and output differ within a pair"  (Intra)
  · all_outputs_comm        : "the example outputs are all common"      (Inter)

Strictly **value-agnostic** (SLICE_1_LOOP.md §9): it inspects only the COMM/DIFF
*type* of each comparison receipt, never an underlying colour or coordinate
value. It therefore fires identically for easy000a (red) and easy000a2 (green)
and can never hard-code an answer.

The receipts are produced by
`agent/compare_scheduler.py:intra_pair_grid_comparisons()`.
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


@register("intra_pair_grids_differ")
def match(patterns: dict, params: dict) -> bool:
    """True iff every intra-pair (G0↔G1) comparison is DIFF (value-agnostic).

    patterns:
      intra_pair_grid_comparisons : list of compare() receipts between each
                                    example pair's sibling grids (Intra-Pair,
                                    Grid-level).
    params:
      min_evidence       : minimum number of receipts required (default 1).
                           Guards against firing on zero comparisons — DIFF
                           cannot be concluded from nothing.
      required_properties: optional list of property names that must each be
                           DIFF. If absent, the overall COMM/DIFF type of each
                           receipt is used.
    """
    receipts = patterns.get("intra_pair_grid_comparisons") or []
    if not isinstance(receipts, (list, tuple)):
        return False

    min_evidence = params.get("min_evidence", 1)
    required_properties = params.get("required_properties")

    results = [_result_of(r) for r in receipts]
    results = [r for r in results if r is not None]

    if len(results) < min_evidence:
        return False

    return all(_is_diff(r, required_properties) for r in results)
