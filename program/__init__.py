"""
program — knowledge abstraction package.

Public interface (docs/ANTI_UNIFICATION.md §1):
    unify            — lift rules sharing a skeleton into one abstract rule
    UnifyResult      — outcome carrying the abstract rule + trace path
    NoCommonSkeleton — raised when inputs share no unifiable skeleton
"""

from program.anti_unification import NoCommonSkeleton, UnifyResult, unify

__all__ = ["unify", "UnifyResult", "NoCommonSkeleton"]
