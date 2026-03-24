"""
basics — Manual debugging and verification utility package.

Public interface:
    visualize_grid           — Grid text visualization
    inspect_object_comparison — Display comparison result of two Objects
    verify_object            — Manual verification of Object attributes
"""

from basics.utils import visualize_grid, inspect_object_comparison, verify_object

__all__ = ["visualize_grid", "inspect_object_comparison", "verify_object"]
