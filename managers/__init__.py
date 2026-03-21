"""
managers — 태스크 로딩 및 ARCKG 구조 구축 패키지.

Public interface:
    ARCManager  — data/에서 태스크를 로드하고 ARCKG 노드 구조를 빌드
"""

from managers.arc_manager import ARCManager

__all__ = ["ARCManager"]
