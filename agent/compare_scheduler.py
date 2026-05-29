"""
compare_scheduler — module C (RecursiveComparisonController), Slice-1 scope.

SLICE_1_LOOP.md §5 redefines module C as exactly **two analysis kinds**
(Intra-/Inter-[Level]) plus a **scope selector** — *not* the old 7-rule list.
This file is the smallest honest realisation of that definition for Slice 1:

    scope  = select(anchor, level, predicate?)
           = filter( elements-at(anchor, level), predicate )
    compare(scope_A, scope_B)            # always N:N; 1:1 is N==1
           reuses ARCKG/comparison.py:compare() (SLICE_1_LOOP.md §5)

Two analysis kinds, both produced here for Slice 1:
  · Inter-Grid (Grid-level, role==G1): the *deciding* comparison of easy000a —
    role-aligned example output grids compared pairwise (P6: 2-at-a-time). When
    every receipt is COMM on {size, color, contents}, the test output is the
    common G1 (copied, not computed). This is exactly the data the iter-2
    `all_outputs_comm` matcher consumes — before this file it had no producer.
  · Inter-Pair (Pair-level, grid_count): the PAIR-level evidence of §3 — pairs
    compared pairwise on grid_count. Examples carry 2 grids, the test pair 1;
    that asymmetry is the §3 goal-B trigger ("construct Pa's missing output"),
    recognised value-agnostically by the `test_output_missing` matcher.

Everything here is **value-agnostic** (SLICE_1_LOOP.md §9): it schedules and
compares; it never reads a colour or coordinate *value* to decide anything. The
COMM/DIFF verdicts come straight from ARCKG.compare().

This is a library (module C). Wiring it into the SOAR pipeline operators and the
value-agnostic predict step (PredictByAllPairCommOp / module K) is a later
iter's smallest step; this iter only builds the producer + recognition chain so
the previously-dead `all_outputs_comm` matcher becomes live.
"""

from itertools import combinations

from ARCKG.comparison import compare as arckg_compare


# ----------------------------------------------------------------------
# Module D building blocks (util) — functional wrappers over the existing
# ARCKG node structure. They *expose* structure; they never recompute a
# property value (SLICE_1_LOOP.md §6: "값 재계산 ✗, 노출 ○").
# ----------------------------------------------------------------------

def pairs_of(task):
    """All pairs under a task: example pairs then test pairs."""
    return list(task.example_pairs) + list(task.test_pairs)


def grids_of(pair):
    """Grids under a pair, in role order: [input] or [input, output]."""
    grids = []
    if pair.input_grid is not None:
        grids.append(pair.input_grid)
    if pair.output_grid is not None:
        grids.append(pair.output_grid)
    return grids


def role_of(grid):
    """Role of a grid from its node id suffix: 'G0' (input) | 'G1' (output).

    Returns the raw role tag rather than recomputing input/output identity, so
    the caller stays decoupled from how pairs store their grids.
    """
    node_id = getattr(grid, "node_id", "") or ""
    tail = node_id.rsplit(".", 1)[-1]
    return tail if tail.startswith("G") else None


def filter_scope(elements, predicate=None):
    """Scope selector's filter step: keep elements satisfying predicate.

    predicate is None -> identity (the whole scope), matching §5's "생략 시 전체".
    """
    if predicate is None:
        return list(elements)
    return [e for e in elements if predicate(e)]


# ----------------------------------------------------------------------
# Scope selector — select(anchor, level, predicate?)  (SLICE_1_LOOP.md §5)
# ----------------------------------------------------------------------

def select(anchor, level, predicate=None):
    """Return the scope = filter( elements-at(anchor, level), predicate ).

    Slice-1 levels:
      level == "pair":  anchor is a task -> its pairs
      level == "grid":  anchor is a pair -> its grids
    """
    if level == "pair":
        elements = pairs_of(anchor)
    elif level == "grid":
        elements = grids_of(anchor)
    else:
        raise ValueError(f"unsupported scope level for Slice 1: {level!r}")
    return filter_scope(elements, predicate)


# ----------------------------------------------------------------------
# Comparison scheduling — pairwise (P6) over a scope, reusing ARCKG.compare
# ----------------------------------------------------------------------

def _compare_pairwise(nodes, compare_fn=None):
    """All 2-at-a-time comparisons over `nodes` (P6: never 3-way)."""
    fn = compare_fn or arckg_compare
    return [fn(a, b) for a, b in combinations(nodes, 2)]


def output_grid_comparisons(task, compare_fn=None):
    """Inter-Grid, role==G1: pairwise comparison of example output grids.

    The deciding comparison of easy000a (SLICE_1_LOOP.md §3). Returns a list of
    ARCKG.compare() receipts; an empty list when there are < 2 example outputs
    (nothing to compare — the matcher then fails its min_evidence guard).
    """
    outputs = [
        p.output_grid
        for p in task.example_pairs
        if p.output_grid is not None and role_of(p.output_grid) == "G1"
    ]
    return _compare_pairwise(outputs, compare_fn)


def input_grid_comparisons(task, compare_fn=None):
    """Inter-Grid, role==G0: pairwise comparison of example *input* grids.

    The role==G0 half of the §3 "② Inter-Grid, Grid-level (role-aligned)" step
    (SLICE_1_LOOP.md §3 line 119: "compare(P0.G0, P1.G0) → 색·위치 DIFF (정답
    기여 안 함)"; raw prose easy000a paragraph: "다른 Pair 의 G0 들을 살펴보면
    … 색집합이 달라 … (색집합이 모두 다르다는 정보)"). It mirrors
    `output_grid_comparisons` (role==G1), completing the Inter-Grid analysis
    kind across *both* roles.

    The flow traverses this comparison but it does **not** contribute the answer
    — its value is the *contrast* it draws with the outputs: in easy000a the
    inputs DIFF while the outputs are COMM, and that contrast is *why* the
    answer is read off the (invariant) outputs and not the (varying) inputs.
    Returns ARCKG.compare() receipts; an empty list when there are < 2 example
    inputs. Value-agnostic: it only schedules and compares, never reading a
    colour or coordinate value. It feeds the `inputs_vary` recognition matcher.
    """
    inputs = [
        p.input_grid
        for p in task.example_pairs
        if p.input_grid is not None and role_of(p.input_grid) == "G0"
    ]
    return _compare_pairwise(inputs, compare_fn)


def intra_pair_grid_comparisons(task, compare_fn=None):
    """Intra-Pair, Grid-level: within each example pair, compare its sibling
    grids (G0 ↔ G1) pairwise (P6: 2-at-a-time).

    The §3 "Intra-Pair, Grid-level" step (SLICE_1_LOOP.md §3 ①; §5 names
    Intra-Pair(Grid-level) as one of the two analysis kinds Slice 1 uses). Each
    example pair holds exactly two sibling grids under one parent, so this yields
    one receipt per complete example pair; that receipt is DIFF for easy000a
    (input and output share size/colour but differ in contents). The test pair
    carries only G0 — no sibling — so it is naturally skipped (combinations over
    a single grid is empty), matching §3's "Pa 는 G0뿐 → 형제 없어 자연 skip".

    This is the **Intra** half of module C's two-analysis-kind contract; the
    previously-implemented producers (`output_grid_comparisons`,
    `pair_grid_count_comparisons`) are both **Inter**. Value-agnostic: it only
    schedules sibling comparisons and returns ARCKG.compare() receipts; it never
    reads a colour or coordinate value to decide anything. It feeds the
    `intra_pair_grids_differ` recognition matcher.
    """
    receipts = []
    for pair in task.example_pairs:
        receipts.extend(_compare_pairwise(grids_of(pair), compare_fn))
    return receipts


def pair_grid_count_comparisons(task, compare_fn=None):
    """Inter-Pair, Pair-level: pairwise comparison of every pair's grid_count.

    The §3 PAIR-level evidence. Compares all pairs (examples + test) 2-at-a-time
    on the single PAIR property (grid_count).
    """
    return _compare_pairwise(pairs_of(task), compare_fn)


def pair_grid_counts(task):
    """Structural grid-count census, split by role (value-agnostic counts only).

    {"example_counts": [...], "test_counts": [...]} — the evidence the
    `test_output_missing` matcher consumes to recognise the construct-the-output
    regime (examples complete, test missing its output).
    """
    return {
        "example_counts": [p.to_json()["grid_count"] for p in task.example_pairs],
        "test_counts": [p.to_json()["grid_count"] for p in task.test_pairs],
    }


def build_patterns(task, compare_fn=None):
    """Assemble the Slice-1 `patterns` dict consumed by the condition matchers.

    Keys:
      output_grid_comparisons      -> all_outputs_comm       (GRID-level, Inter, role==G1)
      input_grid_comparisons       -> inputs_vary            (GRID-level, Inter, role==G0)
      intra_pair_grid_comparisons  -> intra_pair_grids_differ (GRID-level, Intra)
      pair_grid_count_comparisons  -> pair_grid_count_majority (PAIR-level, Inter)
      pair_grid_counts             -> test_output_missing     (PAIR-level trigger)
    """
    return {
        "output_grid_comparisons": output_grid_comparisons(task, compare_fn),
        "input_grid_comparisons": input_grid_comparisons(task, compare_fn),
        "intra_pair_grid_comparisons": intra_pair_grid_comparisons(task, compare_fn),
        "pair_grid_count_comparisons": pair_grid_count_comparisons(task, compare_fn),
        "pair_grid_counts": pair_grid_counts(task),
    }
