"""
managers — Task loading and ARCKG structure construction package.

Public interface:
    ARCManager  — Load tasks from data/ and build the ARCKG node structure
"""

from managers.arc_manager import ARCManager

__all__ = ["ARCManager"]
