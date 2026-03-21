"""
viz.py — ANSI 색상 기반 KG 컴포넌트 시각화 유틸리티.
원본 색상 팔레트: ARC-solver/basics/utils.py  color_text()
원본 출력 방식: ARC-solver/basics/utils.py  print_multiple_grids / print_task_view

설계 원칙 (원본 그대로):
  - 레이블, 구분선, 인덱스 등 텍스트 없음
  - ANSI 색상 블록만 출력
  - 여러 그리드를 가로로 배치할 때 고정 공백(gap)만 사이에 삽입

공개 함수:
    show_task(task)             — 태스크 전체 (example + test) 시각화
    show_objects(grid)          — Grid 검출 object 목록 (5열 배치)
    show_comparison(a, b)       — 두 컴포넌트(Grid / Object / Pixel) 가로 비교
"""

# ---------------------------------------------------------------------------
# ANSI 색상 팔레트 (원본: ARC-solver/basics/utils.py)
# ---------------------------------------------------------------------------

_PALETTE = {
    0:  (0,   0,   0),
    1:  (0,   116, 217),
    2:  (255, 65,  54),
    3:  (46,  204, 64),
    4:  (255, 220, 0),
    5:  (170, 170, 170),
    6:  (240, 18,  190),
    7:  (255, 133, 27),
    8:  (127, 219, 255),
    9:  (135, 12,  37),
    10: (128, 0,   128),
    11: (0,   128, 128),
    12: (101, 67,  33),
    13: (214, 255, 255),
    14: (79,  79,  79),
}
_FALLBACK = (180, 180, 180)


def _cell(color: int) -> str:
    """단일 셀 → 2칸 ANSI 배경색 블록."""
    r, g, b = _PALETTE.get(color, _FALLBACK)
    return f"\033[48;2;{r};{g};{b}m  \033[0m"


def _render_row(row: list) -> str:
    """int 리스트 한 행 → ANSI 문자열."""
    return "".join(_cell(v) for v in row)


def _blank_row(cols: int) -> str:
    """cols 칸 너비의 빈 공백 행 (높이가 다른 그리드 패딩용)."""
    return " " * (cols * 2)


# ---------------------------------------------------------------------------
# 핵심 출력 헬퍼 (원본 print_multiple_grids 방식)
# ---------------------------------------------------------------------------

def _print_side_by_side(grids: list, gap: int = 4):
    """
    여러 2D int 배열을 가로로 나란히 출력한다.
    원본 print_multiple_grids와 동일한 방식:
      - 레이블·구분선 없음
      - 행 단위로 ANSI 문자열을 공백 gap으로 이어 붙임
      - 높이가 짧은 그리드는 빈 공백으로 패딩

    Args:
        grids: list of 2D int arrays
        gap:   그리드 사이 공백 문자 수
    """
    if not grids:
        return
    sep = " " * gap
    cols = [len(g[0]) if g and g[0] else 0 for g in grids]
    max_h = max((len(g) for g in grids if g), default=0)

    for row_idx in range(max_h):
        parts = []
        for grid, w in zip(grids, cols):
            if row_idx < len(grid):
                parts.append(_render_row(grid[row_idx]))
            else:
                parts.append(_blank_row(w))
        print(sep.join(parts))


def _extract_raw(component) -> list:
    """
    Grid / Object / Pixel 컴포넌트에서 2D int 배열 추출.
      Grid  → raw
      Object → colorgrid  (투명=13)
      Pixel  → [[color]]
    """
    if hasattr(component, "raw"):
        return component.raw
    if hasattr(component, "colorgrid"):
        return component.colorgrid
    if hasattr(component, "color"):
        return [[component.color]]
    return []


# ---------------------------------------------------------------------------
# 공개 함수 1: show_task
# ---------------------------------------------------------------------------

def show_task(task, gap: int = 6):
    """
    태스크 전체를 시각화한다.
    Example pair: input(좌)·output(우) 가로 배치, pair 사이에 빈 줄.
    Test pair:    input만 출력.

    원본 print_task_view 방식 그대로.
    """
    for i, pair in enumerate(task.example_pairs):
        if i > 0:
            print()
        grids = [pair.input_grid.raw]
        if pair.output_grid is not None:
            grids.append(pair.output_grid.raw)
        _print_side_by_side(grids, gap=gap)

    if task.example_pairs:
        print()

    for pair in task.test_pairs:
        _print_side_by_side([pair.input_grid.raw], gap=gap)


# ---------------------------------------------------------------------------
# 공개 함수 2: show_objects
# ---------------------------------------------------------------------------

def show_objects(grid, cols_per_row: int = 5, gap: int = 3):
    """
    Grid에서 검출된 object를 한 줄에 cols_per_row 개씩 가로 배치해 출력한다.
    각 object는 colorgrid(bbox 크기, 투명=어두운 회색)로 표시.
    """
    objects = getattr(grid, "objects", [])
    if not objects:
        return

    for batch_start in range(0, len(objects), cols_per_row):
        batch = objects[batch_start: batch_start + cols_per_row]
        _print_side_by_side([obj.colorgrid for obj in batch], gap=gap)
        print()


# ---------------------------------------------------------------------------
# 공개 함수 3: show_comparison
# ---------------------------------------------------------------------------

def show_comparison(a, b, gap: int = 6):
    """
    두 컴포넌트(Grid / Object / Pixel)를 가로로 나란히 출력한다.
    comparison 디버깅 시 사용.
    """
    raw_a = _extract_raw(a)
    raw_b = _extract_raw(b)
    if not raw_a and not raw_b:
        return
    _print_side_by_side([raw_a, raw_b], gap=gap)
