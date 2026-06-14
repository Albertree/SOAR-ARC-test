"""Throwaway diagnostic (iter56): live-pipeline scan for family-shadow misfires.

iter55 found family matchers shadow the reproduction-gated synthesizer and are
sometimes WRONG. For a training sample, for each task:
  - which family (if any) claims it (constant_output / object_motion / object_recolor)
  - whether that family's LIVE prediction is correct on the held-out test
  - if a family claimed it and was WRONG: does the family even REPRODUCE the train
    pairs?  (a reproduce-gate would only step aside when it does NOT)
  - and would the synthesizer ALONE be correct on the test -> RESCUABLE set.

Routing uses the family matchers directly (no synthesizer) so it is fast; the
synthesizer is only invoked on family-WRONG tasks for the rescue check.
"""
import os, sys, random
sys.path.insert(0, os.path.abspath("."))

from managers.arc_manager import ARCManager
from agent.wm import WorkingMemory
from agent.wm_logger import reset_wm_snapshot
from agent.io import inject_arc_task
from agent.active_operators import (
    ExtractPatternOperator, GeneralizeOperator, PredictOperator,
)
from program.synthesis import synthesize_task, run_program

OUT = open(sys.argv[2] if len(sys.argv) > 2 else "scripts/_scan_out.txt", "w")
def emit(s):
    print(s); OUT.write(s + "\n"); OUT.flush()

manager = ARCManager(data_root="data", semantic_memory_root="semantic_memory")
split_dir = os.path.join("data", "ARC_AGI", "training")
hexes = sorted(f[:-5] for f in os.listdir(split_dir) if f.endswith(".json"))
random.seed(42); random.shuffle(hexes)
N = int(sys.argv[1]) if len(sys.argv) > 1 else 200
hexes = hexes[:N]

gen = GeneralizeOperator()
pred = PredictOperator()
FAMILIES = ("object_motion", "object_recolor", "constant_output")


def family_rule(patterns):
    """Replicate GeneralizeOperator's family precedence WITHOUT the synthesizer
    fallback. Returns the family rule dict or None."""
    if gen._matches_constant_output(patterns):
        return {"type": "constant_output",
                "condition": {"type": "constant_output", "params": {"min_evidence": 2}, "min_evidence": 2},
                "action": {"dsl": "copy_common_output", "args": {}}, "confidence": 1.0}
    if gen._matches_object_motion(patterns):
        return {"type": "object_motion",
                "condition": {"type": "object_motion", "params": {"min_evidence": 2}, "min_evidence": 2},
                "action": {"dsl": "place_object", "args": {}}, "confidence": 1.0}
    if gen._matches_object_recolor(patterns):
        return {"type": "object_recolor",
                "condition": {"type": "object_recolor", "params": {"min_evidence": 2}, "min_evidence": 2},
                "action": {"dsl": "recolor_object", "args": {}}, "confidence": 1.0}
    return None


def render(rule, patterns, input_raw):
    """Render a family rule's prediction for one input grid via PredictOperator,
    using a 1-test-pair shim task carrying the given patterns."""
    class _G:  # minimal grid shim
        def __init__(self, raw): self.raw = raw
    class _TP:
        def __init__(self, raw): self.input_grid = _G(raw); self.output_grid = None
    class _T:
        pass
    wm = WorkingMemory()
    reset_wm_snapshot(wm)
    t = _T(); t.test_pairs = [_TP(input_raw)]
    wm.task = t
    wm.s1["patterns"] = patterns
    wm.s1["active-rules"] = [rule]
    pred.effect(wm)
    return (wm.s1.get("predictions") or {}).get("test_0")


def fit_patterns(task):
    wm = WorkingMemory(); reset_wm_snapshot(wm); inject_arc_task(task, wm)
    ExtractPatternOperator().effect(wm)
    return wm.s1.get("patterns") or {}


def family_reproduces_train(rule, patterns, task):
    for p in task.example_pairs:
        if p.input_grid is None or p.output_grid is None:
            continue
        try:
            out = render(rule, patterns, p.input_grid.raw)
        except Exception:
            return False
        if out != p.output_grid.raw:
            return False
    return True


def family_test_correct(rule, patterns, task):
    ans = [p.output_grid.raw for p in task.test_pairs if p.output_grid is not None]
    if not ans:
        return None
    preds = []
    for tp in task.test_pairs:
        try:
            preds.append(render(rule, patterns, tp.input_grid.raw))
        except Exception:
            return False
    return preds == ans


def synth_test_correct(task):
    train = [(p.input_grid.raw, p.output_grid.raw) for p in task.example_pairs
             if p.input_grid is not None and p.output_grid is not None]
    try:
        prog = synthesize_task(train)
        if not prog:
            return None
        ans = [p.output_grid.raw for p in task.test_pairs if p.output_grid is not None]
        preds = [run_program(prog, tp.input_grid.raw) for tp in task.test_pairs]
        return preds == ans
    except Exception:
        return None


from collections import Counter
counter = Counter()
wrong = []   # (h, ftype, reproduces_train)
for i, h in enumerate(hexes):
    if i % 10 == 0:
        sys.stderr.write(f"[{i}/{len(hexes)}] {dict(counter)}\n"); sys.stderr.flush()
    try:
        task = manager.load_task(h)
        patterns = fit_patterns(task)
        rule = family_rule(patterns)
        if rule is None:
            counter["(no family)"] += 1
            continue
        ftype = rule["type"]
        ok = family_test_correct(rule, patterns, task)
        counter[f"{ftype}:{'correct' if ok else 'WRONG'}"] += 1
        if not ok:
            repro = family_reproduces_train(rule, patterns, task)
            wrong.append((h, ftype, repro))
            emit(f"WRONG {h} {ftype} reproduces_train={repro}")
    except Exception as e:
        counter[f"ERR:{type(e).__name__}"] += 1

emit("=== family routing over %d tasks ===" % len(hexes))
for k, c in counter.most_common():
    emit(f"  {k:28s} {c}")

emit(f"\n=== family fired but test WRONG: {len(wrong)} ===")
emit("  (repro=True means family reproduces train yet fails test = honest-but-overfit;")
emit("   repro=False means family fired WITHOUT reproducing train = the shadow bug)")
rescuable = []
not_repro = [w for w in wrong if w[2] is False]
emit(f"\n--- of those, did NOT reproduce train (reproduce-gate would free them): {len(not_repro)} ---")
for h, ftype, repro in not_repro:
    s = synth_test_correct(manager.load_task(h))
    tag = "RESCUABLE" if s else ("synth-miss" if s is False else "synth-None")
    emit(f"  {h}  {ftype:14s} {tag}")
    if s:
        rescuable.append(h)
emit(f"\n=== RESCUABLE (family-no-repro, synthesizer alone correct on test): {len(rescuable)} ===")
for h in rescuable:
    emit("  " + h)
OUT.close()
