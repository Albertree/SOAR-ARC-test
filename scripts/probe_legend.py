"""Read-only probe (iter63): among currently-FAILING training tasks, how many are
'legend/marker correspondence recolour' — a set of small unique-colour MARKER
objects plus larger mono-colour TARGET objects, where each target's OUTPUT colour
equals the colour of the marker it corresponds to under ONE value-agnostic spatial
predicate (column-overlap / row-overlap / nearest-centroid / containment)?

If a SINGLE predicate reproduces >=2 tasks' full train output AND their held-out
test, that's a >=2-fold object-correspondence slice (the iter62 next-gap target).
Writes nothing. Pure diagnosis.
"""
import json, os, sys
sys.path.insert(0, os.getcwd())
from program.synthesis import synthesize_task, background_of, objects_of

TRAIN = "data/ARC_AGI/training"


def objs(grid):
    bg = background_of(grid)
    out = []
    for o in objects_of(grid, bg, same_color=True):
        cells = list(o["cells"])
        if not cells:
            continue
        r, c = cells[0]
        col = grid[r][c]
        rs = [a for a, _ in cells]; cs = [b for _, b in cells]
        cen = (sum(rs) / len(rs), sum(cs) / len(cs))
        out.append({"cells": frozenset(cells), "col": col, "size": len(cells),
                    "rmin": min(rs), "rmax": max(rs), "cmin": min(cs),
                    "cmax": max(cs), "cen": cen})
    return out


PREDS = ("col_overlap", "row_overlap", "nearest", "contains")


def corresponds(target, marker, pred):
    if pred == "col_overlap":
        return not (target["cmax"] < marker["cmin"] or marker["cmax"] < target["cmin"])
    if pred == "row_overlap":
        return not (target["rmax"] < marker["rmin"] or marker["rmax"] < target["rmin"])
    if pred == "nearest":
        return True  # handled specially (min distance)
    if pred == "contains":
        return (target["rmin"] <= marker["cen"][0] <= target["rmax"]
                and target["cmin"] <= marker["cen"][1] <= target["cmax"])
    return False


def try_pred_on_pair(gi, go, pred):
    """Return True iff under `pred`, recolouring each input object by its matched
    marker reproduces go exactly. Markers = smallest-size colour class; targets =
    the rest. Value-agnostic."""
    if len(gi) != len(go) or len(gi[0]) != len(go[0]):
        return False
    ois = objs(gi)
    if len(ois) < 3:
        return False
    sizes = sorted(set(o["size"] for o in ois))
    msize = sizes[0]
    markers = [o for o in ois if o["size"] == msize]
    targets = [o for o in ois if o["size"] != msize]
    if not markers or not targets:
        return False
    # markers must be distinct colours (a legend)
    if len({m["col"] for m in markers}) != len(markers):
        return False
    pred_grid = [row[:] for row in gi]
    for t in targets:
        if pred == "nearest":
            best = min(markers, key=lambda m: (t["cen"][0] - m["cen"][0]) ** 2
                       + (t["cen"][1] - m["cen"][1]) ** 2)
            match = [best]
        else:
            match = [m for m in markers if corresponds(t, m, pred)]
        if len(match) != 1:
            return False
        newcol = match[0]["col"]
        for (r, c) in t["cells"]:
            pred_grid[r][c] = newcol
    return pred_grid == go


def task_pred(pairs, pred):
    return all(try_pred_on_pair(p["input"], p["output"], pred) for p in pairs)


def main():
    files = sorted(os.listdir(TRAIN))
    by_pred = {p: [] for p in PREDS}
    by_pred_heldout = {p: [] for p in PREDS}
    n = 0
    for fn in files:
        task = json.load(open(os.path.join(TRAIN, fn)))
        n += 1
        pairs = task["train"]
        try:
            if synthesize_task(pairs) is not None:
                continue  # already solved
        except Exception:
            continue
        tid = fn[:-5]
        for pred in PREDS:
            try:
                if task_pred(pairs, pred):
                    by_pred[pred].append(tid)
                    # held-out test transfer
                    ok = True
                    for tp in task.get("test", []):
                        if "output" not in tp:
                            ok = False; break
                        if not try_pred_on_pair(tp["input"], tp["output"], pred):
                            ok = False; break
                    if ok and task.get("test"):
                        by_pred_heldout[pred].append(tid)
            except Exception:
                pass
    print(f"scanned {n} tasks (failing only counted)")
    for pred in PREDS:
        print(f"  {pred:12s} train-fold={len(by_pred[pred]):2d} heldout-confirmed={len(by_pred_heldout[pred]):2d} :: {by_pred_heldout[pred][:12]}")
    # union across predicates with held-out confirmation
    allh = set()
    for pred in PREDS:
        allh |= set(by_pred_heldout[pred])
    print(f"UNION held-out-confirmed across predicates: {len(allh)} :: {sorted(allh)[:20]}")


if __name__ == "__main__":
    main()
