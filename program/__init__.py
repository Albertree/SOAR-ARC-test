"""
program — knowledge abstraction package.

Public interface (docs/ANTI_UNIFICATION.md §1):
    unify            — lift ≥2 skeleton-sharing rules into one abstract rule
    UnifyResult      — the result object (.abstract_rule / .trace_path / ...)
    NoCommonSkeleton — raised when the inputs cannot be anti-unified
    anti_unify       — back-compat alias for unify
"""

from program.anti_unification import (
    unify,
    UnifyResult,
    NoCommonSkeleton,
    anti_unify,
)

__all__ = ["unify", "UnifyResult", "NoCommonSkeleton", "anti_unify"]
