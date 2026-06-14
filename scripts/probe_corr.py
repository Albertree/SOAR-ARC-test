"""Read-only probe: how many currently-failing same-dims training tasks are
'recolour by object-correspondence' — i.e. input and output have an identical
set of object footprints (same positions+shapes), differing ONLY in colour?
This sizes the object-correspondence lever (iter-59's big remaining gap).
Writes nothing.
"""
import json, os, sys
sys.path.insert(0, os.getcwd())

from program.synthesis import synthesize_task, background_of, objects_of

TRAIN = "data/ARC_AGI/training"


def footprints(grid):
    """Set of object footprints (frozenset of bbox-relative coords), colour-blind
    shape, plus a parallel list of (footprint, colour)."""
    bg = background_of(grid)
    objs = objects_of(grid, bg, same_color=True)
    fps = []
    for o in objs:
        cells = list(o["cells"])
        if not cells:
            continue
        fp = frozenset(cells)  # absolute footprint (position + shape)
        r, c = cells[0]
        col = grid[r][c]
        fps.append((fp, col))
    return fps


def is_recolor_corr(pairs):
    for p in pairs:
        gi, go = p["input"], p["output"]
        if len(gi) != len(go) or len(gi[0]) != len(go[0]):
            return False
        fi = footprints(gi); fo = footprints(go)
        # same footprints (abs position+shape), ignoring colour
        si = sorted(fp for fp, _ in fi)
        so = sorted(fp for fp, _ in fo)
        if si != so:
            return False
        # at least one colour changed (else identity)
    # require some colour change overall
    changed = False
    for p in pairs:
        if p["input"] != p["output"]:
            changed = True
    return changed


def main():
    files = sorted(os.listdir(TRAIN))
    hits = []
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
        try:
            if is_recolor_corr(pairs):
                hits.append(fn_name[:-5])
        except Exception:
            pass
    print(f"scanned {n}; recolor-by-correspondence candidates: {len(hits)}")
    print(hits[:40])


if __name__ == "__main__":
    main()
