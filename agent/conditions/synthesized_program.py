"""
synthesized_program — the general Slow-path synthesizer's recognition matcher
(modules F/G, ``arbor.md`` Fast/Slow path; BACKLOG_LOOP.md R5/R6).

Unlike the hand-picked shape matchers (``constant_output`` / ``object_motion`` /
``object_recolor``), which each recognise *one* transformation shape, this matcher
recognises a task by *outcome*: a value-agnostic program — built only from the two
frozen transformation primitives (``make_grid`` / ``coloring``) by
``program.synthesis.synthesize_task`` — **reproduces every example pair**. That is
the §2.5-2 discipline made into a recognition predicate: the program is the reason,
and a program either reproduces the examples or it does not.

It is the single, *general* recognition slot for the synthesizer, NOT a per-shape
detector — one matcher covers every program the search can find, so wiring the
synthesizer onto the live ``GeneralizeOperator`` path grows recognition by exactly
one entry (P5 +1) rather than one detector per task category (the §2.5-3 accretion
trap / arbor.md 진단 #1). It is consulted in two places:

* the Slow path (``GeneralizeOperator``) gates a freshly-synthesized program
  through it before saving the rule — recognition stays in the registry, mirroring
  how the family operators consult their own matchers rather than re-implementing
  the predicate;
* the Fast path can reuse a *stored* synthesized-program rule on a new task by
  checking that the stored program reproduces *that* task's examples (R5 reuse).

Reads:

    patterns["synthesis_pairs"] = [ {"input": grid, "output": grid}, ... ]

(the raw train pairs, surfaced by ``ExtractPatternOperator``), and the candidate
program from ``params["program"]``. Deterministic and side-effect-free: it only
*runs* the program against each input and compares to the output.
"""

from agent.conditions import register


@register("synthesized_program")
def synthesized_program(patterns: dict, params: dict | None = None) -> bool:
    """True iff ``params["program"]`` reproduces **every** example pair in
    ``patterns["synthesis_pairs"]`` (≥ ``min_evidence`` pairs, default 1).

    A miss on any pair, an empty program (that is identity — handled by the
    identity fallback, not a learned synthesizer rule), an unresolvable expression
    against some input, or no program/pairs at all → ``False``. The program runs
    on the *input* grids only (every variable originates in G0, P5), so a program
    that reproduces the train pairs applies unchanged to the test input.
    """
    if not isinstance(patterns, dict):
        return False
    params = params or {}
    program = params.get("program")
    if not program:  # None or [] (identity) — not a learned synthesizer rule
        return False

    pairs = patterns.get("synthesis_pairs")
    if not isinstance(pairs, list):
        return False
    min_evidence = params.get("min_evidence", 1)
    if len(pairs) < min_evidence:
        return False

    from program.synthesis import run_program, _Unevaluable

    for p in pairs:
        if not isinstance(p, dict) or "input" not in p or "output" not in p:
            return False
        try:
            if run_program(program, p["input"]) != p["output"]:
                return False
        except _Unevaluable:
            return False
    return True
