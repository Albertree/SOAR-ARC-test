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
