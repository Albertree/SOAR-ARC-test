"""
WorkingMemory — SOAR Working Memory.

One of SOAR's four components.
  WM              ← The entire current problem state (this file)
  Production Memory ← elaboration_rules.py + rules.py
  Operators         ← operators.py + active_operators.py
  Cycle             ← cycle.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[SOAR MANDATORY] WM must exist.
                 All content is represented as (identifier, attribute, value) triplets.
                 Has an S1 (root) / S2 (substate) hierarchical structure.

Dedicated dict slots such as comparison queue, relations, elaborated and WM helpers
that fill them are not provided.
Knowledge is extended only by triplets/operators adding directly.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

────────────────────────────────────────────────────────────────
[Design note — Soar WM vs this class's fields]  (Reference for future cleanup)

Conceptually, Soar WM is only a **set of WMEs**, and wme_records (+ timetag) correspond to that data.
In the Python implementation, **manager-role** fields are attached to operate on the set.

• Recommended to keep (nearly essential for engine/cycle)
  - _timetag_seq : Issues a unique, monotonically increasing timetag per WME (Soar 4 components)
  - _substate_stack : Substate stack on impasse — rule evaluation order (superstate → most recent substate)
  - wme_timetags : Slot-level latest timetag index, since iterating the set alone can be slow

• Can be considered for removal/replacement during refactoring (convenience/cache)
  - s1 : S1 is merely an identifier in the WME graph, but keeping it as a "root pointer" simplifies implementation.
         Can be replaced with entry point search if using a pure graph.
  - task : Cache outside WM. In pure Soar, could be eliminated by accessing only through graph traversal like input-link.

This class serves dual roles: "WM data set" + "managing that set and driving the cycle".
────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import copy
import itertools
from typing import Any

MAX_SUBSTATE_DEPTH: int = 2

# Top-level slots to protect by default in SOAR style
_RESERVED_TOP_KEYS = frozenset({"io"})


def _is_operator_id(key: str) -> bool:
    return bool(key) and key[0] == "O" and key[1:].isdigit()


class _TrackedS1(dict):
    """
    Records timetag when a top-level key is assigned to S1.
    When an operator node dict (O1/O2...) is inserted as a whole, records each sub-key separately.
    """

    __slots__ = ("_wm",)

    def __init__(self, wm: "WorkingMemory", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._wm = wm

    def __setitem__(self, key: str, value: Any) -> None:
        super().__setitem__(key, value)
        self._wm._record_wme("S1", key, value)
        if isinstance(value, dict) and _is_operator_id(key):
            for sk, sv in value.items():
                self._wm._record_wme(key, sk, sv)


class WorkingMemory:
    """
    [SOAR MANDATORY] WM class must exist.
                     S1/S2 hierarchy and triplet access interface (get/set) are SOAR protocol.
    """

    def __init__(self):
        # Soar timetag: integer that increases in WME creation order (not printed in logger)
        self._timetag_seq = itertools.count(1)
        # Full history (for debugger/print(wm.wme_records))
        self.wme_records: list[dict[str, Any]] = []
        # (identifier, attribute) -> latest timetag
        self.wme_timetags: dict[str, int] = {}

        self.s1 = _TrackedS1(self)
        self.s1["type"] = "state"
        self.s1["superstate"] = None
        self.s1["io"] = {
            "input-link": {},
            "output-link": {},
        }
        # States can be connected to semantic memory/episodic memory modules.
        # The detailed protocol is not yet defined, so only id is kept as placeholder.
        self.s1["smem"] = {"id": "SM1"}
        self.s1["epmem"] = {"id": "E1"}

        self.task = None
        self._substate_stack: list = []

    def _record_wme(self, identifier: str, attribute: str, value: Any) -> int:
        """Internal: assigns a timetag to a triplet (output is not done by wm_logger)."""
        tt = next(self._timetag_seq)
        key = f"{identifier}^{attribute}"
        self.wme_timetags[key] = tt
        self.wme_records.append(
            {
                "timetag": tt,
                "identifier": identifier,
                "attribute": attribute,
                "value": value,
            }
        )
        return tt

    def register_wme(self, identifier: str, attribute: str, value: Any) -> int:
        """
        Used to manually record a timetag for paths other than S1 (e.g., input-link.task).
        """
        return self._record_wme(identifier, attribute, value)

    @property
    def active(self) -> dict:
        return self._substate_stack[-1] if self._substate_stack else self.s1

    @property
    def depth(self) -> int:
        return len(self._substate_stack)

    def get(self, key: str):
        return self.active.get(key)

    def set(self, key: str, value):
        if key in _RESERVED_TOP_KEYS:
            raise ValueError(
                f"WorkingMemory.set: Do not directly set '{key}'."
            )
        self.active[key] = value

    def get_list(self, key: str) -> list:
        v = self.active.get(key)
        return v if isinstance(v, list) else []

    def push_substate(
        self,
        impasse_type: str,
        attribute: str,
        *,
        items: list[str] | None = None,
        non_numeric_items: list[str] | None = None,
    ) -> bool:
        """
        Creates a substate for impasse resolution.

        impasse_type:
            - "tie"
            - "no-change"
            - "conflict"
            - "constraint-failure"

        Follows a simplified Soar structure:
            (Sx ^type state
                ^impasse <type>
                ^choices <...>
                ^attribute <attribute>
                ^superstate Sy
                ^item ...              ; optional
                ^item-count N          ; optional
                ^non-numeric ...       ; optional for tie
                ^non-numeric-count M
                ^quiescence t
                ^reward-link Rk
                ^smem SMk
                ^epmem Ek
                ^svs SVk)
        """
        if len(self._substate_stack) >= MAX_SUBSTATE_DEPTH:
            return False

        depth = len(self._substate_stack) + 2  # Starts from S2
        super_id = "S1" if depth == 2 else f"S{depth-1}"

        # Default ^choices value by impasse type
        if impasse_type == "tie":
            choices = "multiple"
        elif impasse_type == "conflict":
            choices = "multiple"
        elif impasse_type == "constraint-failure":
            choices = "constraint-failure"
        else:
            # Default: includes no-change
            choices = "none"

        sub: dict[str, Any] = {
            "type": "state",
            "superstate": super_id,
            "impasse": impasse_type,
            "choices": choices,
            "attribute": attribute,
            "quiescence": True,
            # Module links: keep only smem/epmem, omit reward-link and svs.
            "smem": {"id": f"SM{depth}"},
            "epmem": {"id": f"E{depth}"},
        }

        if items:
            sub["item"] = list(items)
            sub["item-count"] = len(items)

        if non_numeric_items:
            sub["non-numeric"] = list(non_numeric_items)
            sub["non-numeric-count"] = len(non_numeric_items)

        self._substate_stack.append(sub)
        return True

    def pop_substate(self, result: Any = None) -> None:
        if not self._substate_stack:
            return
        self._substate_stack.pop()
