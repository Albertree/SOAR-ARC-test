"""
memory — SOAR Chunking 및 LTM 저장.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[SOAR 강제] Chunking은 subgoal이 해결된 시점에 트리거된다.
            reasoning trace → production rule로 압축된다.

[설계 자유] 압축된 production rule의 형태.
            LTM에 저장하는 형식 (ARCKG edge JSON 등).
            load 타이밍과 방식.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


def chunk_from_substate(substate: dict) -> dict:
    """
    [SOAR 강제] subgoal 해결 시 chunking이 트리거된다.
    [설계 자유] 압축 결과(rule dict)의 형태.
               trigger, ops_applied, result, confidence 등.
    MUST NOT: 실패한 substate를 chunk하지 마.
    """
    raise NotImplementedError("chunk_from_substate() not implemented.")


def save_rule_to_ltm(rule: dict, task_hex: str,
                     semantic_memory_root: str) -> str:
    """
    [설계 자유] LTM에 rule을 어떤 형식으로 저장할지.
               저장 경로: semantic_memory/N_T{hex}/E_rule_{n}.json
               반환값: ref 경로 (active_rules에 사용).
    MUST NOT: 기존 rule 파일을 덮어쓰지 마 — n 증가로 새 파일 생성.
    """
    raise NotImplementedError("save_rule_to_ltm() not implemented.")


def load_rules_from_ltm(task_hex: str, semantic_memory_root: str) -> list:
    """
    [설계 자유] LTM에서 rule을 읽어 active_rules 형식으로 반환.
               형식: [{"ref": path, "confidence": float, "rule": dict}, ...]
    MUST NOT: solve 루프 내부에서 호출하지 마 — solve() 시작 전 1회만.
    REF: CLAUDE.md § Memory System Design Target (LTM → WM: one load at session start)
    """
    raise NotImplementedError("load_rules_from_ltm() not implemented.")
