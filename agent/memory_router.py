"""
memory_router — Symbolic store routing table.

Maps (current_level, current_phase) to which memory stores are relevant.
Prevents irrelevant stores from being loaded. Provides logging for
visibility into which stores each operator accesses.
"""

STORE_ROUTING = {
    # At GRID level
    ("GRID", "elaborate"): ["semantic_memory"],
    ("GRID", "propose"):   ["procedural_memory"],
    ("GRID", "select"):    ["episodic_memory"],
    ("GRID", "apply"):     ["procedural_memory"],

    # At OBJECT level
    ("OBJECT", "elaborate"): ["semantic_memory", "episodic_memory"],
    ("OBJECT", "propose"):   ["procedural_memory"],
    ("OBJECT", "select"):    ["episodic_memory"],
    ("OBJECT", "apply"):     ["procedural_memory", "working_memory"],

    # At PIXEL level
    ("PIXEL", "elaborate"): ["semantic_memory"],
    ("PIXEL", "propose"):   ["procedural_memory"],
    ("PIXEL", "select"):    ["episodic_memory"],
    ("PIXEL", "apply"):     ["procedural_memory"],

    # On impasse (any level) -- only episodic, nothing else
    ("IMPASSE", "any"):     ["episodic_memory"],

    # During generalization -- all procedural to check for duplicates
    ("GENERALIZE", "any"):  ["procedural_memory"],
}

# Operator name -> phase mapping
OPERATOR_PHASE = {
    "select_target":    "elaborate",
    "compare":          "elaborate",
    "extract_pattern":  "propose",
    "generalize":       "generalize",
    "predict":          "apply",
    "submit":           "apply",
}


def get_stores(level: str, phase: str) -> list:
    """Return list of memory store names relevant for (level, phase)."""
    key = (level.upper(), phase)
    if key in STORE_ROUTING:
        return STORE_ROUTING[key]
    # Try with "any" phase (for IMPASSE and GENERALIZE)
    any_key = (level.upper(), "any")
    if any_key in STORE_ROUTING:
        return STORE_ROUTING[any_key]
    # Safe fallback: all stores
    return ["semantic_memory", "procedural_memory", "episodic_memory"]


def get_phase_for_operator(operator_name: str) -> str:
    """Map operator name to its SOAR phase."""
    return OPERATOR_PHASE.get(operator_name, "apply")


def log_routing(operator_name: str, level: str = "GRID"):
    """Log which stores an operator accesses. Returns stores list."""
    phase = get_phase_for_operator(operator_name)
    stores = get_stores(level, phase)
    print(f"[ROUTER] {operator_name} @ ({level}, {phase}) -> {stores}")
    return stores
