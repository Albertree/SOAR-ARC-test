"""
descent_path — module A's full descent *itinerary* (composes `descent_warranted`).

`descent_warranted` (iter 36) answers a single question: "does *this one* level
warrant a descent?". But what module A's `DescendOperator` actually needs is the
*whole* descent the §3 flow performs — TASK→PAIR→GRID, stopping at the first
level that can resolve its goal. That is `descent_warranted` evaluated at each
level **with the evidence visible at that level**, walked top-down until it says
"stop".

The subtlety this module owns is the *staging* of evidence by level. The exec
trace / raw prose descent is progressive: when the flow is still at the PAIR
level it has *not yet* gathered the GRID-level role-aligned output comparisons,
so the resolver (`all_outputs_comm`) cannot fire there and the level is blocked
→ descend. Only after descending to GRID are those comparisons in hand, so the
resolver fires and descent self-terminates (P1: depth entered strictly by
necessity). Calling `descent_warranted` with the *full* pattern bundle at every
level would wrongly let the GRID evidence resolve the PAIR-level goal and skip
the descent. So this module masks the pattern bundle to the keys observable at
each level before consulting `descent_warranted` — exactly the staging the
`descent_warranted` tests build by hand (`_task_level_patterns` /
`_pair_level_patterns` / `_grid_level_patterns`).

The level→visible-keys map is the declarative ARCKG fact "which comparisons /
properties belong to which level" — structural, value-agnostic (it names keys,
never colours/coords/counts). So the whole itinerary is value-agnostic: it fires
identically for easy000a (red) and easy000a2 (green).

This is **not** a registered boolean matcher (it returns the itinerary, a dict),
so it does not enter `CONDITION_REGISTRY` / inflate P5 — it is a recognition
*helper* that composes the registered `descent_warranted` matcher. It lives under
`agent/conditions/` because it is recognition vocabulary (CLAUDE.md §6.3), and it
is what `DescendOperator.effect` consumes to know *how far* to descend.
"""

# ARCKG levels Slice 1 descends through, top-down (P2: same-level comparison; the
# flow moves one level deeper at a time, never skipping a level).
DESCENT_LEVELS = ("task", "pair", "grid")

# Which `patterns` keys are *observable* when the flow is focused at each level.
# This encodes the progressive evidence-gathering of the §3 descent: PAIR-level
# focus cannot yet see the GRID-level role-aligned grid comparisons, so the
# GRID-only resolving evidence (output/input/intra_pair grid comparisons) is
# withheld until GRID focus. Declarative level→property map — value-agnostic.
_LEVEL_VISIBLE_KEYS = {
    "task": (
        "level_sibling_counts",
    ),
    "pair": (
        "level_sibling_counts",
        "pair_grid_counts",
        "pair_grid_count_comparisons",
    ),
    "grid": (
        "level_sibling_counts",
        "pair_grid_counts",
        "pair_grid_count_comparisons",
        "output_grid_comparisons",
        "input_grid_comparisons",
        "intra_pair_grid_comparisons",
    ),
}


def _stage(patterns, level):
    """Mask `patterns` to the keys observable at `level` (missing keys dropped)."""
    visible = _LEVEL_VISIBLE_KEYS.get(level, ())
    return {k: patterns[k] for k in visible if k in patterns}


def descent_itinerary(patterns, params=None):
    """Walk TASK→PAIR→GRID, consulting `descent_warranted` with level-staged
    evidence, and return the descent the §3 flow performs.

    patterns:
      The full Slice-1 pattern bundle (e.g. ``compare_scheduler.build_patterns``
      augmented with ``level_sibling_counts``). It is *staged* per level here, so
      callers pass the whole bundle once rather than rebuilding it per level.
    params:
      Forwarded verbatim to ``descent_warranted`` (e.g. ``min_to_compare`` /
      sub-matcher params); ``level`` is injected per iteration and overrides any
      ``level`` the caller passed.

    Returns a JSON-serialisable dict (P7):
      ``descend_from`` : levels that warranted a descent (the flow left them),
      ``terminal``     : the first level that did *not* warrant a descent — where
                         the flow stops (the level that can resolve the goal),
      ``itinerary``    : the levels visited, in order, up to and including
                         ``terminal``.

    Value-agnostic and self-terminating: it consults only ``descent_warranted``'s
    boolean verdict at each staged level and stops at the first ``False`` (P1).
    If every level warrants a descent (degenerate — e.g. malformed evidence), the
    itinerary runs to the deepest known level and stops there.
    """
    from agent import conditions

    base = dict(params or {})
    descend_from = []
    for i, level in enumerate(DESCENT_LEVELS):
        staged = _stage(patterns or {}, level)
        p = dict(base)
        p["level"] = level
        if conditions.match("descent_warranted", staged, p):
            descend_from.append(level)
            continue
        return {
            "descend_from": list(descend_from),
            "terminal": level,
            "itinerary": list(DESCENT_LEVELS[: i + 1]),
        }

    return {
        "descend_from": list(descend_from),
        "terminal": DESCENT_LEVELS[-1],
        "itinerary": list(DESCENT_LEVELS),
    }


def descent_itinerary_for_task(task, params=None):
    """Assemble the Slice-1 pattern bundle for ``task`` and return its §3 descent.

    The task-level convenience over ``descent_itinerary``: builds the full pattern
    bundle (``compare_scheduler.build_patterns``) plus the structural sibling
    census the ``nothing_to_compare`` disjunct needs (``level_sibling_counts`` —
    ``build_patterns`` does not include it), then walks the itinerary. This is the
    **single** task→itinerary assembly used by both module A's live
    ``DescendOperator.effect`` and the episode-trace recorder, so the descent is
    computed one way everywhere (criterion-2 uniformity, SLICE_1_LOOP.md §8) rather
    than re-assembled per call site.

    Value-agnostic: the bundle's recognisers read only COMM/DIFF verdicts and
    structural counts, so easy000a (red) and easy000a2 (green) descend identically.
    """
    from agent.compare_scheduler import build_patterns, level_sibling_counts
    patterns = dict(build_patterns(task))
    patterns["level_sibling_counts"] = level_sibling_counts(task)
    return descent_itinerary(patterns, params)


def slice1_descent_record(task):
    """Episode-trace record of module A's §3 hierarchical descent on ``task``.

    Module A (HierarchicalDescentController) is the spine of the raw-prose flow
    (``docs/arbor_context/arbor-flow-three-task-description.md``; P1 — "Task수준에서
    막히니까 Pair로, Pair에서 막히니까 Grid로"): depth is entered strictly by
    necessity, TASK→PAIR→GRID, stopping at the first level that can resolve the
    goal. The slow-path cycle performs this descent live (``DescendOperator``,
    iter 41) and leaves it in WM, but the probe solves via the fast path (stored
    rule) where the cycle never runs, and the episode trace recorded module B's
    goal walk and module C's comparison-flow form yet never module A's descent.
    Criterion 3 (SLICE_1_LOOP.md §8 — 접근성: 풀이가 정답 방향으로 간다) was therefore
    unobservable for the descent itself on every recorded episode.

    This is that record. It recomputes the itinerary the same value-agnostic way
    the live operator does (one shared assembly, ``descent_itinerary_for_task``),
    so every solve — fast or slow path — shows its TASK→PAIR→GRID descent path
    alongside the goal walk and comparison form (the module A+B+C observability
    triple). Records the form; does not touch the answer. Returns a plain
    JSON-serialisable dict (P7).
    """
    itinerary = descent_itinerary_for_task(task)
    return {"phase": "hierarchical_descent", "module": "A", **itinerary}
