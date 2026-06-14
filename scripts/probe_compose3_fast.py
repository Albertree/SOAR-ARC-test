"""READ-ONLY probe (iter66): faster 3-STEP compose check. iter65's probe_compose3
timed out (EXIT=124). The 3-step search is O(R*R*candidates) per task which is too
slow over all ~888 failing tasks. This restricts to SHRINKING-output failing tasks
(where stacked structural reductions plausibly help) and tries:
  (a) reduction -> reduction -> identity   (output == m2, the cheap pure-2-reduction case)
  (b) reduction -> reduction -> single stage-2 schema (full re-fit)
Strict full reproduction on every train pair + held-out test. Writes nothing.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from program import synthesis as S

TRAIN = os.path.join("data", "ARC_AGI", "training")

def dims(g): return (len(g), len(g[0]) if g else 0)

def shrinks(pairs):
    for p in pairs:
        hi, wi = dims(p["input"]); ho, wo = dims(p["output"])
        if not (ho * wo < hi * wi): return False
    return True

def main():
    files = sorted(os.listdir(TRAIN))
    R = S._STAGE1_REDUCTIONS
    fold_a, fold_b = [], []
    ho_a, ho_b = [], []
    n = 0
    for fn in files:
        with open(os.path.join(TRAIN, fn)) as f:
            task = json.load(f)
        pairs = [{"input": p["input"], "output": p["output"]} for p in task["train"]]
        try:
            if S.synthesize_task(pairs) is not None:
                continue
        except Exception:
            pass
        if not shrinks(pairs):
            continue
        n += 1
        found = None; kind = None
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
                if m2 == m1:
                    continue
                # (a) pure 2-reduction
                if all(m2[i] == pairs[i]["output"] for i in range(len(pairs))):
                    found = [("compose", pre1), ("compose", pre2)]; kind = "a"; break
                # (b) single stage-2 re-fit
                pairs2 = [{"input": m2[i], "output": pairs[i]["output"]} for i in range(len(pairs))]
                for post in S._candidate_programs(pairs2):
                    if not post:
                        continue
                    composed = [("compose", pre1), ("compose", pre2)] + list(post)
                    try:
                        if S._reproduces(composed, pairs):
                            found = composed; kind = "b"; break
                    except Exception:
                        pass
                if found: break
            if found: break
        if found:
            (fold_a if kind == "a" else fold_b).append(fn[:-5])
            ho = True
            for t in task.get("test", []):
                if "output" not in t: ho = False; break
                try:
                    if S.run_program(found, t["input"]) != t["output"]:
                        ho = False; break
                except Exception:
                    ho = False; break
            if ho:
                (ho_a if kind == "a" else ho_b).append(fn[:-5])

    print(f"shrinking failing tasks scanned: {n}")
    print(f"(a) reduction->reduction        train={len(fold_a)} heldout={len(ho_a)}  {fold_a[:12]}")
    print(f"(b) reduction->reduction->step2 train={len(fold_b)} heldout={len(ho_b)}  {fold_b[:12]}")

if __name__ == "__main__":
    main()
