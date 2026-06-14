"""READ-ONLY probe (iter64): profile the currently-FAILING training tasks by gross
structure, to locate where unsolved mass concentrates and whether any untapped
*general* lever has >=2-task support. Writes nothing.
"""
import json, os, sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from program import synthesis as S

TRAIN = os.path.join("data", "ARC_AGI", "training")


def dims(g):
    return (len(g), len(g[0]) if g else 0)


def main():
    files = sorted(os.listdir(TRAIN))
    solved = 0
    cats = Counter()
    subgrid = []        # every output is a contiguous subgrid of its input
    same_dims_addonly = []   # same dims, output = input + extra non-bg (superset)
    same_dims_recolor = []   # same dims, same non-bg footprint, colours differ
    for fn in files:
        with open(os.path.join(TRAIN, fn)) as f:
            task = json.load(f)
        pairs = task["train"]
        try:
            if S.synthesize_task([{"input": p["input"], "output": p["output"]}
                                  for p in pairs]) is not None:
                solved += 1
                continue
        except Exception:
            pass
        tid = fn[:-5]
        # classify by dims relation (consistent across pairs?)
        rels = set()
        for p in pairs:
            di, do = dims(p["input"]), dims(p["output"])
            if di == do:
                rels.add("same")
            elif do[0] <= di[0] and do[1] <= di[1]:
                rels.add("smaller")
            elif do[0] >= di[0] and do[1] >= di[1]:
                rels.add("larger")
            else:
                rels.add("mixed")
        rel = rels.pop() if len(rels) == 1 else "varies"
        cats[rel] += 1

        # same-dims sub-classification
        if rel == "same":
            addonly = True
            recolor = True
            for p in pairs:
                gi, go = p["input"], p["output"]
                same_fp = True
                superset = True
                for r in range(len(gi)):
                    for c in range(len(gi[0])):
                        a, b = gi[r][c], go[r][c]
                        if a != b:
                            same_fp = False
                            # add-only: input cell was background(0) and got painted
                            if a != 0:
                                superset = False
                if not same_fp:
                    recolor = False
                if not superset:
                    addonly = False
            if addonly:
                same_dims_addonly.append(tid)
            elif recolor is False:
                pass
            # recolor = same footprint of non-bg, only colours change
            rec = True
            for p in pairs:
                gi, go = p["input"], p["output"]
                fi = {(r, c) for r in range(len(gi)) for c in range(len(gi[0])) if gi[r][c] != 0}
                fo = {(r, c) for r in range(len(go)) for c in range(len(go[0])) if go[r][c] != 0}
                if fi != fo:
                    rec = False
                    break
            if rec:
                same_dims_recolor.append(tid)

        # subgrid: output equals some contiguous window of input (all pairs)
        sub = True
        for p in pairs:
            gi, go = p["input"], p["output"]
            H, W = len(gi), len(gi[0])
            h, w = len(go), len(go[0])
            if h > H or w > W:
                sub = False
                break
            found = False
            for r in range(H - h + 1):
                for c in range(W - w + 1):
                    if all(gi[r + i][c:c + w] == go[i] for i in range(h)):
                        found = True
                        break
                if found:
                    break
            if not found:
                sub = False
                break
        if sub:
            subgrid.append(tid)

    print(f"solved={solved}  failing={sum(cats.values())}")
    print("dims relation among failing:", dict(cats))
    print(f"\nsame-dims add-only (bg->colour superset): {len(same_dims_addonly)}")
    print(f"same-dims pure-recolour (footprint fixed): {len(same_dims_recolor)}")
    print(f"output-is-a-subgrid-of-input (any window): {len(subgrid)}")
    print("  subgrid sample:", subgrid[:25])


if __name__ == "__main__":
    main()
