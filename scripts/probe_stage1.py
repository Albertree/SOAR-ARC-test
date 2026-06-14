"""Read-only probe: would WIDENING the compose stage-1 reductions fold >=2
currently-failing training tasks? (iter-59 next-gap lever.)

Tests candidate structural reductions as new stage-1 prefixes:
  - downscale: collapse uniform k_h x k_w blocks to one cell each
  - tilebase : crop to the fundamental translational period tile

For each candidate, count training tasks that synthesize_task currently FAILS
but newly solve under [("compose", pre)] + post (full-output reproduction).
Nothing is written; this only measures.
"""
import json, os, sys
sys.path.insert(0, os.getcwd())

from program.synthesis import (
    synthesize_task, _candidate_programs, _reproduces, run_program,
    _period_axes, background_of, _Unevaluable,
)

TRAIN = "data/ARC_AGI/training"


def _downscale(grid):
    """Largest uniform-block reduction of grid, or None if no proper block
    structure (k_h*k_w > 1 with every block a single colour and dims divisible)."""
    H = len(grid); W = len(grid[0]) if grid else 0
    if H == 0 or W == 0:
        return None
    def divisors(n):
        return [d for d in range(1, n + 1) if n % d == 0]
    best = None
    for kh in sorted(divisors(H), reverse=True):
        for kw in sorted(divisors(W), reverse=True):
            if kh == 1 and kw == 1:
                continue
            oh, ow = H // kh, W // kw
            ok = True
            out = []
            for br in range(oh):
                row = []
                for bc in range(ow):
                    v = grid[br * kh][bc * kw]
                    for r in range(br * kh, br * kh + kh):
                        for c in range(bc * kw, bc * kw + kw):
                            if grid[r][c] != v:
                                ok = False; break
                        if not ok: break
                    if not ok: break
                    row.append(v)
                if not ok: break
                out.append(row)
            if ok:
                return out  # largest factor first
    return best


def _tilebase(grid):
    """Crop to the fundamental period tile (top-left pv x ph), if grid is fully
    periodic on at least one axis and the tile is strictly smaller."""
    bg = background_of(grid)
    pv, ph = _period_axes(grid, bg)
    H = len(grid); W = len(grid[0]) if grid else 0
    th = pv if pv else H
    tw = ph if ph else W
    if th == H and tw == W:
        return None
    return [row[:tw] for row in grid[:th]]


CANDS = {"downscale": _downscale, "tilebase": _tilebase}


def composed_solves(pairs, fn):
    try:
        inter = [fn(p["input"]) for p in pairs]
    except _Unevaluable:
        return False
    if any(g is None for g in inter):
        return False
    pairs2 = [{"input": inter[i], "output": pairs[i]["output"]}
              for i in range(len(pairs))]
    for post in _candidate_programs(pairs2):
        if not post:
            continue
        # emulate compose by running post on the reduced grid
        ok = True
        for i, p in enumerate(pairs):
            try:
                got = run_program(post, inter[i])
            except _Unevaluable:
                ok = False; break
            if got != p["output"]:
                ok = False; break
        if ok:
            return True
    return False


def main():
    files = sorted(os.listdir(TRAIN))
    hits = {k: [] for k in CANDS}
    n = 0
    for fn_name in files:
        path = os.path.join(TRAIN, fn_name)
        with open(path) as f:
            task = json.load(f)
        pairs = task["train"]
        n += 1
        try:
            if synthesize_task(pairs) is not None:
                continue  # already solved
        except Exception:
            continue
        for cname, cfn in CANDS.items():
            try:
                if composed_solves(pairs, cfn):
                    hits[cname].append(fn_name[:-5])
            except Exception:
                pass
    print(f"scanned {n} training tasks")
    for cname in CANDS:
        print(f"  {cname}: {len(hits[cname])} newly-solved -> {hits[cname][:15]}")


if __name__ == "__main__":
    main()
