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


def level_sibling_counts(task):
    """Structural census of how many sibling nodes sit at each Slice-1 level for
    *pairwise* (Inter) comparison (value-agnostic counts only).

    Returns ``{"task": <#task nodes>, "pair": <#pairs>}``. A node is compared
    against its role-aligned *siblings* (P6: 2-at-a-time), so a level offers
    "something to compare" only when its sibling count is >= 2:

      · ``task`` == 1 always in Slice 1 — the working memory holds a single
        loaded task with no sibling tasks, so the TASK level has nothing to
        compare pairwise. This is the §3 ``[TASK level]`` step's ``n_at_level==1``
        impasse ("형제 TASK 없음 → Inter 비교 대상 0 → 비교 자연 skip → descend"):
        the flow must descend to PAIR before any comparison — or goal — can form
        (P1: depth entered by necessity, never gratuitously).
      · ``pair`` == len(pairs_of(task)) (examples + test) >= 2 — the PAIR level
        has siblings to compare, so it does *not* trigger this descent.

    Counts only (never a colour/coordinate/grid_count value) → value-agnostic
    (P7); it feeds the `nothing_to_compare` recognition matcher.
    """
    return {"task": 1, "pair": len(pairs_of(task))}


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


def grid_comparison_specs(task):
    """Grid-level comparison agenda for the SOAR cycle (Slice 1, module C).

    Module C owns *scheduling* (SLICE_1_LOOP.md §5), so the specs the cycle's
    ``compare`` step executes are produced here rather than inline in the
    operator. Two analysis kinds (§5), both at GRID level, value-agnostic
    (node ids only — never a colour/coord):

      · Intra-Pair (role G0↔G1): one spec per complete example pair — the §3 ①
        sibling comparison (DIFF for easy000a). ``type=="grid"``.
      · Inter-Grid, role-aligned — the §3 ② comparison, scheduled across *both*
        roles so the cycle executes the step's deciding half *and* its contrast:
          - role==G1 (``type=="inter_grid_output"``): the *deciding* comparison —
            example output grids compared pairwise (P6: 2-at-a-time). All COMM ⇒
            the test output is the common G1.
          - role==G0 (``type=="inter_grid_input"``): the *contrast* — example
            input grids compared pairwise. They DIFF in easy000a; that contrast
            is *why* the answer is read off the (invariant) outputs, not the
            (varying) inputs (§3 line 119; raw prose easy000a paragraph).

    Routing these through the agenda means the cycle's select→compare→extract
    actually *executes* them (CLAUDE.md §5: compare writes comparisons, extract
    reads them) instead of extract recomputing them. Each spec carries a unique
    ``key`` so CompareOperator can store receipts without collision.
    """
    specs = []
    for idx, pair in enumerate(task.example_pairs):
        if pair.input_grid is not None and pair.output_grid is not None:
            specs.append({
                "type": "grid",
                "pair_idx": idx,
                "pair_type": "example",
                "key": f"grid_{idx}",
                "id1": pair.input_grid.node_id,
                "id2": pair.output_grid.node_id,
            })
    for spec_type, role, grid_attr in (
        ("inter_grid_output", "G1", "output_grid"),
        ("inter_grid_input", "G0", "input_grid"),
    ):
        grids = [
            getattr(p, grid_attr) for p in task.example_pairs
            if getattr(p, grid_attr) is not None
            and role_of(getattr(p, grid_attr)) == role
        ]
        for j, (a, b) in enumerate(combinations(grids, 2)):
            specs.append({
                "type": spec_type,
                "key": f"{spec_type}_{j}",
                "id1": a.node_id,
                "id2": b.node_id,
            })
    return specs


def pair_comparison_specs(task):
    """PAIR-level comparison agenda: Inter-Pair grid_count, pairwise (P6).

    The §3 PAIR-level evidence (SLICE_1_LOOP.md §3): every pair (examples *and*
    the test) compared 2-at-a-time on its single PAIR property, grid_count
    (``Pair.to_json`` exposes exactly ``grid_count``). The examples carry 2 grids
    and the test 1, so the receipts split COMM (the complete pairs agree) / DIFF
    (the test dissents) — the consensus-with-dissenter structure the
    ``pair_grid_count_majority`` matcher recognises (and the same fact
    ``test_output_missing`` reads from the raw census). Scheduling it here means
    the cycle's compare step *executes* this PAIR-level comparison instead of
    ``build_patterns`` recomputing it (CLAUDE.md §5). Pair node ids only —
    value-agnostic (P7): it never reads a colour, coordinate, or grid_count value.
    """
    specs = []
    for j, (a, b) in enumerate(combinations(pairs_of(task), 2)):
        specs.append({
            "type": "inter_pair_grid_count",
            "key": f"inter_pair_grid_count_{j}",
            "id1": a.node_id,
            "id2": b.node_id,
        })
    return specs


def comparison_specs(task):
    """The full Slice-1 comparison agenda the SOAR cycle executes (module C).

    Concatenates the GRID-level specs (``grid_comparison_specs``: Intra-Pair
    G0↔G1 + role-aligned Inter-Grid over both roles) with the PAIR-level
    Inter-Pair grid_count specs (``pair_comparison_specs``). Routing *every* §3
    comparison kind through one agenda means select→compare→extract share one
    receipt set rather than extract recomputing comparisons the cycle never ran
    (CLAUDE.md §5). Each spec carries a unique ``key`` (the GRID and PAIR key
    prefixes differ), so CompareOperator stores receipts without collision.
    """
    return grid_comparison_specs(task) + pair_comparison_specs(task)


def build_node_lookup(task):
    """Map node_id -> ARCKG node for every node ``comparison_specs`` references.

    CompareOperator resolves each spec's ``id1``/``id2`` against this map. The
    GRID-level specs reference grid nodes and the PAIR-level Inter-Pair
    grid_count spec references pair nodes, so both the pairs (examples + test)
    and their grids are indexed.
    """
    lookup = {}
    for pair in pairs_of(task):
        lookup[pair.node_id] = pair
        if pair.input_grid is not None:
            lookup[pair.input_grid.node_id] = pair.input_grid
        if pair.output_grid is not None:
            lookup[pair.output_grid.node_id] = pair.output_grid
    return lookup


def build_patterns(task, compare_fn=None, intra_pair_receipts=None,
                   output_receipts=None, input_receipts=None,
                   pair_grid_count_receipts=None):
    """Assemble the Slice-1 `patterns` dict consumed by the condition matchers.

    Keys:
      output_grid_comparisons      -> all_outputs_comm       (GRID-level, Inter, role==G1)
      input_grid_comparisons       -> inputs_vary            (GRID-level, Inter, role==G0)
      intra_pair_grid_comparisons  -> intra_pair_grids_differ (GRID-level, Intra)
      pair_grid_count_comparisons  -> pair_grid_count_majority (PAIR-level, Inter)
      pair_grid_counts             -> test_output_missing     (PAIR-level trigger)

    ``intra_pair_receipts`` / ``output_receipts`` / ``input_receipts`` /
    ``pair_grid_count_receipts``: when supplied (the receipts the SOAR cycle's
    ``compare`` step already produced for the Intra-Pair G0↔G1, the deciding
    Inter-Grid role==G1, the contrast Inter-Grid role==G0, and the PAIR-level
    Inter-Pair grid_count comparisons respectively), they populate the matching
    key instead of being recomputed here — so select→compare→extract share one
    receipt set rather than extract silently redoing the cycle's comparison work
    (CLAUDE.md §5: "extract_pattern reads comparisons"). ``None`` (library /
    standalone use) keeps the original behaviour: that key is computed from the
    task here.
    """
    intra = (intra_pair_receipts if intra_pair_receipts is not None
             else intra_pair_grid_comparisons(task, compare_fn))
    outputs = (output_receipts if output_receipts is not None
               else output_grid_comparisons(task, compare_fn))
    inputs = (input_receipts if input_receipts is not None
              else input_grid_comparisons(task, compare_fn))
    pair_counts = (pair_grid_count_receipts if pair_grid_count_receipts is not None
                   else pair_grid_count_comparisons(task, compare_fn))
    return {
        "output_grid_comparisons": outputs,
        "input_grid_comparisons": inputs,
        "intra_pair_grid_comparisons": intra,
        "pair_grid_count_comparisons": pair_counts,
        "pair_grid_counts": pair_grid_counts(task),
    }


def patterns_from_cycle_receipts(task, comparisons, compare_fn=None):
    """Build the Slice-1 `patterns` dict from the receipts the cycle produced.

    The extract step's job (CLAUDE.md §5: "extract_pattern reads comparisons,
    writes patterns"). Partitions ``wm.s1["comparisons"]`` by the comparison kind
    each spec records so every GRID-level kind the agenda scheduled is *read from*
    the cycle's receipts rather than recomputed:

      · ``inter_grid_output``     -> output_grid_comparisons     (deciding, §3 ②)
      · ``inter_grid_input``      -> input_grid_comparisons      (contrast, §3 ②)
      · ``inter_pair_grid_count`` -> pair_grid_count_comparisons (PAIR-level, §3)
      · everything else           -> intra_pair_grid_comparisons (§3 ①)

    The only kind not on the agenda is the grid-count *census*
    (``pair_grid_counts``, a structural count split by role, not a
    ``compare(scope_A, scope_B)`` receipt), so it is still computed from the task
    by ``build_patterns``. With no receipts (operator invoked standalone), every
    key falls back to a task recompute, so the result equals
    ``build_patterns(task)``. Value-agnostic: only COMM/DIFF verdicts and
    structural counts are read, never a colour/coordinate value (P7).
    """
    by_type = {}
    for c in (comparisons or {}).values():
        if isinstance(c, dict) and "result" in c:
            spec_type = (c.get("spec") or {}).get("type")
            by_type.setdefault(spec_type, []).append(c["result"])
    routed = {"inter_grid_output", "inter_grid_input", "inter_pair_grid_count"}
    intra = [r for t, rs in by_type.items() if t not in routed for r in rs]
    return build_patterns(
        task, compare_fn,
        intra_pair_receipts=intra or None,
        output_receipts=by_type.get("inter_grid_output") or None,
        input_receipts=by_type.get("inter_grid_input") or None,
        pair_grid_count_receipts=by_type.get("inter_pair_grid_count") or None,
    )
