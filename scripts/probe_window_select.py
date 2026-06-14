"""READ-ONLY probe (iter64): among currently-failing tasks whose output is a
contiguous window of the input, does a NEW value-agnostic window selector fold
>=2 with held-out test transfer? Distinct from crop's 5 selectors and from
panel-SELECT (which required uniform separator lines). Writes nothing.

Candidate selectors target the "grid tiles into equal blocks, pick one" family
WITHOUT separators (so panel-select missed them):
  - odd_block   : grid splits into equal r x c blocks; output = the one block
                  that differs from all the others (which are mutually equal).
  - common_block: same split; output = the block all-but-one agree on (majority).
  - tile_unit   : grid is an exact k-fold tiling of a unit block; output = unit.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from program import synthesis as S

TRAIN = os.path.join("data", "ARC_AGI", "training")


def _divisors(n):
    return [d for d in range(2, n + 1) if n % d == 0]


def _blocks(grid, nr, nc):
    """Split grid into nr x nc equal blocks; None if not divisible."""
    H, W = len(grid), len(grid[0])
    if H % nr or W % nc:
        return None
    bh, bw = H // nr, W // nc
    out = []
    for bi in range(nr):
        for bj in range(nc):
            blk = [row[bj * bw:(bj + 1) * bw]
                   for row in grid[bi * bh:(bi + 1) * bh]]
            out.append(blk)
    return out


def _all_splits(grid):
    """Yield every (nr, nc) equal-block split with >=2 blocks total."""
    H, W = len(grid), len(grid[0])
    for nr in [1] + _divisors(H):
        for nc in [1] + _divisors(W):
            if nr * nc >= 2:
                yield nr, nc


def odd_block(grid):
    for nr, nc in _all_splits(grid):
        blks = _blocks(grid, nr, nc)
        if blks is None:
            continue
        # exactly one differs from the rest (rest mutually equal)
        for i in range(len(blks)):
            rest = blks[:i] + blks[i + 1:]
            if rest and all(b == rest[0] for b in rest) and blks[i] != rest[0]:
                return blks[i]
    return None


def common_block(grid):
    for nr, nc in _all_splits(grid):
        blks = _blocks(grid, nr, nc)
        if blks is None:
            continue
        # the majority block (all but one equal); return that majority value
        for i in range(len(blks)):
            rest = blks[:i] + blks[i + 1:]
            if rest and all(b == rest[0] for b in rest) and blks[i] != rest[0]:
                return rest[0]
    return None


def tile_unit(grid):
    """If grid is an exact k-fold tiling (kr x kc, k>=2 total) of one unit block
    (every block identical), return the unit."""
    for nr, nc in _all_splits(grid):
        blks = _blocks(grid, nr, nc)
        if blks is None:
            continue
        if all(b == blks[0] for b in blks):
            return blks[0]
    return None


SELECTORS = {"odd_block": odd_block, "common_block": common_block,
             "tile_unit": tile_unit}


def reduce_inputs(fn, pairs):
    out = []
    for p in pairs:
        g = fn(p["input"])
        if g is None:
            return None
        out.append(g)
    return out


def fold(fn, pairs):
    inter = reduce_inputs(fn, pairs)
    if inter is None:
        return None
    if all(inter[i] == pairs[i]["output"] for i in range(len(pairs))):
        return ([], True)
    pairs2 = [{"input": inter[i], "output": pairs[i]["output"]}
              for i in range(len(pairs))]
    for post in S._candidate_programs(pairs2):
        if not post:
            continue
        ok = True
        for i, p in enumerate(pairs):
            try:
                if S.run_program(post, inter[i]) != p["output"]:
                    ok = False; break
            except S._Unevaluable:
                ok = False; break
        if ok:
            return (post, False)
    return None


def transfers(fn, post, task):
    for t in task.get("test", []):
        if "output" not in t:
            return False
        red = fn(t["input"])
        if red is None:
            return False
        if not post:
            if red != t["output"]:
                return False
        else:
            try:
                if S.run_program(post, red) != t["output"]:
                    return False
            except S._Unevaluable:
                return False
    return True


def main():
    files = sorted(os.listdir(TRAIN))
    folds = {k: [] for k in SELECTORS}
    held = {k: [] for k in SELECTORS}
    for idx, fn_name in enumerate(files):
        with open(os.path.join(TRAIN, fn_name)) as f:
            task = json.load(f)
        pairs = [{"input": p["input"], "output": p["output"]} for p in task["train"]]
        hits = {}
        for name, sfn in SELECTORS.items():
            res = fold(sfn, pairs)
            if res is not None:
                hits[name] = res
        if hits:
            if S.synthesize_task(pairs) is None:  # currently failing
                for name, (post, direct) in hits.items():
                    tag = "direct" if direct else (post[0][0] if post else "?")
                    folds[name].append(fn_name[:-5])
                    if transfers(SELECTORS[name], post, task):
                        held[name].append(fn_name[:-5])
        if (idx + 1) % 200 == 0:
            print(f"[{idx+1}/1000] "
                  + " ".join(f"{k}:f={len(folds[k])},h={len(held[k])}" for k in SELECTORS),
                  flush=True)
    print("\n===== RESULT =====", flush=True)
    for name in SELECTORS:
        print(f"--- {name}: train-fold={len(folds[name])} held-out={len(held[name])} ---")
        print("   train:", folds[name])
        print("   held :", held[name])


if __name__ == "__main__":
    main()
