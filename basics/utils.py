"""
utils — 수동 디버깅, 격자 시각화, 오브젝트 검증 유틸.
"""


def visualize_grid(grid, label: str = "") -> str:
    """
    INTENT: Grid 또는 TFGrid의 raw 격자를 색상별 문자로 변환해
            사람이 읽기 쉬운 텍스트 표현을 반환한다.
            label이 있으면 헤더에 표시한다.
    MUST NOT: 파일에 저장하지 마 — 출력용 문자열 반환만.
    REF: ARC-solver/basics/utils.py printcg (line 32)
         ARC-solver/basics/utils.py color_text (line 7)
         ARC-solver/basics/utils.py rgb (line 1)
    """
    pass


def inspect_object_comparison(obj_a, obj_b, comparison_result: dict) -> str:
    """
    INTENT: 두 Object와 그 비교 결과를 나란히 보여주는 텍스트 표현을 반환한다.
            디버깅 시 어떤 속성이 COMM/DIFF인지 수동으로 확인하는 데 사용.
    MUST NOT: compare()를 내부에서 호출하지 마 — 결과를 인자로 받는다.
    REF: ARCKG/comparison.py compare()
    """
    pass


def verify_object(obj, grid) -> bool:
    """
    INTENT: Object의 mask와 bounding_box가 Grid의 raw 격자와 일치하는지 수동 검증.
            불일치하면 False와 함께 불일치 위치를 stdout에 출력한다.
    MUST NOT: Object나 Grid를 수정하지 마.
    REF: ARCKG/object.py Object, ARCKG/grid.py Grid
    """
    pass


def print_comparison_tree(comparison_result: dict, indent: int = 0):
    """
    INTENT: compare()의 중첩 결과 dict를 들여쓰기 트리 형태로 출력한다.
    MUST NOT: 결과를 수정하지 마 — 읽기 전용 출력.
    REF: ARC-solver/ARCKG/comparison.py get_comparison_data (line 547)
    """
    pass
