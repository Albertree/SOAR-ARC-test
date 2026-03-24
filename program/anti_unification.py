"""
anti_unification — generalize pair programs into a task-level abstract program.
"""


def anti_unify_pair_programs(pair_programs: list[list[dict]]) -> list[dict]:
    """
    INTENT: Take flat program lists from multiple pairs, perform anti-unification,
            and return a list of abstract program lines containing ?vN variables.
            Flow: program_lines_to_terms -> _align_term_lists_dp -> anti_unify_terms
                  -> terms_to_program_lines
    MUST NOT: Do not force-merge two pair programs when they are structurally different
              — mismatches are generalized as ?vN.
    REF: CLAUDE.md § Anti-unification
         ARC-solver/program_gen/anti_unification.py
    """
    pass


def program_lines_to_terms(program_lines: list[dict]) -> list[dict]:
    """
    INTENT: Convert a list of program lines into a term tree structure for use in anti-unification.
    MUST NOT: Do not modify the original program_lines — return a new structure.
    REF: CLAUDE.md § Anti-unification
         ARC-solver/program_gen/anti_unification.py program_lines_to_terms (line 30)
         ARC-solver/program_gen/anti_unification.py _parse_apply_dsl_args (line 86)
    """
    pass


def _align_term_lists_dp(terms_a: list, terms_b: list,
                          context_bonus: dict = None) -> list[tuple]:
    """
    INTENT: Align two term lists using DP-based sequence alignment.
            context_bonus provides bonus scores when func names match in .context.json.
            PAIR component comparison results can also be used as alignment bonuses.
    MUST NOT: Do not cache alignment results in global state.
    REF: CLAUDE.md § Anti-unification
         ARC-solver/program_gen/anti_unification.py _align_term_lists_dp
    """
    pass


def anti_unify_terms(term_a: dict, term_b: dict,
                     var_counter: list) -> dict:
    """
    INTENT: Recursively anti-unify two terms.
            If the structures match, process sub-items recursively; if they differ, replace with a ?vN variable.
            var_counter is a mutable counter of the form [int] (for sharing variable numbers).
    MUST NOT: Do not force-unify terms of different types.
    REF: CLAUDE.md § Anti-unification
         ARC-solver/program_gen/anti_unification.py anti_unify_terms
    """
    pass


def terms_to_program_lines(terms: list[dict]) -> list[dict]:
    """
    INTENT: Convert the term list resulting from anti_unify_terms back into program line format.
    MUST NOT: Do not substitute ?vN variables with concrete values.
    REF: ARC-solver/program_gen/anti_unification.py
    """
    pass
