"""
agent — SOAR cognitive architecture package.

Public interface:
    ActiveSoarAgent   — Main agent (sole solver, solve entry point)
    WorkingMemory     — S1/S2 state, goal/operator/knowledge/result areas
    run_cycle         — elaborate → propose → select → apply decision cycle
    Elaborator        — Fixed-point derived fact computation
    build_elaborator  — Create Elaborator with standard ElaborationRule set
    build_proposer    — Create Proposer with standard ProductionRule set (no task parameter needed)
    print_wm_triplets — Print entire WM state in SOAR triplet format to stdout
"""

from agent.active_agent import ActiveSoarAgent
from agent.wm import WorkingMemory
from agent.cycle import run_cycle
from agent.elaboration_rules import Elaborator, build_elaborator
from agent.rules import Proposer, build_proposer
from agent.wm_logger import print_wm_triplets

__all__ = [
    "ActiveSoarAgent",
    "WorkingMemory",
    "run_cycle",
    "Elaborator",
    "build_elaborator",
    "Proposer",
    "build_proposer",
    "print_wm_triplets",
]
