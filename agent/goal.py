"""
goal — module B (GoalStack with Evolution), Slice-1 scope.

The raw prose (``docs/arbor_context/arbor-flow-three-task-description.md``,
easy000a paragraph) describes a goal that is *formed* from comparison evidence
and then *evolved* as the flow descends a level:

  · PAIR level, after comparing grid_count: the agent concludes
    "grid 개수가 1개인 pair 에 변화를 가해서 grid 개수가 2 인 속성을 가지는 pair 가
    되도록 하자" — i.e. the deficient (test) pair is missing a grid (its output),
    so the goal becomes *construct that missing grid Gx*.
  · GRID level, on seeing that a grid is made of three properties: the goal
    concretises to "Gx.color, Gx.size, Gx.contents 를 구하자" — determine each
    property of Gx.

``docs/arbor_context/arbor-execution-trace.md`` module B names exactly two
evolution kinds and the surface to build:

    B. GoalStack with Evolution
       · Refinement   : "Pa.grid_count := 2" → "create Gx"        (value → action)
       · Decomposition: "create Gx" → "{Gx.color, Gx.size, Gx.contents}"
                                                                  (schema split)
       다음 액션: agent/goal.py 신규 (GoalStack 클래스 + evolve(new_node, schema)
                  + 진화 규칙 2종)

This module is that library. It is **value-agnostic** (SLICE_1_LOOP.md §9 / P7):
a goal node names *property keys* (``"size"``/``"color"``/``"contents"``) and
*structural* facts (which pair is deficient, by how many grids) — never a colour
or coordinate literal. The PAIR-level value goal is derived from the grid-count
*census* (counts only), so easy000a (red output) and easy000a2 (green output)
produce an *identical* goal tree.

Everything here is a plain symbolic dict, JSON-serialisable (P7). Goal nodes use
the same ``{"subgoals": {name: {"status": ...}}}`` shape the SOAR cycle's
satisfaction check reads (``agent/cycle.py:_s1_goal_satisfied``), so a later iter
can wire ``GoalStack`` into the pipeline without reshaping it. This iter only
builds + tests the library; wiring it into ``active_operators.py`` (which would
add net lines and so requires an anti-unification-side companion, F8) is the next
iter's smallest step — mirroring how ``compare_scheduler.py`` was built
library-first and wired later.
"""

from __future__ import annotations


# ----------------------------------------------------------------------
# Goal-node kinds (the three forms a goal takes as it evolves)
# ----------------------------------------------------------------------

KIND_VALUE = "value"     # a property-value target/mismatch to resolve (pre-action)
KIND_ACTION = "action"   # an actionable goal: construct a named component
KIND_SCHEMA = "schema"   # an action goal decomposed over a component's schema

# The GRID schema (module D grid property keys: ARCKG/grid.py:to_json). The
# decomposition step splits "construct Gx" into one child per key. Property
# *names* only — value-agnostic.
GRID_SCHEMA = ("size", "color", "contents")

STATUS_OPEN = "open"
STATUS_SOLVED = "solved"


# ----------------------------------------------------------------------
# Goal constructors
# ----------------------------------------------------------------------

def value_goal_from_grid_count_census(census) -> dict | None:
    """Build the initial PAIR-level *value* goal from the grid-count census.

    ``census`` is ``compare_scheduler.pair_grid_counts(task)`` —
    ``{"example_counts": [...], "test_counts": [...]}`` — structural counts only.
    The goal expresses the §3 PAIR-level conclusion *value-agnostically*: the
    example pairs share a majority grid_count, and any test pair below it is
    *deficient* (missing ``majority - count`` grids — its output). It carries no
    colour/coordinate; the target count is the observed majority, not a literal.

    Returns ``None`` when there is no actionable deficiency (no examples, or no
    test pair below the example majority) — the flow then has nothing to
    construct at this level.
    """
    example_counts = list((census or {}).get("example_counts") or [])
    test_counts = list((census or {}).get("test_counts") or [])
    if not example_counts:
        return None

    # Majority example grid_count (the consensus the deficient pair should reach).
    majority = _majority(example_counts)

    deficient = [i for i, c in enumerate(test_counts) if c < majority]
    if not deficient:
        return None

    return {
        "kind": KIND_VALUE,
        "property": "grid_count",
        "target_count": majority,          # structural, derived — not a literal
        "deficient_test_pairs": deficient,  # indices into task.test_pairs
        "status": STATUS_OPEN,
    }


def _majority(counts):
    """Most frequent value in ``counts`` (ties → the larger value).

    Value-agnostic: operates on structural integer counts only.
    """
    tally = {}
    for c in counts:
        tally[c] = tally.get(c, 0) + 1
    best_freq = max(tally.values())
    return max(c for c, f in tally.items() if f == best_freq)


# ----------------------------------------------------------------------
# The two evolution rules (module B)
# ----------------------------------------------------------------------

def refine_value_to_action(goal: dict) -> dict:
    """Refinement: a grid_count *value* goal → an *action* goal (value → action).

    Raw prose: "grid 개수가 1개인 pair 에 변화를 가해서 … grid 개수가 2 … 되도록
    하자" — the deficient pair is missing a grid, so the actionable form is
    *construct that missing grid Gx*. The action names the component to build
    (``"Gx"``) and which pairs need it; it carries no colour/coordinate (P7).
    """
    if goal.get("kind") != KIND_VALUE:
        raise ValueError(f"refinement expects a {KIND_VALUE!r} goal, got {goal.get('kind')!r}")
    return {
        "kind": KIND_ACTION,
        "verb": "construct",
        "target": "Gx",                                   # the missing grid
        "in_test_pairs": list(goal.get("deficient_test_pairs") or []),
        "from_property": goal.get("property"),            # provenance: grid_count
        "status": STATUS_OPEN,
    }


def decompose_action(goal: dict, schema=GRID_SCHEMA) -> dict:
    """Decomposition: an *action* goal → a *schema* goal with per-property children.

    Raw prose: a grid is made of three properties, so "construct Gx" concretises
    to "Gx.{size, color, contents} 를 구하자". Splits ``schema`` (property *names*)
    into one ``determine`` child per key, all open. The children live under the
    ``subgoals`` key in the same shape ``agent/cycle.py:_s1_goal_satisfied``
    reads, so the schema goal is satisfied exactly when every property is solved.
    Value-agnostic: only property names are enumerated; no value is chosen here.
    """
    if goal.get("kind") != KIND_ACTION:
        raise ValueError(f"decomposition expects a {KIND_ACTION!r} goal, got {goal.get('kind')!r}")
    if not schema:
        raise ValueError("decomposition requires a non-empty schema")
    subgoals = {
        prop: {"determine": f"{goal.get('target', 'Gx')}.{prop}", "status": STATUS_OPEN}
        for prop in schema
    }
    return {
        "kind": KIND_SCHEMA,
        "verb": goal.get("verb", "construct"),
        "target": goal.get("target", "Gx"),
        "in_test_pairs": list(goal.get("in_test_pairs") or []),
        "subgoals": subgoals,
        "status": STATUS_OPEN,
    }


def evolve(goal: dict, schema=GRID_SCHEMA) -> dict:
    """Single entry point (exec-trace ``evolve(new_node, schema)``).

    Dispatches on the current goal's kind, applying whichever of the two
    evolution rules fits — Refinement for a value goal, Decomposition for an
    action goal. A schema goal (already decomposed) or anything solved is
    returned unchanged: evolution is monotone value → action → schema.
    """
    kind = goal.get("kind")
    if kind == KIND_VALUE:
        return refine_value_to_action(goal)
    if kind == KIND_ACTION:
        return decompose_action(goal, schema)
    return goal


# ----------------------------------------------------------------------
# GoalStack — minimal evolving-goal holder
# ----------------------------------------------------------------------

class GoalStack:
    """A minimal evolving goal (module B).

    Holds the current goal node and the history of forms it has taken as the
    flow descended. ``advance(schema)`` replaces the current node with its
    evolved form (Refinement or Decomposition), keeping the prior form in
    ``history`` so the descent path stays inspectable (symbolic, P7).

    This is *minimal* by design (exec-trace: "minimal GoalStack"): it tracks one
    goal evolving in place rather than a full subgoal forest — Slice 1's flow is
    a single chain (PAIR value → action → GRID schema). The schema goal's own
    ``subgoals`` carry the per-property leaves.
    """

    def __init__(self, goal: dict):
        if not isinstance(goal, dict) or "kind" not in goal:
            raise ValueError("GoalStack requires a goal node dict with a 'kind'")
        self.current = goal
        self.history: list[dict] = []

    def advance(self, schema=GRID_SCHEMA) -> dict:
        """Evolve the current goal one step; record the prior form. Returns the
        new current goal. A no-op evolution (already a schema/solved goal) leaves
        the stack unchanged and is not recorded as a distinct history step."""
        evolved = evolve(self.current, schema)
        if evolved is self.current or evolved == self.current:
            return self.current
        self.history.append(self.current)
        self.current = evolved
        return self.current

    def mark_property_solved(self, prop: str) -> None:
        """Mark one schema child (e.g. ``"size"``) solved. Only meaningful once
        the current goal is a decomposed schema goal."""
        subs = self.current.get("subgoals")
        if isinstance(subs, dict) and prop in subs:
            subs[prop]["status"] = STATUS_SOLVED

    def is_satisfied(self) -> bool:
        """True when the current goal is solved.

        A schema goal is solved exactly when every child property is solved
        (same rule as ``agent/cycle.py:_s1_goal_satisfied``); a value/action goal
        is solved only by an explicit ``status``."""
        return _goal_satisfied(self.current)

    def to_json(self) -> dict:
        """Symbolic, JSON-serialisable snapshot of the whole stack (P7)."""
        return {"current": self.current, "history": list(self.history)}


def _goal_satisfied(goal: dict) -> bool:
    if not isinstance(goal, dict):
        return False
    subs = goal.get("subgoals")
    if isinstance(subs, dict) and subs:
        return all(
            isinstance(sg, dict) and sg.get("status") == STATUS_SOLVED
            for sg in subs.values()
        )
    return goal.get("status") == STATUS_SOLVED
