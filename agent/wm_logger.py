"""
wm_logger — Utility for printing WorkingMemory state in SOAR triplet format.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SOAR Working Memory Element (WME) format:
    (identifier ^attribute value)

    identifier : S1=root, S2/S3...=substates, I1/I2...=auto-generated child nodes
    attribute  : field name
    value      : primitive or child node identifier

diff colors (git diff style):
    Green background + white text  →  WME added/changed compared to previous call
    Red background + white text    →  WME removed compared to previous call
    Normal                         →  Unchanged WME

    Comparison is based on path_key (e.g., S1/relations/pair_0/type) rather than
    auto-id (I1, I2...), so the semantic diff is computed accurately even if
    identifiers change.

Usage:
    from agent.wm_logger import print_wm_triplets, reset_wm_snapshot
    reset_wm_snapshot()                                 # Reset snapshot before task starts
    print_wm_triplets(wm, label="After: elaborate", step=3)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from __future__ import annotations

import sys
import io
import itertools
from dataclasses import dataclass
from typing import Any

# Fix UnicodeEncodeError on Windows with non-UTF-8 locales (e.g., cp949)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')


# ── ANSI colors ────────────────────────────────────────────────────────── #

_GREEN_BG = "\033[42;37m"   # Green background, white text (added/changed)
_RED_BG   = "\033[41;37m"   # Red background, white text (removed)
_RESET    = "\033[0m"

# Output width: pad color background to match divider width.
_LINE_WIDTH = 62


# ── Output constants ────────────────────────────────────────────────────── #

_L1      = "  "       # depth 0 (root identifier S1/S2/WM) line indentation
_L2      = "    "     # depth 1 (direct children: I1, etc.) indentation
_L3      = "      "   # depth 2+ (grandchildren and below: I2, I3, etc.) indentation
_DIVIDER = "=" * _LINE_WIDTH

# S1/WM family identifier detection
_ROOT_IDS = {"S1", "S2", "S3", "S4", "WM"}

# Maximum display length for string values
_MAX_STR_LEN = 80


# ── WME data model ──────────────────────────────────────────────────── #

@dataclass(frozen=True)
class _WME:
    """
    A single Working Memory Element.

    identifier : display node ID (S1, I1, ...)
    attribute  : field name
    value      : formatted value string
    path_key   : canonical path for diff comparison (e.g., "S1/relations/pair_0/type")
    is_root    : True if identifier is S1/WM family → L1 indentation
    """
    identifier: str
    attribute:  str
    value:      str
    path_key:   str
    is_root:    bool
    depth:      int   # Depth relative to S1 (0=S1, 1=child, 2=grandchild...)


# ── Module-level diff state ──────────────────────────────────────────── #

# {path_key: _WME} — Snapshot from the previous print_wm_triplets call
_prev_snap: dict[str, _WME] = {}


def reset_wm_snapshot(wm=None) -> None:
    """
    Resets the diff snapshot.

    wm=None  : Reset to empty snapshot → next print_wm_triplets call shows everything in green
    wm=<WM>  : Pre-fill snapshot with current WM state
               → next print_wm_triplets call shows no changes, all in normal color

    Recommended usage pattern:
        # run_task.py — Start diff from initial WM state
        build_wm_from_task(task, wm)
        reset_wm_snapshot(wm)              # Set initial state as baseline
        print_wm_triplets(wm, "Initial WM state")  # Print current state without colors

        # active_agent.solve() — Prevent previous state from mixing between tasks
        reset_wm_snapshot()                # Reset to empty state before task starts
    """
    global _prev_snap
    if wm is not None:
        entries    = _wm_as_entries(wm)
        _prev_snap = {e.path_key: e for e in entries}
    else:
        _prev_snap = {}


# ── Value formatting ────────────────────────────────────────────────────── #

def _fmt(value: Any) -> str:
    """Converts a primitive value to a SOAR display string."""
    if value is None:
        return "nil"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        # Preference symbols etc. — single characters used bare in Soar
        if len(value) == 1 and value in "+-!~<>":
            return value
        # SOAR style: symbols without spaces/special chars are kept as-is; others are quoted.
        s = value if len(value) <= _MAX_STR_LEN else value[:_MAX_STR_LEN] + "…"
        if s and all(ch.isalnum() or ch in ("_", "-", ".") for ch in s):
            return s
        return f'"{s}"'
    return str(value)


def _is_grid(lst: list) -> bool:
    """Determines whether the list looks like a 2D grid (array of integers or array of integer arrays)."""
    return bool(lst) and isinstance(lst[0], (int, list, tuple))


# ── WME collection (recursive) ──────────────────────────────────────── #

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
    Recursively expands a single (identifier, attribute, value) and appends _WME entries to out.

    path_key generation rules:
        Normal dict field: "{path_prefix}/{attribute}"
        List item: "{path_prefix}/{attribute}[{list_index}]"
    """
    if list_index is not None:
        path_key = f"{path_prefix}/{attribute}[{list_index}]"
    else:
        path_key = f"{path_prefix}/{attribute}"

    is_root = identifier in _ROOT_IDS

    if isinstance(value, dict):
        if not value:
            # Empty dict also gets a separate identifier (Ix) with just the link.
            # e.g., (I1 ^output-link I3) where I3 has no attributes yet.
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
        # Normal list: recursively collect each item with index-based path_key
        for idx, item in enumerate(value):
            _collect(identifier, attribute, item, id_gen, out, path_prefix, depth, list_index=idx)

    else:
        out.append(_WME(identifier, attribute, _fmt(value), path_key, is_root, depth))


# ── WM → WME list conversion ───────────────────────────────────────── #

def _wm_as_entries(wm) -> list[_WME]:
    """Converts the entire WorkingMemory to a list of _WME entries."""
    id_gen = (f"I{n}" for n in itertools.count(1))
    out: list[_WME] = []

    # S1 (root state)
    root = "S1"
    for attr, val in wm.s1.items():
        # Operator nodes and similar separate identifier nodes are treated as
        # independent identifiers rather than S1 attributes (e.g., O1).
        if isinstance(val, dict) and attr[:1].isalpha() and attr[0].isupper():
            for child_attr, child_val in val.items():
                _collect(attr, child_attr, child_val, id_gen, out, attr, depth=0)
            continue
        _collect(root, attr, val, id_gen, out, root, depth=0)

    # task is an external reference outside WM (Python level), so only a summary is printed.
    # In SOAR style, environment input should go under io/input-link,
    # so this value is kept for debug purposes only.
    if getattr(wm, "task", None) is not None:
        summary = getattr(wm.task, "task_hex", repr(wm.task))
        out.append(_WME(root, "task_ref", f"<task {summary}>", f"{root}/task_ref", True, 0))

    # S2, S3, ... (substate stack) — Each substate is represented only as an independent Sx identifier.
    for depth, substate in enumerate(wm._substate_stack, start=2):
        sub = f"S{depth}"
        for attr, val in substate.items():
            # Same as S1: O* operator nodes are expanded as independent identifiers.
            if isinstance(val, dict) and attr[:1].isalpha() and attr[0].isupper():
                for child_attr, child_val in val.items():
                    _collect(attr, child_attr, child_val, id_gen, out, attr, depth=0)
                continue
            _collect(sub, attr, val, id_gen, out, sub, depth=0)

    return out


# ── Line formatting + colors ─────────────────────────────────────────── #

def _indent_for_depth(depth: int) -> str:
    """Returns the indentation string for the given depth value."""
    if depth <= 0:
        return _L1
    if depth == 1:
        return _L2
    return _L3


def _render(entry: _WME) -> str:
    """Converts a single _WME to a string in `  (S1 ^attr val)` format."""
    indent = _L1 if entry.is_root else _L2
    return f"{indent}({entry.identifier} ^{entry.attribute} {entry.value})"


def _op_preference_map_current(current_entries: list[_WME]) -> dict[str, str]:
    """Returns op-preference of O* nodes that exist only in the current WM (must not mix with removed WME list)."""
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
    Groups WMEs with the same identifier into a single block, similar to SOAR debug output style.

    op_preference_map: Computed from current WM only (prevents contamination even if display_entries contains removed items).
    """
    if not entries:
        return []

    op_preference = op_preference_map

    # Collect all WMEs by identifier (regardless of contiguity).
    by_id: dict[str, list[_WME]] = {}
    order: list[str] = []
    for e in entries:
        if e.identifier not in by_id:
            by_id[e.identifier] = []
            order.append(e.identifier)
        by_id[e.identifier].append(e)

    # In O* blocks, ^op-preference is merged into the S1 line, so omit it as a separate line
    for oid, group in list(by_id.items()):
        if oid.startswith("O") and len(oid) >= 2 and oid[1:].isdigit():
            by_id[oid] = [w for w in group if w.attribute != "op-preference"]

    # Output order: S1, operators (O*), S2/S3/S4, WM, then remaining identifiers.
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

    # S1: proposal ^operator O* + followed by official ^operator O* (operator-application)
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

    # S2, S3, ... (substate) — smem → epmem fixed order
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
    Displays a removed WME with path_key-based identifier.

    Uses entry.identifier / attribute / depth information to
    maintain the same indentation as normal output.
    """
    base_indent = _indent_for_depth(entry.depth)
    return f"{base_indent}({entry.identifier} ^{entry.attribute} {entry.value})"


def _colorize(text: str, ansi: str) -> str:
    """Pads text to _LINE_WIDTH and wraps it with ANSI background color."""
    padded = text.ljust(_LINE_WIDTH)
    return f"{ansi}{padded}{_RESET}"


# ── Public output function ───────────────────────────────────────────── #

def print_wm_triplets(wm, label: str = "", step: int = 0) -> None:
    """
    Prints the entire WorkingMemory state in SOAR triplet format + git diff style colors.

    Output rules:
        Green background  → WME newly added or value changed compared to previous snapshot
        Red background    → WME that existed in previous snapshot but is now absent (removed section)
        Normal text       → Unchanged WME

    On the first call, _prev_snap is empty so all items are shown in green.
    When the task changes, reset_wm_snapshot() must be called to reset the snapshot.
    """
    global _prev_snap

    entries   = _wm_as_entries(wm)
    curr_snap = {e.path_key: e for e in entries}

    # ── Diff computation ─────────────────────────────────────────── #
    added_keys = {
        k for k, e in curr_snap.items()
        if k not in _prev_snap or _prev_snap[k].value != e.value
    }
    removed = {
        k: e for k, e in _prev_snap.items()
        if k not in curr_snap
    }

    # ── Header ──────────────────────────────────────────────────── #
    header = f"[Step {step}] {label}" if label else f"[Step {step}]"
    print(_DIVIDER)
    print(f"{_L1}{header}")
    print(_DIVIDER)

    # ── Print current state + removed items together (grouped by identifier) ── #
    # Display entries: current entries + removed entries (current takes priority for duplicate path_keys)
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

    # ── Footer ──────────────────────────────────────────────────── #
    print(_DIVIDER)
    print()

    # ── Update snapshot ───────────────────────────────────────────── #
    _prev_snap = curr_snap
