"""
pair_grid_count_majority — recognise the Slice-1 PAIR-level majority-vote step.

This is the *recognition* half of the §3 PAIR-level pairwise comparison
(arbor-flow raw prose, easy000a paragraph; SLICE_1_LOOP.md §3):

    Inter-Pair, Pair-level on grid-count, pairwise (P6):
        compare(P0, P1) -> COMM (both 2)
        compare(P0, Pa) -> DIFF (2 vs 1)
        compare(P1, Pa) -> DIFF (2 vs 1)
    => "grid-count 다수결 2 vs Pa 의 1"  (a majority agree on grid_count;
       one pair dissents — so it is the one whose output must be constructed).

It consumes `pair_grid_count_comparisons`, the only `build_patterns` producer
(agent/compare_scheduler.py) that previously had no recognition matcher: the
three siblings cover the GRID-decider (`all_outputs_comm`), the GRID-Intra step
(`intra_pair_grids_differ`), and the PAIR count-census trigger
(`test_output_missing` <- `pair_grid_counts`). This matcher pairs the remaining
producer with a consumer, so every comparison family module C schedules now has
a named recogniser (module-uniformity, SLICE_1_LOOP.md §8 criterion 2).

It is the *comparison-receipt* counterpart to `test_output_missing`, which reads
the raw count census. They name the same §3 fact from the two representations §3
lists side by side: the census ("examples 2, test 1") and the pairwise verdicts
("consensus COMM among the complete pairs, DIFF for the dissenter"). Neither
subsumes the other — this one asserts the consensus/dissent *structure* without
committing to specific counts or roles; `test_output_missing` asserts the exact
2-vs-1 counts. Like `intra_pair_grids_differ`, this is a flow-step recogniser,
not the deciding comparison (that is `all_outputs_comm` at GRID level).

Strictly **value-agnostic** (SLICE_1_LOOP.md §9): it inspects only the COMM/DIFF
*type* of each comparison receipt, never an underlying colour, coordinate, or
even the grid_count *value*. It therefore fires identically for easy000a and
easy000a2 and can never hard-code an answer.
"""

from agent.conditions import register


def _result_of(receipt):
    """Return the inner result dict of a compare() receipt (or the receipt
    itself if it is already a bare result). Mirrors the sibling matchers."""
    if not isinstance(receipt, dict):
        return None
    if "result" in receipt and isinstance(receipt["result"], dict):
        return receipt["result"]
    if "type" in receipt:
        return receipt
    return None


def _verdict(result, required_properties):
    """Return "COMM" / "DIFF" for one comparison result, or None if malformed.

    With `required_properties` given, the verdict is COMM iff every named
    property in the receipt's `category` is COMM (else DIFF) — letting a caller
    judge on grid_count alone while tolerating extra properties. Without it, the
    receipt's overall `type` is used (for a PAIR comparison that is exactly the
    grid_count verdict, since a PAIR's only property is grid_count).
    """
    if not isinstance(result, dict):
        return None
    if required_properties:
        category = result.get("category") or {}
        for prop in required_properties:
            entry = category.get(prop)
            if not isinstance(entry, dict) or entry.get("type") not in ("COMM", "DIFF"):
                return None
            if entry.get("type") != "COMM":
                return "DIFF"
        return "COMM"
    t = result.get("type")
    return t if t in ("COMM", "DIFF") else None


@register("pair_grid_count_majority")
def match(patterns: dict, params: dict) -> bool:
    """True iff the pairwise PAIR grid_count comparisons show consensus AND
    dissent — at least one COMM and at least one DIFF (value-agnostic).

    patterns:
      pair_grid_count_comparisons : list of compare() receipts between every
                                    pair (examples + test), 2-at-a-time on the
                                    single PAIR property grid_count (Inter-Pair,
                                    Pair-level).
    params:
      min_evidence       : minimum number of well-formed receipts required
                           (default 2 — a consensus AND a dissent need at least
                           two comparisons, which in turn needs >= 3 pairs, i.e.
                           >= 2 examples + the test; one example + test alone
                           yields a single DIFF receipt and must not fire).
      required_properties : optional list of property names judged per receipt
                            (e.g. ["grid_count"]). If absent, the overall
                            COMM/DIFF type of each receipt is used.

    Fail-closed: a non-list payload, fewer than `min_evidence` well-formed
    receipts, or an all-COMM / all-DIFF set all return False — consensus *with*
    a dissenter is the whole point, so neither extreme qualifies.
    """
    receipts = patterns.get("pair_grid_count_comparisons") or []
    if not isinstance(receipts, (list, tuple)):
        return False

    min_evidence = params.get("min_evidence", 2)
    required_properties = params.get("required_properties")

    verdicts = [_verdict(_result_of(r), required_properties) for r in receipts]
    verdicts = [v for v in verdicts if v is not None]

    if len(verdicts) < min_evidence:
        return False

    has_comm = any(v == "COMM" for v in verdicts)
    has_diff = any(v == "DIFF" for v in verdicts)
    return has_comm and has_diff
