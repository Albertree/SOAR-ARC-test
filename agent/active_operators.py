"""
active_operators — SOAR Operator 구현체.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[SOAR 강제] 각 operator는 precondition + effect 인터페이스를 따른다.
            effect는 WM을 갱신한다. cycle은 예외·wme 변화로 성공/실패/무변화를 판단.

[설계 자유] 어떤 operator를 둘지, 이름, precondition 조건, effect 내용.
            비교 함수(compare_fn)와 일반화 함수(generalize_fn)를 외부 주입 가능.

이 모듈의 operator들은 인지 수준에서 다음 여섯 연산에 대응하도록 설계된다.

    1. compare  (target_a, target_b, level)
    2. collect  (scope, relation_type)
    3. generalize(targets)
    4. descend  (target, from_level, to_level)
    5. predict  (test_input, rule_ref)
    6. verify   (predicted_output, constraints)

구체 클래스 간 매핑은 다음과 같다.

    - CompareOperator         → compare
    - ExtractPatternOperator  → collect
    - GeneralizeOperator      → generalize
    - DescendOperator         → descend
    - PredictOperator         → predict
    - SubmitOperator/VerifyOperator → verify

즉, SOAR 스타일의 Operator 인터페이스를 유지하면서,
사용자 관점의 고수준 operator 레퍼토리를 그대로 반영한다.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from agent.operators import Operator


class SolveTaskOperator(Operator):
    """
    [설계 자유] 최상위 ARC 태스크를 해결하기 위한 상위 수준 operator.

    INTENT:
        - (S1 ^current-task <hex>)가 있을 때, compare/collect/generalize/descend
          등의 하위 operator를 조직적으로 사용해 태스크를 푸는 역할.
        - 현재 단계에서는 구체 로직 없이 인터페이스(이름, 위치)만 확보한다.

    향후:
        - precondition: S1에 current-task가 있고 아직 goal이 완료되지 않았을 때.
        - effect: 한 decision cycle 동안 solve-task 파이프라인의 일부를 수행.
    """

    def __init__(self):
        super().__init__("solve-task")
        self.proposal_preference = "+"

    def precondition(self, wm) -> bool:
        """[설계 자유] 나중에 S1^current-task, goal 상태 등을 검사하도록 확장."""
        raise NotImplementedError("SolveTaskOperator.precondition() not implemented.")

    def effect(self, wm):
        """추상 오퍼레이터: intentionally no WM change.

        Soar 관점에서 solve-task는 상위 수준 목표만 제시하고,
        실제 상태 변화는 하위 substate(S2…)에서 구체 오퍼레이터들이 수행하게 둔다.
        따라서 여기서는 WM을 변경하지 않는다.
        """
        return


class SubstateProgressOperator(Operator):
    """
    [설계 자유] 서브스테이트에서 operator no-change 임패스를 풀기 위한 최소 result.

    상위 상태 S1에 짧은 요약 WME를 추가해, 이후 사이클에서 상위 WM이 변한 것을
    반영한다. (완전한 i-support retract 전 단계의 플레이스홀더.)
    """

    def __init__(self):
        super().__init__("substate-progress")
        self.proposal_preference = "+"

    def precondition(self, wm) -> bool:
        raise NotImplementedError(
            "SubstateProgressOperator.precondition() not implemented."
        )

    def effect(self, wm):
        attr = wm.active.get("attribute")
        wm.s1["substate-resolution"] = f"handled-no-change:{attr}"


class SelectTargetOperator(Operator):
    """
    [설계 자유] 이 operator의 존재, precondition, effect 전부.
    INTENT: (미구현) 비교 대상 선택 후 WM에 pending 비교 항목을 반영한다.
            agenda/pending 전용 dict·헬퍼는 사용하지 않는다.
            구체 비교 대상 타입은 알지 못한다.
    MUST NOT: 비교 자체를 수행하지 마 — pending 큐 이동만.
              wm.task를 직접 참조하지 마.
    precondition: elaborated["needs_target_selection"] == True
    """

    def __init__(self):
        super().__init__("select_target")

    def precondition(self, wm) -> bool:
        """[설계 자유]"""
        raise NotImplementedError("SelectTargetOperator.precondition() not implemented.")

    def effect(self, wm):
        """
        [설계 자유]
        1. 비교 대상 선택
        2. WM(triplet)에 pending 비교 사실 반영
        3. …
        4. op_status = "success" or "failure"
        """
        raise NotImplementedError("SelectTargetOperator.effect() not implemented.")


class CompareOperator(Operator):
    """
    [설계 자유] 이 operator의 존재, precondition, effect 전부.
    INTENT: 대기 중인 비교 한 건을 수행하고 결과를 WM에 triplet으로 추가한다.
            비교 함수는 외부 주입(compare_fn) 또는 기본값 사용.
            CompareOperator는 항목이 무엇인지 알지 못한다.
    MUST NOT: 큐에서 여러 항목을 한 번에 처리하지 마 — 1회 = 1 비교.
              특정 비교 라이브러리를 클래스에 하드코딩하지 마.
    precondition: elaborated["has_pending_comparison"] == True
    """

    def __init__(self, compare_fn=None):
        """
        [설계 자유] compare_fn: (node_a, node_b, context) → result.
                   None이면 기본 비교 함수 사용.
        """
        super().__init__("compare")
        self._compare_fn = compare_fn

    def precondition(self, wm) -> bool:
        """[설계 자유]"""
        raise NotImplementedError("CompareOperator.precondition() not implemented.")

    def effect(self, wm):
        """
        [설계 자유]
        1. pending 비교 항목 확보
        2. self._compare_fn(node_a, node_b, context) 호출
        3. WM에 비교 결과 반영 (triplet)
        4. op_status = "success" or "failure"
        """
        raise NotImplementedError("CompareOperator.effect() not implemented.")


class ExtractPatternOperator(Operator):
    """
    [설계 자유] 이 operator의 존재, precondition, effect 전부.
    INTENT: 비교 결과에서 COMM/DIFF 패턴을 WM triplet으로 정리한다.
            실패 시 deeper analysis용 목표를 WM에 반영.
    MUST NOT: COMM/DIFF 판단 로직을 여기서 구현하지 마 — result의 type 필드 읽기만.
    precondition: elaborated["ready_for_pattern_extraction"] == True
    """

    def __init__(self):
        super().__init__("extract_pattern")

    def precondition(self, wm) -> bool:
        """[설계 자유]"""
        raise NotImplementedError("ExtractPatternOperator.precondition() not implemented.")

    def effect(self, wm):
        """
        [설계 자유]
        compare/collect/generalize 파이프라인에서
        collect(scope, relation_type)에 해당하는 역할을 담당한다.

        1. 비교 결과 순회
        2. COMM/DIFF를 WM triplet으로 기록
        4. op_status = "success" or "failure"
        """
        raise NotImplementedError("ExtractPatternOperator.effect() not implemented.")


class DescendOperator(Operator):
    """
    [설계 자유] 이 operator의 존재, precondition, effect 전부.
    INTENT: GRID/OBJECT/PIXEL 등 상위 레벨 분석에서 impasse가 발생했을 때
            descend(target, from_level, to_level)을 구현하는 역할로,
            더 낮은 레벨의 노드/관계를 WM으로 끌어와 추가 비교를 가능하게 한다.

    이 연산은 SOAR 관점에서는 impasse 해소를 위한 substate 생성 또는
    comparison_agenda 확장으로 구현된다.

    예시 개념 흐름:
        - from_level 분석이 insufficient → elaborated["needs_descend"] = True
        - DescendOperator.effect:
            1) wm.push_substate(...) 또는
            2) 더 미시적 비교 과제를 WM에 반영

    precondition: elaborated["needs_descend"] == True (설계 선택)
    """

    def __init__(self):
        super().__init__("descend")

    def precondition(self, wm) -> bool:
        """[설계 자유]"""
        raise NotImplementedError("DescendOperator.precondition() not implemented.")

    def effect(self, wm):
        """
        [설계 자유]
        1. 현재 focus/impasse 정보를 읽어 from_level, to_level 해석
        2. 대상 pair/객체에 대해 더 낮은 레벨 비교 과제를 agenda에 추가하거나
           필요하다면 wm.push_substate(...)를 호출해 subgoal을 연다.
        3. op_status = "success" or "failure"
        """
        raise NotImplementedError("DescendOperator.effect() not implemented.")


class GeneralizeOperator(Operator):
    """
    [설계 자유] 이 operator의 존재, precondition, effect 전부.
    INTENT: WM에 모인 불변/차이 패턴을 일반화 함수에 전달해
            추상 규칙을 생성하고 wm.active_rules에 추가한다.
            일반화 함수와 LTM 저장 함수는 외부 주입 또는 기본값 사용.
    MUST NOT: 특정 일반화 모듈을 클래스에 하드코딩하지 마.
    precondition: elaborated["ready_for_generalization"] == True
    """

    def __init__(self, generalize_fn=None, save_fn=None):
        """
        [설계 자유] generalize_fn: (invariants, diff_patterns) → rule dict.
                   save_fn: rule dict → LTM ref str.
                   None이면 기본 구현 사용.
        """
        super().__init__("generalize")
        self._generalize_fn = generalize_fn
        self._save_fn = save_fn

    def precondition(self, wm) -> bool:
        """[설계 자유]"""
        raise NotImplementedError("GeneralizeOperator.precondition() not implemented.")

    def effect(self, wm):
        """
        [설계 자유]
        1. self._generalize_fn(불변·차이 정보)
        2. self._save_fn(rule) → LTM ref 경로
        3. wm.active_rules에 {"ref": path, "confidence": ...} 추가
        4. op_status = "success" or "failure"
        """
        raise NotImplementedError("GeneralizeOperator.effect() not implemented.")


class PredictOperator(Operator):
    """
    [설계 자유] 이 operator의 존재, precondition, effect 전부.
    INTENT: wm.active_rules 중 최고 confidence 규칙을 pending test subgoal에 적용해
            출력을 예측하고 goal.subgoals·found를 갱신한다.
    MUST NOT: 여러 규칙을 병렬로 시도하지 마 — 단일 결정적 예측.
    precondition: elaborated["ready_for_prediction"] == True
    """

    def __init__(self):
        super().__init__("predict")

    def precondition(self, wm) -> bool:
        """[설계 자유]"""
        raise NotImplementedError("PredictOperator.precondition() not implemented.")

    def effect(self, wm):
        """
        [설계 자유]
        1. pending test subgoal 하나 선택
        2. wm.active_rules 중 confidence 최고 규칙 선택
        3. 규칙을 test input에 적용 → output 도출
        4. 해당 test subgoal solved + found 기록
        5. op_status = "success" or "failure"
        """
        raise NotImplementedError("PredictOperator.effect() not implemented.")


class SubmitOperator(Operator):
    """
    [설계 자유] 이 operator의 존재와 precondition.
    [SOAR 강제] goal_satisfied 조건을 충족시키는 마지막 단계가 있어야 한다.
    INTENT: elaborated["all_outputs_found"] == True이면 op_status = "success" 설정.
    MUST NOT: 실제 채점을 수행하지 마 — ARCEnvironment 책임.
    precondition: elaborated["all_outputs_found"] == True
    """

    def __init__(self):
        super().__init__("submit")

    def precondition(self, wm) -> bool:
        """[설계 자유]"""
        raise NotImplementedError("SubmitOperator.precondition() not implemented.")

    def effect(self, wm):
        """
        [설계 자유]
        verify(predicted_output, constraints)에 대응하는 단계로,
        모든 test subgoal이 해결되었고(elaborated["all_outputs_found"])
        내부 제약 조건을 만족한다고 판단되면
        op_status = "success"로 설정해 goal_satisfied를 만족시킨다.
        """
        raise NotImplementedError("SubmitOperator.effect() not implemented.")


class VerifyOperator(SubmitOperator):
    """
    [설계 자유] verify 연산의 별칭(alias) operator.

    INTENT: 인지 수준에서의 verify(predicted_output, constraints)를
            SOAR operator 레벨에서 SubmitOperator와 동일한 메커니즘으로
            구현하되, 이름 차이를 통해 파이프라인을 더 명시적으로 표현한다.

    구현 상으로는 SubmitOperator를 상속해 동일한 precondition/effect를 사용한다.
    """

    def __init__(self):
        super().__init__()
        # 이름만 "verify"로 재설정해 PREFERENCE_ORDER 등에서 구분 가능하게 함.
        self.name = "verify"
