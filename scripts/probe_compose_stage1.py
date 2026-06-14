"""READ-ONLY probe (iter 61): would a NEW compose stage-1 reduction fold >=2
currently-failing training tasks?

For each of the 1000 ARC-AGI training tasks:
  1. baseline = synthesize_task(train_pairs)  (current code, incl. existing compose)
  2. if baseline is None (currently FAILING): for each candidate stage-1 reduction,
     transform every train input, re-fit the single-step search on the reduced
     pairs, and require FULL-output reproduction of the composed program.

A candidate "folds" a task only if the composed program reproduces EVERY train
pair AND the baseline does not already solve it. Reports per-candidate the set of
newly-folded task ids (the only non-trap, covers-raising signal, PROMPT.md §2.5).

No files are written. Pure diagnosis.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from program import synthesis as S
from agent.dsl_expr.selection import objects_of, background_of

TRAIN_DIR = os.path.join("data", "ARC_AGI", "training")


# ---- candidate stage-1 reductions (value-agnostic, structural) -------------

def _dedup_grid(grid):
    """Collapse runs of identical *adjacent* rows and columns to one each
    (the ARC 'compress duplicated lines' reduction). Returns None if nothing
    collapses (it would be identity)."""
    if not grid or not grid[0]:
        return None
    rows = [grid[0]]
    for r in grid[1:]:
        if r != rows[-1]:
            rows.append(r)
    # dedup columns
    W = len(rows[0])
    keep = [0]
    for c in range(1, W):
        if any(rows[r][c] != rows[r][keep[-1]] for r in range(len(rows))):
            keep.append(c)
    out = [[row[c] for c in keep] for row in rows]
    if out == grid:
        return None
    return out


def _block_reduce_grid(grid):
    """If the grid partitions into uniform k x k blocks (greatest such k>1),
    reduce to one cell per block. Returns None if no k>1 works."""
    if not grid or not grid[0]:
        return None
    H, W = len(grid), len(grid[0])

    def divisors(n):
        return [d for d in range(n, 1, -1) if n % d == 0]

    for kh in divisors(H):
        for kw in divisors(W):
            ok = True
            for bi in range(H // kh):
                for bj in range(W // kw):
                    v = grid[bi * kh][bj * kw]
                    for r in range(bi * kh, (bi + 1) * kh):
                        for c in range(bj * kw, (bj + 1) * kw):
                            if grid[r][c] != v:
                                ok = False
                                break
                        if not ok:
                            break
                    if not ok:
                        break
                if not ok:
                    break
            if ok:
                return [[grid[bi * kh][bj * kw] for bj in range(W // kw)]
                        for bi in range(H // kh)]
    return None


def _trim_border_grid(grid):
    """Strip a uniform 1-cell border frame if present (peel a solid frame).
    Returns None if no peel."""
    if not grid or len(grid) < 3 or len(grid[0]) < 3:
        return None
    top = grid[0]
    bot = grid[-1]
    left = [r[0] for r in grid]
    right = [r[-1] for r in grid]
    border = set(top) | set(bot) | set(left) | set(right)
    if len(border) != 1:
        return None
    return [row[1:-1] for row in grid[1:-1]]


CANDIDATES = {
    "dedup": _dedup_grid,
    "block_reduce": _block_reduce_grid,
    "trim_border": _trim_border_grid,
}


def reduce_pairs(fn, pairs):
    inter = []
    for p in pairs:
        g = fn(p["input"])
        if g is None:
            return None
        inter.append(g)
    return [{"input": inter[i], "output": pairs[i]["output"]}
            for i in range(len(pairs))]


def candidate_refit(redfn, pairs):
    """If redfn applies to every input and a single-step stage-2 reproduces the
    composed task, return the stage-2 program; else None."""
    rp = reduce_pairs(redfn, pairs)
    if rp is None:
        return None
    for post in S._candidate_programs(rp):
        if not post:
            continue
        ok = True
        for p in pairs:
            red = redfn(p["input"])
            if red is None:
                ok = False
                break
            try:
                out = S.run_program(post, red)
            except S._Unevaluable:
                ok = False
                break
            if out != p["output"]:
                ok = False
                break
        if ok:
            return post
    return None


def main():
    files = sorted(os.listdir(TRAIN_DIR))
    folds = {k: [] for k in CANDIDATES}
    applied = {k: 0 for k in CANDIDATES}
    n_hit = 0  # tasks where >=1 candidate composed-reproduces
    for idx, fn in enumerate(files):
        tid = fn[:-5]
        with open(os.path.join(TRAIN_DIR, fn)) as f:
            task = json.load(f)
        pairs = [{"input": p["input"], "output": p["output"]}
                 for p in task["train"]]
        hits = {}
        for name, redfn in CANDIDATES.items():
            if reduce_pairs(redfn, pairs) is not None:
                applied[name] += 1
                got = candidate_refit(redfn, pairs)
                if got is not None:
                    hits[name] = got
        if hits:
            # only now pay for the baseline: is the current code already solving it?
            baseline = S.synthesize_task(pairs)
            if baseline is None:
                n_hit += 1
                for name, got in hits.items():
                    folds[name].append((tid, got[0][0] if got else "?"))
        if (idx + 1) % 100 == 0:
            print(f"[{idx+1}/{len(files)}] newly-folded-tasks={n_hit} "
                  + " ".join(f"{k}:apply={applied[k]},fold={len(folds[k])}"
                             for k in CANDIDATES),
                  flush=True)

    print("\n===== RESULT =====", flush=True)
    print(f"newly-folded distinct tasks={n_hit}", flush=True)
    for name, lst in folds.items():
        print(f"\n--- {name}: applied={applied[name]} newly-folded={len(lst)} ---",
              flush=True)
        for tid, stage2 in lst:
            print(f"  {tid}  stage2={stage2}", flush=True)


if __name__ == "__main__":
    main()
