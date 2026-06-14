"""Throwaway (iter56): size the 'recolor-by-context' cluster.

A task is in the cluster if, for EVERY train pair, input and output have the same
shape and differ ONLY in cell colours (no cell becomes/stops-being background in a
way that moves an object) -- i.e. it is a pure in-place recolour. Among those,
how many does the current synthesizer already solve, and how many are MISSED?
A large missed cluster justifies a relational-recolor generalization; a tiny one
means no-op.
"""
import os, sys, random
sys.path.insert(0, os.path.abspath("."))
from managers.arc_manager import ARCManager
from program.synthesis import synthesize_task, run_program

manager = ARCManager(data_root="data", semantic_memory_root="semantic_memory")
split_dir = os.path.join("data", "ARC_AGI", "training")
hexes = sorted(f[:-5] for f in os.listdir(split_dir) if f.endswith(".json"))
random.seed(42); random.shuffle(hexes)
N = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
hexes = hexes[:N]


def same_shape(a, b):
    return len(a) == len(b) and all(len(ra) == len(rb) for ra, rb in zip(a, b))


def pure_recolor(gin, gout):
    """Same shape; the set of NON-background positions is identical (objects don't
    move), only colours change. Background = most-frequent colour of gin."""
    if not same_shape(gin, gout):
        return False
    from collections import Counter
    cnt = Counter(v for row in gin for v in row)
    bg = cnt.most_common(1)[0][0]
    for r in range(len(gin)):
        for c in range(len(gin[0])):
            inb = gin[r][c] == bg
            outb = gout[r][c] == bg
            if inb != outb:
                return False
    # require at least one colour actually change
    return any(gin[r][c] != gout[r][c]
               for r in range(len(gin)) for c in range(len(gin[0])))


cluster = []
solved = 0
missed = []
for h in hexes:
    try:
        task = manager.load_task(h)
        train = [(p.input_grid.raw, p.output_grid.raw) for p in task.example_pairs
                 if p.input_grid is not None and p.output_grid is not None]
        if len(train) < 2:
            continue
        if not all(pure_recolor(gi, go) for gi, go in train):
            continue
        cluster.append(h)
    except Exception:
        continue

print(f"pure in-place recolour cluster: {len(cluster)} / {len(hexes)} tasks", flush=True)
print("cluster:", " ".join(cluster), flush=True)
# How many does the synthesizer already reproduce on train? (single-step only, fast)
from program.synthesis import _candidate_programs, _reproduces
for i, h in enumerate(cluster):
    sys.stderr.write(f"[{i}/{len(cluster)}] solved={solved}\n"); sys.stderr.flush()
    task = manager.load_task(h)
    train = [{"input": p.input_grid.raw, "output": p.output_grid.raw}
             for p in task.example_pairs
             if p.input_grid is not None and p.output_grid is not None]
    prog = None
    try:
        for cand in _candidate_programs(train):
            if cand and _reproduces(cand, train):
                prog = cand; break
    except Exception:
        prog = None
    if prog:
        solved += 1
    else:
        missed.append(h)
    print(f"  {h}: {'SOLVED ' + str(prog[0][0]) if prog else 'missed'}", flush=True)
print(f"  synthesizer (single-step) reproduces train: {solved}", flush=True)
print(f"  MISSED (candidates for a relational recolour): {len(missed)}", flush=True)
for h in missed:
    print("   ", h, flush=True)
