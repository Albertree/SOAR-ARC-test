"""READ-ONLY probe (iter66): does the 2-step compose lever generalize to EXPANSION
stage-1s? The existing _synthesize_composed only chains REDUCTIONS (crop/dihedral/
dedup) as stage-1. So an "expand then transform" task (scale-by-2 then recolour,
fractal then connect, ...) is uncaught even though both stages are existing
schemas. This probes scale/fractal expansions as compose stage-1, then a single-step
stage-2 re-fit, over ALL currently-failing training tasks. Strict full reproduction
on every train pair + held-out test. Counts >=2-fold. Writes nothing.
"""
import json, os, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from program import synthesis as S

TRAIN = os.path.join("data", "ARC_AGI", "training")

# expansion stage-1 candidates (value-agnostic const-leaf programs)
EXPAND = []
for kh, kw in [(2, 2), (3, 3), (2, 1), (1, 2), (3, 1), (1, 3), (2, 3), (3, 2)]:
    EXPAND.append([("scale", ("const", kh), ("const", kw))])
for mode in ("nonbg", "isbg", "most", "least", "all"):
    EXPAND.append([("fractal", ("const", mode))])

def main():
    files = sorted(os.listdir(TRAIN))
    folds = []
    heldout = []
    by_pre = Counter()
    n_fail = 0
    for fn in files:
        with open(os.path.join(TRAIN, fn)) as f:
            task = json.load(f)
        pairs = [{"input": p["input"], "output": p["output"]} for p in task["train"]]
        try:
            if S.synthesize_task(pairs) is not None:
                continue
        except Exception:
            pass
        # restrict to LARGER-output tasks (expansion stage-1 can only help here)
        def area(g): return len(g) * (len(g[0]) if g else 0)
        if not all(area(p["output"]) > area(p["input"]) for p in pairs):
            continue
        # cap input size so fractal's ih^2 x iw^2 canvas stays cheap
        if any(len(p["input"]) * (len(p["input"][0]) if p["input"] else 0) > 100 for p in pairs):
            continue
        n_fail += 1
        found = None
        for pre in EXPAND:
            try:
                inter = [S.run_program(pre, p["input"]) for p in pairs]
            except S._Unevaluable:
                continue
            # skip if expansion already equals output (that's a pure single-step solve)
            if all(inter[i] == pairs[i]["output"] for i in range(len(pairs))):
                composed = [("compose", pre)]
                # actually pure expansion == output means single-step should've caught it; skip
                continue
            pairs2 = [{"input": inter[i], "output": pairs[i]["output"]}
                      for i in range(len(pairs))]
            for post in S._candidate_programs(pairs2):
                if not post:
                    continue
                composed = [("compose", pre)] + list(post)
                try:
                    if S._reproduces(composed, pairs):
                        found = (composed, pre)
                        break
                except Exception:
                    pass
            if found:
                break
        if found:
            composed, pre = found
            folds.append(fn[:-5])
            by_pre[str(pre)] += 1
            ho = True
            for t in task.get("test", []):
                if "output" not in t:
                    ho = False; break
                try:
                    if S.run_program(composed, t["input"]) != t["output"]:
                        ho = False; break
                except Exception:
                    ho = False; break
            if ho:
                heldout.append(fn[:-5])

    print(f"failing tasks scanned: {n_fail}")
    print(f"expand-compose train-folds: {len(folds)}  {folds[:20]}")
    print(f"expand-compose held-out folds: {len(heldout)}  {heldout[:20]}")
    print(f"by stage-1: {by_pre.most_common()}")

if __name__ == "__main__":
    main()
