"""
program — knowledge abstraction package.

Public interface:
    unify  — lift ≥2 canonical rules sharing a skeleton into one abstract rule
             (R3, CLAUDE.md §8). The only permitted call site is
             agent/memory.py:save_rule().
"""

from program.anti_unification import unify

__all__ = ["unify"]
