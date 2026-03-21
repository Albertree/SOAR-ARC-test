"""
anti_unification — pair 프로그램들을 태스크 레벨 추상 프로그램으로 일반화.
"""


def anti_unify_pair_programs(pair_programs: list[list[dict]]) -> list[dict]:
    """
    INTENT: 여러 pair의 flat 프로그램 목록을 받아 anti-unification을 수행하고
            ?vN 변수가 포함된 추상 프로그램 라인 목록을 반환한다.
            흐름: program_lines_to_terms → _align_term_lists_dp → anti_unify_terms
                  → terms_to_program_lines
    MUST NOT: 두 pair 프로그램이 구조적으로 다를 때 강제로 합치지 마
              — 불일치는 ?vN으로 일반화.
    REF: CLAUDE.md § Anti-unification
         ARC-solver/program_gen/anti_unification.py
    """
    pass


def program_lines_to_terms(program_lines: list[dict]) -> list[dict]:
    """
    INTENT: 프로그램 라인 목록을 anti-unification에 사용할 term 트리 구조로 변환.
    MUST NOT: 원본 program_lines를 변경하지 마 — 새 구조 반환.
    REF: CLAUDE.md § Anti-unification
         ARC-solver/program_gen/anti_unification.py program_lines_to_terms (line 30)
         ARC-solver/program_gen/anti_unification.py _parse_apply_dsl_args (line 86)
    """
    pass


def _align_term_lists_dp(terms_a: list, terms_b: list,
                          context_bonus: dict = None) -> list[tuple]:
    """
    INTENT: DP 기반 sequence alignment로 두 term 목록을 정렬한다.
            context_bonus는 .context.json의 func name 일치 시 보너스 점수를 제공.
            PAIR component comparison 결과도 alignment bonus로 사용 가능.
    MUST NOT: 정렬 결과를 전역 상태로 캐시하지 마.
    REF: CLAUDE.md § Anti-unification
         ARC-solver/program_gen/anti_unification.py _align_term_lists_dp
    """
    pass


def anti_unify_terms(term_a: dict, term_b: dict,
                     var_counter: list) -> dict:
    """
    INTENT: 두 term을 재귀적으로 anti-unify한다.
            구조가 같으면 하위 항목을 재귀적으로 처리, 다르면 ?vN 변수로 대체.
            var_counter는 [int] 형태의 mutable counter (변수 번호 공유용).
    MUST NOT: 타입이 다른 term을 강제로 unify하지 마.
    REF: CLAUDE.md § Anti-unification
         ARC-solver/program_gen/anti_unification.py anti_unify_terms
    """
    pass


def terms_to_program_lines(terms: list[dict]) -> list[dict]:
    """
    INTENT: anti_unify_terms 결과 term 목록을 다시 프로그램 라인 형식으로 변환.
    MUST NOT: ?vN 변수를 구체값으로 치환하지 마.
    REF: ARC-solver/program_gen/anti_unification.py
    """
    pass
