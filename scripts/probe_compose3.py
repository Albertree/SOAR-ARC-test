"""READ-ONLY probe (iter65): test 3-STEP compose (stage1-reduce -> stage1-reduce ->
single-step) over all currently-FAILING training tasks. The 2-step compose lever
(iter46 +10, iter61 dedup +6) is the one historically-paying non-Q-B3 lever; this
asks whether a SECOND stacked reduction folds >=2 currently-failing tasks with
held-out transfer. Strict full reproduction. Writes nothing.
"""
import json, os, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from program import synthesis as S

TRAIN = os.path.join("data", "ARC_AGI", "training")

def main():
    files = sorted(os.listdir(TRAIN))
    R = S._STAGE1_REDUCTIONS
    folds = []
    heldout = []
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
        n_fail += 1
        found = None
        for pre1 in R:
            try:
                m1 = [S.run_program(pre1, p["input"]) for p in pairs]
            except S._Unevaluable:
                continue
            for pre2 in R:
                try:
                    m2 = [S.run_program(pre2, g) for g in m1]
                except S._Unevaluable:
                    continue
                if m2 == m1:  # second reduction did nothing
                    continue
                pairs2 = [{"input": m2[i], "output": pairs[i]["output"]} for i in range(len(pairs))]
                for post in S._candidate_programs(pairs2):
                    if not post:
                        continue
                    composed = [("compose", pre1), ("compose", pre2)] + list(post)
                    try:
                        if S._reproduces(composed, pairs):
                            found = composed
                            break
                    except Exception:
                        pass
                if found: break
            if found: break
        if found:
            folds.append(fn[:-5])
            # held-out
            ho = True
            for t in task.get("test", []):
                if "output" not in t: ho = False; break
                try:
                    if S.run_program(found, t["input"]) != t["output"]:
                        ho = False; break
                except Exception:
                    ho = False; break
            if ho:
                heldout.append(fn[:-5])

    print(f"failing tasks scanned: {n_fail}")
    print(f"3-step compose train-folds: {len(folds)}  {folds[:15]}")
    print(f"3-step compose held-out folds: {len(heldout)}  {heldout[:15]}")

if __name__ == "__main__":
    main()
