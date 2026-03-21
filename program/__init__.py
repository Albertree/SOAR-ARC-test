"""
program — 지식 추상화 패키지.

Public interface:
    anti_unify  — 여러 pair의 relation trace를 anti-unification으로 추상화
"""

from program.anti_unification import anti_unify

__all__ = ["anti_unify"]
