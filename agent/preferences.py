"""
preferences — Operator selection priority.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[SOAR MANDATORY] In the Select phase, one operator must be selected.
                 A selection criterion is needed when there are multiple candidates.

[DESIGN FREE] PREFERENCE_ORDER content (in what order to prioritize).
              It is also possible to change from hard-coded order to dynamic WM state-based decisions.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

# [DESIGN FREE] Priority order. Must match operator.name.
# Pipeline order: select_target/compare (compare phase) →
#                 extract_pattern (collect phase) →
#                 generalize →
#                 descend (for impasse resolution, prioritized when generalize fails) →
#                 predict →
#                 verify/submit
PREFERENCE_ORDER: list = [
    "solve-task",
    "substate-progress",  # Record result to superstate (S1) during impasse in S2+ operator no-change, etc.
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
    [SOAR MANDATORY] Select phase — must select exactly one or return None (impasse).
    [DESIGN FREE] Selection criterion (based on PREFERENCE_ORDER or other strategy).
    MUST NOT: Do not use random selection — deterministic selection.
              Use candidates list order as tiebreak when ranks are equal.
    """
    if not candidates:
        return None
    rank = {name: i for i, name in enumerate(PREFERENCE_ORDER)}

    def sort_key(op: object) -> tuple[int, int]:
        name = getattr(op, "name", "") or ""
        return (rank.get(name, 10_000), candidates.index(op))

    return min(candidates, key=sort_key)
