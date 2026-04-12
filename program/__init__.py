"""
program — knowledge abstraction package.

Modules:
    anti_unification — AU over ARCKG comparison result trees
    program_solver   — per-pair program solver using existing concepts
    program_au       — AU over programs (step lists)
    claude_au        — Claude-assisted program solving and concept generation
"""

from program.anti_unification import anti_unify, anti_unify_pairs, extract_invariants

__all__ = ["anti_unify", "anti_unify_pairs", "extract_invariants"]
