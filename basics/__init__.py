"""
basics — 수동 디버깅 및 검증 유틸 패키지.

Public interface:
    visualize_grid           — 격자 텍스트 시각화
    inspect_object_comparison — 두 Object 비교 결과 출력
    verify_object            — Object 속성 수동 검증
"""

from basics.utils import visualize_grid, inspect_object_comparison, verify_object

__all__ = ["visualize_grid", "inspect_object_comparison", "verify_object"]
