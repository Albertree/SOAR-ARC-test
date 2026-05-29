"""
program — knowledge abstraction package.

Public interface (anti-unification, CLAUDE.md §8 — module H, currently stubs):
    anti_unify_pair_programs  — generalize multiple pair programs into one
                                task-level abstract program (top-level entry)
    program_lines_to_terms    — program lines  -> term-tree structure
    anti_unify_terms          — recursively anti-unify two terms
    terms_to_program_lines    — term list -> program-line format
"""

from program.anti_unification import (
    anti_unify_pair_programs,
    anti_unify_terms,
    program_lines_to_terms,
    terms_to_program_lines,
)

__all__ = [
    "anti_unify_pair_programs",
    "anti_unify_terms",
    "program_lines_to_terms",
    "terms_to_program_lines",
]
