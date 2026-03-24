"""
env — evaluation environment package.

Public interface:
    ARCEnvironment  — task provisioning, scoring, time budget, and trace management
"""

from arc2_env.arc_environment import ARCEnvironment

__all__ = ["ARCEnvironment"]
