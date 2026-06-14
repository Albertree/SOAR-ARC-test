"""Read-only probe v2: more compose stage-1 reduction candidates.
strip_border, dedup (collapse consecutive duplicate rows/cols), and a combined
downscale+tilebase baseline. Counts currently-failing training tasks newly
solved via [("compose", pre)] + post (full-output reproduction). Writes nothing.
"""
import json, os, sys
sys.path.insert(0, os.getcwd())

from program.synthesis import (
    synthesize_task, _candidate_programs, run_program,
    _period_axes, background_of, _Unevaluable,
)

TRAIN = "data/ARC_AGI/training"


def _strip_border(grid):
    """Strip uniform single-colour outer rings repeatedly; None if nothing stripped
    or it collapses to empty."""
    g = [row[:] for row in grid]
    changed = False
    while len(g) > 1 and len(g[0]) > 1:
        top = g[0]; bot = g[-1]
        left = [r[0] for r in g]; right = [r[-1] for r in g]
        ring = set(top) | set(bot) | set(left) | set(right)
        if len(ring) == 1:
            g = [row[1:-1] for row in g[1:-1]]
            changed = True
        else:
            break
    if not changed or not g or not g[0]:
        return None
    return g


def _dedup(grid):
    """Collapse runs of consecutive identical rows, then identical columns
    (de-stretch). None if nothing collapses."""
    rows = []
    for r in grid:
        if not rows or rows[-1] != r:
            rows.append(r[:])
    # transpose, dedup, transpose back
    if not rows:
        return None
    cols = list(map(list, zip(*rows)))
    dcols = []
    for c in cols:
        if not dcols or dcols[-1] != c:
            dcols.append(c)
    out = list(map(list, zip(*dcols)))
    out = [list(r) for r in out]
    if out == [list(r) for r in grid]:
        return None
    return out


CANDS = {"strip_border": _strip_border, "dedup": _dedup}


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
        with open(os.path.join(TRAIN, fn_name)) as f:
            task = json.load(f)
        pairs = task["train"]
        n += 1
        try:
            if synthesize_task(pairs) is not None:
                continue
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
        print(f"  {cname}: {len(hits[cname])} -> {hits[cname][:20]}")


if __name__ == "__main__":
    main()
