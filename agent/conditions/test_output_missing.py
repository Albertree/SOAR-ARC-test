"""
test_output_missing — recognise the Slice-1 PAIR-level goal-B trigger.

This is the *recognition* half of the §3 PAIR-level step (arbor-flow raw prose,
easy000a paragraph; SLICE_1_LOOP.md §3):

    The example pairs each carry two grids (input + output); the test pair
    carries only one (input). Comparing pair grid_counts pairwise yields a clear
    minority — the test pair is the one whose output must be *constructed*. That
    asymmetry is what sets goal B ("make Pa's missing output grid") and drives
    the descent to GRID level.

It is the PAIR-level counterpart to `all_outputs_comm` (which decides at GRID
level). Together they name the two recognition steps Slice 1 leans on:
  · test_output_missing : "this is a construct-the-output task"  (PAIR level)
  · all_outputs_comm    : "the output is the common example G1"  (GRID level)

Strictly **value-agnostic** (SLICE_1_LOOP.md §9): it inspects only structural
grid *counts*, never a colour or coordinate value. It therefore fires
identically for easy000a and easy000a2 and can never hard-code an answer.

Produced by `agent/compare_scheduler.py:pair_grid_counts()`.
"""

from agent.conditions import register


def _all_ints(values):
    """True iff `values` is a non-empty list of plain ints (bool rejected)."""
    if not isinstance(values, (list, tuple)) or not values:
        return False
    return all(isinstance(v, int) and not isinstance(v, bool) for v in values)


@register("test_output_missing")
def match(patterns: dict, params: dict) -> bool:
    """True iff every example pair is complete and every test pair lacks output.

    patterns:
      pair_grid_counts : {"example_counts": [int, ...],
                          "test_counts":    [int, ...]}
                         Structural grid-count census (value-agnostic).
    params:
      min_evidence : minimum number of example pairs required (default 1).
                     Guards against firing on a degenerate task with no
                     example evidence.

    Fires iff (fail-closed on anything malformed):
      · there are >= min_evidence example pairs, each with grid_count == 2
        (a complete input+output pair), AND
      · there is >= 1 test pair, every one with grid_count == 1
        (input only — its output is what we must construct).
    """
    census = patterns.get("pair_grid_counts")
    if not isinstance(census, dict):
        return False

    example_counts = census.get("example_counts")
    test_counts = census.get("test_counts")
    if not _all_ints(example_counts) or not _all_ints(test_counts):
        return False

    min_evidence = params.get("min_evidence", 1)
    if len(example_counts) < min_evidence:
        return False

    if not all(c == 2 for c in example_counts):
        return False
    if not all(c == 1 for c in test_counts):
        return False

    return True
