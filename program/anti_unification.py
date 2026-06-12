"""
anti_unification — generalize task-specific rules into one abstract rule.

This is R3 (BACKLOG_LOOP §3, CLAUDE.md §8): the mechanism by which two or more
*pair/family-specific* programs that share a skeleton are lifted into a single
rule whose differing points become generalization variables (``?vN``). It is the
only avenue by which new transformational vocabulary may grow — the static DSL
stays frozen at ``make_grid``/``coloring`` (INVARIANTS F3); generality is *data*
produced here, not hand-coded code.

BACKLOG_LOOP §2.5-2 is the load-bearing design point: **the input to
anti-unification is the *argument-expression* tree, not the raw transformation.**
Two object-move rules whose targets are literal coordinates would share no common
skeleton (the 168-rule failure). Expressed instead as one ``place_object`` action
parameterised by a *target reading* (``constant_target`` vs ``constant_offset``),
the skeleton is identical and only the reading differs — so anti-unification
lifts the reading to a variable and the two collapse into one ``covers>1`` rule.

The single permitted call site is ``agent/memory.py:save_rule()`` (CLAUDE.md §8).
"""

import json
import os
from datetime import datetime


# ---------------------------------------------------------------------------
# Term representation (BACKLOG_LOOP §2.5-2: argument-expression trees)
# ---------------------------------------------------------------------------
#
# A term is one of:
#   {"t": "leaf", "value": <scalar>}
#   {"t": "list", "items": [<term>, ...]}
#   {"t": "map",  "items": {<key>: <term>, ...}}
#   {"t": "func", "name": <str>, "args": [<term>, ...]}
#   {"t": "var",  "name": "?vN", "fillers": [<value-or-term>, ...]}   (only after lift)


def program_lines_to_terms(program_lines: list) -> list:
    """Convert a list of program lines into a term-tree list (new structure).

    A *program line* is ``{"dsl": <name>, "args": {...}}``; it becomes a ``func``
    term whose single child is the term of its argument map. The original
    ``program_lines`` is not mutated.
    """
    return [_value_to_term(line) for line in program_lines]


def _value_to_term(value):
    if isinstance(value, dict):
        if "dsl" in value:  # a program line
            return {
                "t": "func",
                "name": value["dsl"],
                "args": [_value_to_term(value.get("args", {}))],
            }
        return {"t": "map", "items": {k: _value_to_term(v) for k, v in sorted(value.items())}}
    if isinstance(value, (list, tuple)):
        return {"t": "list", "items": [_value_to_term(v) for v in value]}
    return {"t": "leaf", "value": value}


def terms_to_program_lines(terms: list) -> list:
    """Convert a (possibly variabilised) term list back to program-line form.

    ``?vN`` variables are preserved verbatim as their name string — they are
    *not* substituted with a concrete value (that is the consumer's job, at
    predict time, per BACKLOG_LOOP §2.5-2b).
    """
    return [_term_to_value(t) for t in terms]


def _term_to_value(term):
    kind = term.get("t")
    if kind == "leaf":
        return term["value"]
    if kind == "var":
        return term["name"]
    if kind == "list":
        return [_term_to_value(x) for x in term["items"]]
    if kind == "map":
        return {k: _term_to_value(v) for k, v in term["items"].items()}
    if kind == "func":
        return {"dsl": term["name"], "args": _term_to_value(term["args"][0])}
    raise ValueError(f"unknown term kind: {kind!r}")


def _align_term_lists_dp(terms_a: list, terms_b: list,
                         context_bonus: dict = None) -> list:
    """Align two term lists positionally (LCS-style DP on head identity).

    For the single-line object-move programs this lift handles, the lists are
    equal-length and align 1:1; the DP keeps the function general for longer
    programs without caching anything in global state. ``context_bonus`` is
    accepted for interface compatibility (func-name match bonus) but the simple
    positional alignment already prefers same-name pairs.
    """
    n, m = len(terms_a), len(terms_b)
    # DP over LCS of head signatures; fall back to positional pairing.
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            same = _head_sig(terms_a[i]) == _head_sig(terms_b[j])
            bonus = 0
            if context_bonus and same:
                bonus = context_bonus.get(_head_sig(terms_a[i]), 0)
            if same:
                dp[i][j] = dp[i + 1][j + 1] + 1 + bonus
            else:
                dp[i][j] = max(dp[i + 1][j], dp[i][j + 1])
    pairs = []
    i = j = 0
    while i < n and j < m:
        if _head_sig(terms_a[i]) == _head_sig(terms_b[j]):
            pairs.append((i, j))
            i += 1
            j += 1
        elif dp[i + 1][j] >= dp[i][j + 1]:
            i += 1
        else:
            j += 1
    return pairs


def _head_sig(term):
    if term.get("t") == "func":
        return ("func", term["name"])
    return (term.get("t"),)


def anti_unify_terms(term_a: dict, term_b: dict, var_counter: list,
                     variables: dict = None) -> dict:
    """Recursively anti-unify two terms.

    Matching structure is preserved and recursed into; a point where the two
    differ is replaced by a fresh ``?vN`` variable that records both fillers.
    ``var_counter`` is a mutable ``[int]`` so variable numbers are shared across
    a whole program; ``variables`` accumulates ``{?vN: [filler, ...]}``. Terms of
    different *type* are never force-unified — they become a variable.
    """
    if variables is None:
        variables = {}

    # An existing variable absorbs another filler (n-ary fold).
    if term_a.get("t") == "var":
        _add_filler(term_a, _term_to_value(term_b), variables)
        return term_a
    if term_b.get("t") == "var":
        _add_filler(term_b, _term_to_value(term_a), variables)
        return term_b

    if term_a == term_b:
        return _copy_term(term_a)

    if term_a.get("t") == term_b.get("t"):
        kind = term_a["t"]
        if kind == "func" and term_a["name"] == term_b["name"] \
                and len(term_a["args"]) == len(term_b["args"]):
            return {
                "t": "func",
                "name": term_a["name"],
                "args": [
                    anti_unify_terms(x, y, var_counter, variables)
                    for x, y in zip(term_a["args"], term_b["args"])
                ],
            }
        if kind == "list" and len(term_a["items"]) == len(term_b["items"]):
            return {
                "t": "list",
                "items": [
                    anti_unify_terms(x, y, var_counter, variables)
                    for x, y in zip(term_a["items"], term_b["items"])
                ],
            }
        if kind == "map" and set(term_a["items"]) == set(term_b["items"]):
            return {
                "t": "map",
                "items": {
                    k: anti_unify_terms(term_a["items"][k], term_b["items"][k],
                                        var_counter, variables)
                    for k in sorted(term_a["items"])
                },
            }

    # Structural mismatch → fresh variable.
    return _new_var(term_a, term_b, var_counter, variables)


def _new_var(term_a, term_b, var_counter, variables):
    name = f"?v{var_counter[0]}"
    var_counter[0] += 1
    fillers = [_term_to_value(term_a), _term_to_value(term_b)]
    variables[name] = list(fillers)
    return {"t": "var", "name": name, "fillers": fillers}


def _add_filler(var_term, value, variables):
    if value not in var_term["fillers"]:
        var_term["fillers"].append(value)
    variables.setdefault(var_term["name"], var_term["fillers"])
    if value not in variables[var_term["name"]]:
        variables[var_term["name"]].append(value)


def _copy_term(term):
    return json.loads(json.dumps(term))


def anti_unify_pair_programs(pair_programs: list) -> list:
    """Anti-unify ≥2 flat program lists into one abstract program (``?vN`` vars).

    Flow: ``program_lines_to_terms`` → ``_align_term_lists_dp`` → fold via
    ``anti_unify_terms`` → ``terms_to_program_lines``. Structurally different
    pairs are *not* force-merged — their differing points become variables.
    """
    lines, _vars = _anti_unify_with_vars(pair_programs)
    return lines


def _anti_unify_with_vars(pair_programs):
    if not pair_programs:
        return [], {}
    term_lists = [program_lines_to_terms(p) for p in pair_programs]
    var_counter = [0]
    variables: dict = {}

    acc = [_copy_term(t) for t in term_lists[0]]
    for nxt in term_lists[1:]:
        pairs = _align_term_lists_dp(acc, nxt)
        aligned_acc = {i: j for (i, j) in pairs}
        merged = []
        for i, term in enumerate(acc):
            if i in aligned_acc:
                merged.append(anti_unify_terms(term, nxt[aligned_acc[i]],
                                               var_counter, variables))
            else:
                merged.append(term)
        acc = merged
    return terms_to_program_lines(acc), variables


# ---------------------------------------------------------------------------
# Rule-level lift (the CLAUDE.md §8 entry point)
# ---------------------------------------------------------------------------

#: How a concrete object-move action's DSL name reads its target argument.
#: This is the BACKLOG_LOOP §2.5-1 representation lift: both concrete moves are
#: one ``place_object`` action parameterised by *which COMM reading* fixes the
#: target. Expressing them this way is what gives anti-unification a common
#: skeleton to abstract (§2.5-2).
_OBJECT_MOVE_READING = {
    "place_object_constant": "constant_target",
    "place_object_relative": "constant_offset",
    "place_object_corner": "constant_corner",
    "place_object_resize": "constant_resize",
    "place_object_select": "constant_select",
}


# ---------------------------------------------------------------------------
# Liftable families (BACKLOG_LOOP §2.5-2 / R3)
# ---------------------------------------------------------------------------
#
# A *liftable family* is a set of concrete rules that share one transformation
# skeleton and differ only in a single *argument expression*. Anti-unification
# turns that differing argument into a variable, collapsing N concrete rules into
# one ``covers>1`` abstract rule (§2.5-4: rule count falls while covers rises).
#
# Each family declares (a) how a concrete rule maps to its single-line
# argument-expression *program* (or None when the rule is not a concrete member),
# (b) which single value differs across members (the lift `key`), (c) the
# umbrella `condition_type`/`concept` for the abstract rule, and (d) the `args`
# slot (`list_key`) under which the abstraction records the concrete values it
# ranges over (so the consumer can resolve the variable at predict time from
# COMM/DIFF — §2.5-2b). Adding a family here is the *only* way the lift grows to a
# new concept; it introduces no new transformation (the program bottoms out in
# make_grid/coloring — F3-exempt).


def _object_move_program(rule):
    reading = _OBJECT_MOVE_READING.get(rule.get("action", {}).get("dsl"))
    if reading is None:
        return None
    return [{"dsl": "place_object", "args": {"target": {"reading": reading}}}]


def _object_move_key(rule):
    return _OBJECT_MOVE_READING.get(rule.get("action", {}).get("dsl"))


def _object_move_synth(reading):
    reading_to_dsl = {v: k for k, v in _OBJECT_MOVE_READING.items()}
    return {
        "condition": {"type": "object_move",
                      "params": {"min_evidence": 2}, "min_evidence": 2},
        "action": {"dsl": reading_to_dsl[reading], "args": {}},
        "concept": "place_object",
        "category": "object_move",
    }


def _size_grid_program(rule):
    act = rule.get("action", {})
    if act.get("dsl") != "size_to_grid":
        return None
    args = act.get("args", {})
    if "properties" in args:            # already an abstract lift, not a source
        return None
    prop = args.get("dim_property")
    if not isinstance(prop, str) or prop.startswith("?"):
        return None
    return [{"dsl": "size_to_grid", "args": {"dim_property": prop}}]


def _size_grid_key(rule):
    act = rule.get("action", {})
    if act.get("dsl") != "size_to_grid":
        return None
    args = act.get("args", {})
    if "properties" in args:
        return None
    prop = args.get("dim_property")
    if not isinstance(prop, str) or prop.startswith("?"):
        return None
    return prop


def _size_grid_synth(prop):
    return {
        "condition": {"type": "object_size_grid",
                      "params": {"min_evidence": 2}, "min_evidence": 2},
        "action": {"dsl": "size_to_grid", "args": {"dim_property": prop}},
        "concept": "object_size_to_solid_square",
        "category": "object_size_grid",
    }


#: The lift families, tried in order. ``object_move`` lifts the four placement
#: readings into ``place_object``; ``object_size_grid`` lifts the canvas-sizing
#: *dimension property* (object_size, bbox_height, …) into a single
#: ``size_to_grid`` rule — the first lift family *outside* object_move (R3 on a
#: fresh concept, raising P3 = au_traced_frac).
LIFT_FAMILIES = [
    {
        "name": "object_move",
        "category": "object_move",
        "condition_type": "object_move",
        "concept": "place_object",
        "list_key": "readings",
        "program": _object_move_program,
        "key": _object_move_key,
        "synth": _object_move_synth,
    },
    {
        "name": "object_size_grid",
        "category": "object_size_grid",
        "condition_type": "object_size_grid",
        "concept": "object_property_to_solid_square",
        "list_key": "properties",
        "program": _size_grid_program,
        "key": _size_grid_key,
        "synth": _size_grid_synth,
    },
]


def family_for_rule(rule: dict):
    """The lift family a *concrete* rule belongs to, or None. A concrete rule is
    one whose argument-expression program is defined for some family (an abstract
    lift, or an unrelated rule, yields None)."""
    for fam in LIFT_FAMILIES:
        if fam["program"](rule) is not None:
            return fam
    return None


def abstract_values(rule: dict, fam: dict) -> list:
    """The concrete values an abstract rule of family ``fam`` already ranges over
    (its ``args[list_key]`` list), or ``[]`` when ``rule`` is not that
    abstraction."""
    args = rule.get("action", {}).get("args", {})
    vals = args.get(fam["list_key"])
    return list(vals) if isinstance(vals, list) else []


class AntiUnifyResult:
    """Outcome of :func:`unify` — an abstract rule plus its trace.

    ``is_more_general()`` is True only when a common skeleton survived *and* at
    least one variable was introduced (i.e. the inputs genuinely differed and the
    abstraction covers more than any one source). ``write_trace`` persists the
    receipt to ``episodic_memory/<task>/anti_unification/`` (CLAUDE.md §8).
    """

    def __init__(self, abstract_rule, variables, sources, common_skeleton):
        self.abstract_rule = abstract_rule
        self.variables = variables
        self.sources = sources
        self.common_skeleton = common_skeleton
        self.trace_path = None

    def is_more_general(self) -> bool:
        return bool(self.common_skeleton) and bool(self.variables)

    def write_trace(self, source_task: str,
                    episodic_root: str = "episodic_memory") -> str:
        au_dir = os.path.join(episodic_root, source_task, "anti_unification")
        os.makedirs(au_dir, exist_ok=True)
        action = self.abstract_rule.get("action", {})
        trace = {
            "created_at": datetime.now().isoformat(),
            "abstract_action": action,
            "abstract_condition_type": self.abstract_rule.get("condition", {}).get("type"),
            "variables": self.variables,
            "sources": [
                {
                    "concept": s.get("concept"),
                    "condition_type": s.get("condition", {}).get("type"),
                    "action_dsl": s.get("action", {}).get("dsl"),
                    "covers": s.get("covers", []),
                }
                for s in self.sources
            ],
            "skeleton": self.common_skeleton,
        }
        dsl = action.get("dsl", "abstract")
        path = os.path.join(au_dir, f"{dsl}_lift.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(trace, fh, indent=2)
        self.trace_path = path
        return path


def _rule_to_program(rule: dict):
    """The liftable argument-expression program for a canonical rule, or None.

    Dispatches on the rule's lift family (`LIFT_FAMILIES`): a concrete
    ``place_object_*`` action becomes a ``place_object`` line carrying the COMM
    *reading* that fixes its target (§2.5-1); a concrete ``size_to_grid`` action
    becomes a line carrying its *dimension property*. Rules outside every known
    family return None, so :func:`unify` declines (NoCommonSkeleton) rather than
    force-merging.
    """
    fam = family_for_rule(rule)
    return fam["program"](rule) if fam is not None else None


def unify(rules: list) -> "AntiUnifyResult | None":
    """Lift ≥2 canonical rules sharing a skeleton into one abstract rule.

    Returns an :class:`AntiUnifyResult`, or ``None`` when there is no common
    skeleton (the rules are not in a shared lift family, or fewer than two were
    given). The caller (``agent/memory.py:save_rule``) checks
    ``result.is_more_general()`` before adopting ``result.abstract_rule``.
    """
    if not rules or len(rules) < 2:
        return None

    fams = [family_for_rule(r) for r in rules]
    if any(f is None for f in fams):
        return None  # NoCommonSkeleton — leave inputs unchanged
    if len({f["name"] for f in fams}) != 1:
        return None  # mixed families share no skeleton
    fam = fams[0]
    programs = [fam["program"](r) for r in rules]

    # All sources must share a category for a meaningful umbrella condition.
    categories = {r.get("category") for r in rules}
    if len(categories) != 1:
        return None
    category = next(iter(categories))

    abstract_lines, variables = _anti_unify_with_vars(programs)
    if not abstract_lines or not variables:
        # Identical inputs (no differing point) — nothing to generalise.
        return AntiUnifyResult(None, {}, rules, [])

    # Build the abstract canonical rule. The umbrella condition recognises the
    # whole family; the action keeps the lifted variable plus the concrete fillers
    # it ranges over (so the consumer can resolve it at predict time from
    # COMM/DIFF — §2.5-2b). The family decides which condition type, concept and
    # `args` slot record the abstraction.
    var_name = next(iter(variables))
    fillers = sorted(variables[var_name])
    line = abstract_lines[0]
    args = dict(line.get("args", {}))
    args[fam["list_key"]] = fillers
    abstract_rule = {
        "condition": {
            "type": fam["condition_type"],
            "params": {"min_evidence": 2},
            "min_evidence": 2,
        },
        "action": {
            "dsl": line["dsl"],
            "args": args,
        },
        "concept": fam["concept"],
        "category": category,
    }
    return AntiUnifyResult(abstract_rule, variables, rules, abstract_lines)
