"""
memory — SOAR Chunking and LTM storage.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[SOAR MANDATORY] Chunking is triggered when a subgoal is resolved.
                 reasoning trace → compressed into a production rule.

[DESIGN FREE] Form of the compressed production rule.
              Format for storing in LTM (ARCKG edge JSON, etc.).
              Load timing and method.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


def chunk_from_substate(substate: dict) -> dict:
    """
    [SOAR MANDATORY] Chunking is triggered when a subgoal is resolved.
    [DESIGN FREE] Form of the compression result (rule dict).
                  trigger, ops_applied, result, confidence, etc.
    MUST NOT: Do not chunk a failed substate.
    """
    raise NotImplementedError("chunk_from_substate() not implemented.")


def save_rule_to_ltm(rule: dict, task_hex: str,
                     semantic_memory_root: str) -> str:
    """
    [DESIGN FREE] In what format to save the rule to LTM.
                  Save path: semantic_memory/N_T{hex}/E_rule_{n}.json
                  Return value: ref path (used in active_rules).
    MUST NOT: Do not overwrite existing rule files — create new files by incrementing n.
    """
    raise NotImplementedError("save_rule_to_ltm() not implemented.")


def load_rules_from_ltm(task_hex: str, semantic_memory_root: str) -> list:
    """
    [DESIGN FREE] Read rules from LTM and return in active_rules format.
                  Format: [{"ref": path, "confidence": float, "rule": dict}, ...]
    MUST NOT: Do not call inside the solve loop — only once before solve() starts.
    REF: CLAUDE.md § Memory System Design Target (LTM → WM: one load at session start)
    """
    raise NotImplementedError("load_rules_from_ltm() not implemented.")
