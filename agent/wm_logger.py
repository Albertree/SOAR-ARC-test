"""
wm_logger — WorkingMemory 상태를 SOAR triplet 형식으로 출력하는 유틸리티.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SOAR Working Memory Element(WME) 형식:
    (identifier ^attribute value)

    identifier : S1=루트, S2/S3…=서브스테이트, I1/I2…=자동생성 하위 노드
    attribute  : 필드명
    value      : 프리미티브 또는 하위 노드 identifier

diff 색상 (git diff 스타일):
    녹색 배경 + 흰 글자  →  이전 호출 대비 추가 / 변경된 WME
    붉은 배경 + 흰 글자  →  이전 호출 대비 제거된 WME
    일반                 →  변화 없는 WME

    비교는 auto-id(I1, I2…)가 아닌 path_key(S1/relations/pair_0/type 등) 기반으로
    수행되므로 identifier가 바뀌어도 의미 단위 diff가 정확하게 계산된다.

사용:
    from agent.wm_logger import print_wm_triplets, reset_wm_snapshot
    reset_wm_snapshot()                                 # 태스크 시작 전 스냅샷 초기화
    print_wm_triplets(wm, label="After: elaborate", step=3)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Any


# ── ANSI 색상 ────────────────────────────────────────────────────────── #

_GREEN_BG = "\033[42;37m"   # 녹색 배경, 흰색 글자 (추가/변경)
_RED_BG   = "\033[41;37m"   # 붉은 배경, 흰색 글자 (제거)
_RESET    = "\033[0m"

# 출력 폭: 색상 배경을 divider 너비에 맞게 채운다.
_LINE_WIDTH = 62


# ── 출력 상수 ────────────────────────────────────────────────────────── #

_L1      = "  "       # depth 0 (루트 식별자 S1/S2/WM) 줄 들여쓰기
_L2      = "    "     # depth 1 (직접 자식: I1 등) 들여쓰기
_L3      = "      "   # depth 2+ (손자 이하: I2, I3 등) 들여쓰기
_DIVIDER = "═" * _LINE_WIDTH

# S1·WM 계열 식별자 판별
_ROOT_IDS = {"S1", "S2", "S3", "S4", "WM"}

# 문자열 값 최대 표시 길이
_MAX_STR_LEN = 80


# ── WME 데이터 모델 ──────────────────────────────────────────────────── #

@dataclass(frozen=True)
class _WME:
    """
    하나의 Working Memory Element.

    identifier : 출력용 노드 ID (S1, I1, …)
    attribute  : 필드명
    value      : 포맷된 값 문자열
    path_key   : diff 비교용 정규 경로 (예: "S1/relations/pair_0/type")
    is_root    : identifier가 S1/WM 계열이면 True → L1 들여쓰기
    """
    identifier: str
    attribute:  str
    value:      str
    path_key:   str
    is_root:    bool
    depth:      int   # S1 기준 깊이 (0=S1, 1=자식, 2=손자…)


# ── 모듈 레벨 diff 상태 ──────────────────────────────────────────────── #

# {path_key: _WME} — 이전 print_wm_triplets 호출 시점의 스냅샷
_prev_snap: dict[str, _WME] = {}


def reset_wm_snapshot(wm=None) -> None:
    """
    diff 스냅샷을 초기화한다.

    wm=None  : 빈 스냅샷으로 초기화 → 다음 print_wm_triplets 호출 시 전체가 녹색
    wm=<WM>  : 현재 WM 상태로 스냅샷을 미리 채움
               → 다음 print_wm_triplets 호출은 변화가 없어 모두 일반 색으로 출력됨

    권장 사용 패턴:
        # run_task.py — 초기 WM 상태를 기준으로 diff 시작
        build_wm_from_task(task, wm)
        reset_wm_snapshot(wm)              # 초기 상태를 baseline으로 설정
        print_wm_triplets(wm, "Initial WM state")  # 색상 없이 현재 상태 출력

        # active_agent.solve() — 태스크 간 이전 상태가 섞이지 않도록
        reset_wm_snapshot()                # 태스크 시작 전 비어있는 상태로 리셋
    """
    global _prev_snap
    if wm is not None:
        entries    = _wm_as_entries(wm)
        _prev_snap = {e.path_key: e for e in entries}
    else:
        _prev_snap = {}


# ── 값 포맷팅 ────────────────────────────────────────────────────────── #

def _fmt(value: Any) -> str:
    """프리미티브 값을 SOAR 출력용 문자열로 변환한다."""
    if value is None:
        return "nil"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        # 선호 기호 등 Soar에서 bare로 쓰는 단일 문자
        if len(value) == 1 and value in "+-!~<>":
            return value
        # SOAR 스타일: 공백·특수문자 없는 심볼은 그대로, 그 외는 문자열로 취급해 따옴표.
        s = value if len(value) <= _MAX_STR_LEN else value[:_MAX_STR_LEN] + "…"
        if s and all(ch.isalnum() or ch in ("_", "-", ".") for ch in s):
            return s
        return f'"{s}"'
    return str(value)


def _is_grid(lst: list) -> bool:
    """2D 그리드처럼 생겼는지 판별한다 (정수 배열 또는 정수 배열의 배열)."""
    return bool(lst) and isinstance(lst[0], (int, list, tuple))


# ── WME 수집 (재귀) ──────────────────────────────────────────────────── #

def _collect(
    identifier:  str,
    attribute:   str,
    value:       Any,
    id_gen,
    out:         list[_WME],
    path_prefix: str,
    depth:       int,
    list_index:  int | None = None,
) -> None:
    """
    (identifier, attribute, value) 하나를 재귀 확장해 _WME 엔트리를 out에 추가한다.

    path_key 생성 규칙:
        일반 dict 필드: "{path_prefix}/{attribute}"
        리스트 내 항목: "{path_prefix}/{attribute}[{list_index}]"
    """
    if list_index is not None:
        path_key = f"{path_prefix}/{attribute}[{list_index}]"
    else:
        path_key = f"{path_prefix}/{attribute}"

    is_root = identifier in _ROOT_IDS

    if isinstance(value, dict):
        if not value:
            # 빈 dict도 별도 identifier(Ix)를 만들어 연결만 남긴다.
            # 예: (I1 ^output-link I3) 처럼 쓰이고, I3에는 아직 속성이 없다.
            child_id = next(id_gen)
            out.append(_WME(identifier, attribute, child_id, path_key, is_root, depth))
            return
        child_id = next(id_gen)
        out.append(_WME(identifier, attribute, child_id, path_key, is_root, depth))
        for child_attr, child_val in value.items():
            _collect(child_id, child_attr, child_val, id_gen, out, path_key, depth + 1)

    elif isinstance(value, list):
        if not value:
            out.append(_WME(identifier, attribute, "[]", path_key, is_root, depth))
            return
        if _is_grid(value):
            first = value[0]
            ncols = len(first) if isinstance(first, (list, tuple)) else 1
            out.append(_WME(
                identifier, attribute, f"<grid {len(value)}x{ncols}>",
                path_key, is_root, depth,
            ))
            return
        # 일반 리스트: 각 항목을 index 기반 path_key로 재귀 수집
        for idx, item in enumerate(value):
            _collect(identifier, attribute, item, id_gen, out, path_prefix, depth, list_index=idx)

    else:
        out.append(_WME(identifier, attribute, _fmt(value), path_key, is_root, depth))


# ── WM → WME 목록 변환 ───────────────────────────────────────────────── #

def _wm_as_entries(wm) -> list[_WME]:
    """WorkingMemory 전체를 _WME 목록으로 변환한다."""
    id_gen = (f"I{n}" for n in itertools.count(1))
    out: list[_WME] = []

    # S1 (루트 상태)
    root = "S1"
    for attr, val in wm.s1.items():
        # 오퍼레이터 등 별도 식별자 노드는 S1의 속성이 아니라
        # 독립 identifier로 취급한다 (예: O1).
        if isinstance(val, dict) and attr[:1].isalpha() and attr[0].isupper():
            for child_attr, child_val in val.items():
                _collect(attr, child_attr, child_val, id_gen, out, attr, depth=0)
            continue
        _collect(root, attr, val, id_gen, out, root, depth=0)

    # task는 WM 밖(파이썬 레벨)의 외부 참조이므로 요약만 출력한다.
    # SOAR 스타일에서는 환경 입력은 io/input-link 아래로 들어가야 하므로
    # 여기 값은 디버그 용도로만 유지한다.
    if getattr(wm, "task", None) is not None:
        summary = getattr(wm.task, "task_hex", repr(wm.task))
        out.append(_WME(root, "task_ref", f"<task {summary}>", f"{root}/task_ref", True, 0))

    # S2, S3, … (서브스테이트 스택) — 각 substate는 독립된 Sx identifier로만 표현한다.
    for depth, substate in enumerate(wm._substate_stack, start=2):
        sub = f"S{depth}"
        for attr, val in substate.items():
            # S1과 동일: O* 연산자 노드는 독립 identifier로 펼친다.
            if isinstance(val, dict) and attr[:1].isalpha() and attr[0].isupper():
                for child_attr, child_val in val.items():
                    _collect(attr, child_attr, child_val, id_gen, out, attr, depth=0)
                continue
            _collect(sub, attr, val, id_gen, out, sub, depth=0)

    return out


# ── 줄 포맷팅 + 색상 ─────────────────────────────────────────────────── #

def _indent_for_depth(depth: int) -> str:
    """depth 값에 따른 들여쓰기 문자열을 반환한다."""
    if depth <= 0:
        return _L1
    if depth == 1:
        return _L2
    return _L3


def _render(entry: _WME) -> str:
    """_WME 하나를 `  (S1 ^attr val)` 형태의 문자열로 변환한다."""
    indent = _L1 if entry.is_root else _L2
    return f"{indent}({entry.identifier} ^{entry.attribute} {entry.value})"


def _op_preference_map_current(current_entries: list[_WME]) -> dict[str, str]:
    """현재 WM에만 존재하는 O*의 op-preference (제거된 WME 목록과 섞이면 안 됨)."""
    d: dict[str, str] = {}
    for e in current_entries:
        if (
            len(e.identifier) >= 2
            and e.identifier[0] == "O"
            and e.identifier[1:].isdigit()
            and e.attribute == "op-preference"
        ):
            d[e.identifier] = e.value.strip()
    return d


def _grouped_lines(
    entries: list[_WME],
    *,
    op_preference_map: dict[str, str],
) -> list[tuple[str, str | None]]:
    """
    SOAR 디버그 출력 스타일에 가깝게, 같은 identifier의 WME들을 하나의 블록으로 묶는다.

    op_preference_map: 현재 WM만으로 계산한 것 (display_entries에 제거분이 섞여도 + 오염 방지).
    """
    if not entries:
        return []

    op_preference = op_preference_map

    # identifier 별로 모든 WME를 모은다 (연속 여부와 무관하게).
    by_id: dict[str, list[_WME]] = {}
    order: list[str] = []
    for e in entries:
        if e.identifier not in by_id:
            by_id[e.identifier] = []
            order.append(e.identifier)
        by_id[e.identifier].append(e)

    # O* 블록에서는 ^op-preference는 S1 줄에 합쳐 보이므로 별도 줄 생략
    for oid, group in list(by_id.items()):
        if oid.startswith("O") and len(oid) >= 2 and oid[1:].isdigit():
            by_id[oid] = [w for w in group if w.attribute != "op-preference"]

    # 출력 순서: S1, 연산자(O*), S2/S3/S4, WM, 그 다음 나머지 identifier 들.
    def id_priority(ident: str) -> tuple[int, str]:
        if ident == "S1":
            return (0, ident)
        if ident.startswith("O"):
            return (1, ident)
        if ident in {"S2", "S3", "S4"}:
            return (2, ident)
        if ident == "WM":
            return (3, ident)
        return (4, ident)

    sorted_ids = sorted(order, key=id_priority)

    # S1: 제안 ^operator O* + 다음에 공식 ^operator O* (operator-application)
    _S1_ORDER = (
        "type",
        "superstate",
        "io",
        "smem",
        "epmem",
        "current-task",
        "operator",
        "operator-application",
    )

    # S2, S3, … (substate) — smem → epmem 순 고정
    _SUBSTATE_ORDER = (
        "type",
        "superstate",
        "impasse",
        "choices",
        "attribute",
        "quiescence",
        "operator",
        "operator-application",
        "smem",
        "epmem",
        "item",
        "item-count",
        "non-numeric",
        "non-numeric-count",
    )

    def _s1_sort_key(e: _WME) -> tuple[int, str]:
        try:
            return (_S1_ORDER.index(e.attribute), e.attribute)
        except ValueError:
            return (len(_S1_ORDER), e.attribute)

    def _substate_sort_key(e: _WME) -> tuple[int, str]:
        try:
            return (_SUBSTATE_ORDER.index(e.attribute), e.path_key)
        except ValueError:
            return (len(_SUBSTATE_ORDER), e.path_key)

    def _is_substate_ident(ident: str) -> bool:
        return (
            len(ident) >= 2
            and ident[0] == "S"
            and ident != "S1"
            and ident[1:].isdigit()
        )

    def _s1_show_attr(attr: str) -> str:
        return "operator" if attr == "operator-application" else attr

    lines: list[tuple[str, str | None]] = []

    for ident in sorted_ids:
        group = by_id[ident]
        if not group:
            continue
        if ident == "S1":
            group = sorted(group, key=_s1_sort_key)
        elif _is_substate_ident(ident):
            group = sorted(group, key=_substate_sort_key)

        first = group[0]
        base_indent = _indent_for_depth(first.depth)
        cont_indent = base_indent + (" " * (len(ident) + 2))

        def _proposal_suffix(e: _WME) -> str:
            if ident != "S1" or e.attribute != "operator":
                return ""
            sym = op_preference.get(e.value)
            return f" {sym}" if sym else ""

        if ident == "S1":
            if len(group) == 1:
                e0 = group[0]
                a = _s1_show_attr(e0.attribute)
                text = f"{base_indent}({ident} ^{a} {e0.value}{_proposal_suffix(e0)})"
                lines.append((text, e0.path_key))
            else:
                e0 = group[0]
                a0 = _s1_show_attr(e0.attribute)
                first_text = f"{base_indent}({ident} ^{a0} {e0.value}{_proposal_suffix(e0)}"
                lines.append((first_text, e0.path_key))
                for k in range(1, len(group) - 1):
                    e = group[k]
                    a = _s1_show_attr(e.attribute)
                    mid = f"{cont_indent}^{a} {e.value}{_proposal_suffix(e)}"
                    lines.append((mid, e.path_key))
                el = group[-1]
                al = _s1_show_attr(el.attribute)
                last_text = f"{cont_indent}^{al} {el.value}{_proposal_suffix(el)})"
                lines.append((last_text, el.path_key))
            continue

        if len(group) == 1:
            text = f"{base_indent}({ident} ^{first.attribute} {first.value})"
            lines.append((text, first.path_key))
        else:
            first_text = f"{base_indent}({ident} ^{first.attribute} {first.value}"
            lines.append((first_text, first.path_key))
            for k in range(1, len(group) - 1):
                e = group[k]
                lines.append((f"{cont_indent}^{e.attribute} {e.value}", e.path_key))
            last = group[-1]
            lines.append((f"{cont_indent}^{last.attribute} {last.value})", last.path_key))

    return lines

def _render_removed(entry: _WME) -> str:
    """
    제거된 WME를 path_key 기반 식별자로 표시한다.

    entry.identifier / attribute / depth 정보를 활용해
    일반 출력과 동일한 들여쓰기를 유지한다.
    """
    base_indent = _indent_for_depth(entry.depth)
    return f"{base_indent}({entry.identifier} ^{entry.attribute} {entry.value})"


def _colorize(text: str, ansi: str) -> str:
    """text를 _LINE_WIDTH 폭으로 패딩한 뒤 ANSI 배경색으로 감싼다."""
    padded = text.ljust(_LINE_WIDTH)
    return f"{ansi}{padded}{_RESET}"


# ── 공개 출력 함수 ───────────────────────────────────────────────────── #

def print_wm_triplets(wm, label: str = "", step: int = 0) -> None:
    """
    WorkingMemory 전체 상태를 SOAR triplet 형식 + git diff 스타일 색상으로 출력한다.

    출력 규칙:
        녹색 배경  → 이전 스냅샷 대비 새로 추가되거나 값이 바뀐 WME
        붉은 배경  → 이전 스냅샷에 있었지만 현재는 없는 WME  (removed 섹션)
        일반 텍스트 → 변화 없는 WME

    첫 번째 호출 시 _prev_snap이 비어 있으므로 모든 항목이 녹색으로 표시된다.
    태스크가 바뀔 때는 reset_wm_snapshot()으로 스냅샷을 초기화해야 한다.
    """
    global _prev_snap

    entries   = _wm_as_entries(wm)
    curr_snap = {e.path_key: e for e in entries}

    # ── diff 계산 ─────────────────────────────────────────────────── #
    added_keys = {
        k for k, e in curr_snap.items()
        if k not in _prev_snap or _prev_snap[k].value != e.value
    }
    removed = {
        k: e for k, e in _prev_snap.items()
        if k not in curr_snap
    }

    # ── 헤더 ──────────────────────────────────────────────────────── #
    header = f"[Step {step}] {label}" if label else f"[Step {step}]"
    print(_DIVIDER)
    print(f"{_L1}{header}")
    print(_DIVIDER)

    # ── 현재 상태 + 제거된 항목을 함께 출력 (identifier별 묶음) ────── #
    # 디스플레이용 엔트리: 현재 엔트리 + 제거된 엔트리(중복 path_key는 현재가 우선)
    display_entries: list[_WME] = list(entries)
    for k, e in removed.items():
        if k not in curr_snap:
            display_entries.append(e)

    op_pref = _op_preference_map_current(entries)
    for text, path_key in _grouped_lines(display_entries, op_preference_map=op_pref):
        if path_key is not None:
            if path_key in removed:
                print(_colorize(text, _RED_BG))
                continue
            if path_key in added_keys:
                print(_colorize(text, _GREEN_BG))
                continue
        print(text)

    # ── 푸터 ──────────────────────────────────────────────────────── #
    print(_DIVIDER)
    print()

    # ── 스냅샷 갱신 ───────────────────────────────────────────────── #
    _prev_snap = curr_snap
