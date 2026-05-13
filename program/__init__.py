"""
program — knowledge abstraction package.

Public interface (see ``docs/ANTI_UNIFICATION.md`` for details):

    unify(rules)        anti-unify ≥ 2 rules into an abstract rule
    UnifyResult         return type of unify()
    NoCommonSkeleton    raised when inputs share no common skeleton
"""

from program.anti_unification import NoCommonSkeleton, UnifyResult, unify

__all__ = ["NoCommonSkeleton", "UnifyResult", "unify"]
