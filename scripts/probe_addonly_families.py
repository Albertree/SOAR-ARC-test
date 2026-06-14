"""READ-ONLY probe (iter65): test fresh ADD-ONLY candidate mechanisms over ALL 223
same-dims add-only failing tasks. Strict FULL-grid reproduction on every train pair
AND held-out test pair. Counts >=2-fold transfer. iter64 next-gap final check before
honest termination. Writes nothing.

Candidates (value-agnostic, all expressible as coloring compositions):
  reflect_union : output = input | mirror(input) over {h,v,rot180} (add-only overlay)
  diag_ray      : from each non-bg cell, shoot 4 diagonal rays of its colour to edge
  ortho_ray     : from each non-bg cell, shoot 4 orthogonal rays of its colour to edge
  frame         : draw bbox outline (single colour = the unique non-bg colour) of all non-bg
  project_wall  : project each non-bg cell to all 4 walls as same-colour marker on border
"""
import json, os, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from program import synthesis as S

TRAIN = os.path.join("data", "ARC_AGI", "training")

def dims(g): return (len(g), len(g[0]) if g else 0)

def is_addonly(pairs):
    for p in pairs:
        gi, go = p["input"], p["output"]
        if dims(gi) != dims(go): return False
        changed = False
        for r in range(len(gi)):
            for c in range(len(gi[0])):
                a, b = gi[r][c], go[r][c]
                if a != b:
                    changed = True
                    if a != 0: return False
        if not changed: return False
    return True

def clone(g): return [row[:] for row in g]

def reflect_union(g, mode):
    H, W = len(g), len(g[0])
    out = clone(g)
    for r in range(H):
        for c in range(W):
            if g[r][c] == 0: continue
            if mode == "h": rr, cc = r, W-1-c
            elif mode == "v": rr, cc = H-1-r, c
            else: rr, cc = H-1-r, W-1-c
            if out[rr][cc] == 0:
                out[rr][cc] = g[r][c]
    return out

def diag_ray(g):
    H, W = len(g), len(g[0])
    out = clone(g)
    for r in range(H):
        for c in range(W):
            if g[r][c] == 0: continue
            col = g[r][c]
            for dr, dc in [(1,1),(1,-1),(-1,1),(-1,-1)]:
                rr, cc = r+dr, c+dc
                while 0 <= rr < H and 0 <= cc < W:
                    if out[rr][cc] == 0: out[rr][cc] = col
                    rr += dr; cc += dc
    return out

def ortho_ray(g):
    H, W = len(g), len(g[0])
    out = clone(g)
    for r in range(H):
        for c in range(W):
            if g[r][c] == 0: continue
            col = g[r][c]
            for dr, dc in [(1,0),(-1,0),(0,1),(0,-1)]:
                rr, cc = r+dr, c+dc
                while 0 <= rr < H and 0 <= cc < W:
                    if out[rr][cc] == 0: out[rr][cc] = col
                    rr += dr; cc += dc
    return out

def frame(g):
    H, W = len(g), len(g[0])
    cells = [(r,c) for r in range(H) for c in range(W) if g[r][c] != 0]
    if not cells: return None
    cols = set(g[r][c] for r,c in cells)
    if len(cols) != 1: return None
    col = cols.pop()
    r0 = min(r for r,_ in cells); r1 = max(r for r,_ in cells)
    c0 = min(c for _,c in cells); c1 = max(c for _,c in cells)
    out = clone(g)
    for c in range(c0, c1+1):
        if out[r0][c] == 0: out[r0][c] = col
        if out[r1][c] == 0: out[r1][c] = col
    for r in range(r0, r1+1):
        if out[r][c0] == 0: out[r][c0] = col
        if out[r][c1] == 0: out[r][c1] = col
    return out

CANDS = {
    "reflect_h":  lambda g: reflect_union(g, "h"),
    "reflect_v":  lambda g: reflect_union(g, "v"),
    "reflect_r180": lambda g: reflect_union(g, "rot180"),
    "diag_ray":   diag_ray,
    "ortho_ray":  ortho_ray,
    "frame":      frame,
}

def main():
    files = sorted(os.listdir(TRAIN))
    folds = Counter()
    heldout = Counter()
    hit_tasks = {k: [] for k in CANDS}
    n_addonly = 0
    for fn in files:
        with open(os.path.join(TRAIN, fn)) as f:
            task = json.load(f)
        pairs = task["train"]
        try:
            if S.synthesize_task([{"input": p["input"], "output": p["output"]} for p in pairs]) is not None:
                continue
        except Exception:
            pass
        if not is_addonly(pairs): continue
        n_addonly += 1
        for name, fn_c in CANDS.items():
            ok = True
            for p in pairs:
                try:
                    out = fn_c(p["input"])
                except Exception:
                    out = None
                if out != p["output"]:
                    ok = False; break
            if ok:
                folds[name] += 1
                hit_tasks[name].append(fn[:-5])
                # held-out test
                ho_ok = True
                for t in task.get("test", []):
                    if "output" not in t: ho_ok = False; break
                    try:
                        if fn_c(t["input"]) != t["output"]:
                            ho_ok = False; break
                    except Exception:
                        ho_ok = False; break
                if ho_ok:
                    heldout[name] += 1

    print(f"add-only failing tasks scanned: {n_addonly}\n")
    for name in CANDS:
        print(f"  {name:14s} train-fold={folds[name]:3d}  heldout-fold={heldout[name]:3d}  {hit_tasks[name][:8]}")

if __name__ == "__main__":
    main()
