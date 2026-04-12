"""
program — knowledge abstraction package.

Public interface:
    anti_unify        — anti-unify two ARCKG comparison results
    anti_unify_pairs  — anti-unify a list of comparison results
    extract_invariants — extract concrete invariant fields from AU result
"""

from program.anti_unification import anti_unify, anti_unify_pairs, extract_invariants

__all__ = ["anti_unify", "anti_unify_pairs", "extract_invariants"]
