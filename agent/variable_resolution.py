"""
variable_resolution — filling an anti-unification variable in a lifted rule.

§2.5-2b (BACKLOG_LOOP.md, user's advice): an anti-unification product is
*incomplete*. When `program.anti_unification.unify()` lifts two pair-specific
programs into one abstract rule, the position where they differed becomes a
`?vN` **hole**. Before the (frozen) transformation can run, that hole must be
*filled* — and the filling's *ground* must be the comparison evidence (COMM/DIFF
of the examples), never an invented value (P3/P4: reasons over values).

This module supplies that selection over a **bounded, already-known domain** of
candidate fillings. It deliberately does NOT *invent* a new derive-expression
for the hole (e.g. "target == 2·colour") — that is the open question Q-B3/Q-B4
(`arbor-open-questions.md`) and stays out of scope. The choice here is only
*which of a fixed set of known fillings* the examples support, decided by
example-reproduction. This is the selection vocabulary §2.5-1 says must grow
under `agent/` (not the frozen transformation DSL under `procedural_memory/DSL/`).

The criterion — example-reproduction — is the same one the fast path already
uses to admit a concrete rule (`ActiveSoarAgent._rule_matches_examples`): a
filling is accepted iff, instantiated into the rule, it reproduces *every*
example output exactly. A hole filled this way is grounded in the comparisons,
not guessed; a task that supports no candidate filling yields None (the rule is
then correctly *not* reused, rather than applied on a false match).
"""


def resolve_variable(task, candidates, instantiate, render):
    """Select the first candidate filling whose instantiated rule reproduces all
    of `task`'s example outputs, or None if none do.

    Args:
        task: the ARC task; its `example_pairs` supply the comparison ground.
        candidates: an *ordered, bounded* iterable of concrete fillings to try.
            Order encodes priority — the first filling that explains the
            examples wins (ties are decided deterministically, matching the
            slow-path build order).
        instantiate: ``value -> rule`` — build the concrete rule for a candidate.
        render: ``(rule, task, input_grid) -> grid | None`` — the transformation
            used to validate a candidate against an example input.

    The selection is grounded in comparison (P3/P4): a filling is chosen only
    when it *reproduces* the examples, never by fiat. ``render`` is invoked only
    with concrete (already-instantiated) rules, so a render path that calls back
    into this resolver does not recurse.
    """
    examples = [
        pair for pair in task.example_pairs
        if pair.input_grid is not None and pair.output_grid is not None
    ]
    if not examples:
        return None

    for value in candidates:
        rule = instantiate(value)
        if all(
            render(rule, task, pair.input_grid) == pair.output_grid.raw
            for pair in examples
        ):
            return value
    return None
