"""READ-ONLY probe (iter65): characterize the same-dims ADD-ONLY failing cluster
(output = input with extra non-bg painted on previously-bg cells). iter64 next-gap:
test whether this cluster hides any >=2-fold mechanism beyond iter59's 5 families.
Writes nothing. Buckets each add-only task by candidate add-only structure.
"""
import json, os, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from program import synthesis as S

TRAIN = os.path.join("data", "ARC_AGI", "training")

def dims(g): return (len(g), len(g[0]) if g else 0)

def added_cells(gi, go):
    cells = []
    for r in range(len(gi)):
        for c in range(len(gi[0])):
            if gi[r][c] == 0 and go[r][c] != 0:
                cells.append((r, c, go[r][c]))
    return cells

def main():
    files = sorted(os.listdir(TRAIN))
    addonly = []
    for fn in files:
        with open(os.path.join(TRAIN, fn)) as f:
            task = json.load(f)
        pairs = task["train"]
        try:
            if S.synthesize_task([{"input": p["input"], "output": p["output"]} for p in pairs]) is not None:
                continue
        except Exception:
            pass
        # add-only same-dims, all pairs
        ok = True
        for p in pairs:
            gi, go = p["input"], p["output"]
            if dims(gi) != dims(go):
                ok = False; break
            superset = True
            changed = False
            for r in range(len(gi)):
                for c in range(len(gi[0])):
                    a, b = gi[r][c], go[r][c]
                    if a != b:
                        changed = True
                        if a != 0:
                            superset = False
            if not superset or not changed:
                ok = False; break
        if ok:
            addonly.append(fn[:-5])

    print(f"add-only failing tasks: {len(addonly)}")

    # bucket by structure of added cells (use first train pair as representative)
    buckets = Counter()
    samples = {}
    for tid in addonly:
        with open(os.path.join(TRAIN, tid + ".json")) as f:
            task = json.load(f)
        p = task["train"][0]
        gi, go = p["input"], p["output"]
        ac = added_cells(gi, go)
        added_colors = set(col for _,_,col in ac)
        in_colors = set(v for row in gi for v in row if v != 0)
        # how many added cells
        n = len(ac)
        # are added cells single-colour?
        single = len(added_colors) == 1
        # is added colour present in input?
        new_color = bool(added_colors - in_colors)
        # are added cells horizontally/vertically aligned (rows/cols)?
        rows = set(r for r,_,_ in ac)
        cols = set(c for _,_,c2 in [(r,c,col) for r,c,col in ac])
        cols = set(c for _,c,_ in ac)
        full_rows = sum(1 for r in rows if all((r,c) in {(rr,cc) for rr,cc,_ in ac} for c in range(len(gi[0]))))
        tag = []
        tag.append("single" if single else "multi")
        tag.append("newcol" if new_color else "samecol")
        key = "/".join(tag)
        buckets[key] += 1
        samples.setdefault(key, []).append(tid)

    print("\nbuckets (single/multi colour added, new/existing colour):")
    for k, v in buckets.most_common():
        print(f"  {k}: {v}   e.g. {samples[k][:6]}")

if __name__ == "__main__":
    main()
