"""
preferences — 오퍼레이터 선택 우선순위.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[SOAR 강제] Select 단계에서 하나의 operator가 선택되어야 한다.
            여러 후보가 있을 때 선택 기준이 필요하다.

[설계 자유] PREFERENCE_ORDER 내용 (어떤 순서로 우선시할지).
            순서를 하드코딩이 아닌 WM 상태 기반 동적 결정으로 바꾸는 것도 가능.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

# [설계 자유] 우선순위 순서. operator.name과 일치해야 한다.
# 파이프라인 순서: select_target/compare(compare 단계) →
#                 extract_pattern(collect 단계) →
#                 generalize →
#                 descend(impasse 해소용, generalize 실패 시 우선) →
#                 predict →
#                 verify/submit
PREFERENCE_ORDER: list = [
    "solve-task",
    "substate-progress",  # S2+ operator no-change 등 임패스에서 상위(S1)에 result 기록
    "select_target",
    "compare",
    "extract_pattern",
    "generalize",
    "descend",
    "predict",
    "verify",
    "submit",
]


def select_operator(candidates: list, wm) -> object:
    """
    [SOAR 강제] Select 단계 — 반드시 하나를 선택하거나 None(impasse)을 반환.
    [설계 자유] 선택 기준 (PREFERENCE_ORDER 순서 기반 또는 다른 전략).
    MUST NOT: 무작위 선택을 사용하지 마 — 결정적 선택.
              동순위 발생 시 candidates 목록 순서를 tiebreak로 사용.
    """
    if not candidates:
        return None
    rank = {name: i for i, name in enumerate(PREFERENCE_ORDER)}

    def sort_key(op: object) -> tuple[int, int]:
        name = getattr(op, "name", "") or ""
        return (rank.get(name, 10_000), candidates.index(op))

    return min(candidates, key=sort_key)
