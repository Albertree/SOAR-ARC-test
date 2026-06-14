"""READ-ONLY probe (iter 64): does a PANEL-SELECT reduction fold >=2 currently-
failing training tasks, with held-out test transfer?

iter63's next-gap nominated *panel-SELECT* (pick the unique / odd-one-out /
content-distinguished panel of a separator-split grid) as the next compose
stage-1 widening — distinct from iter62's REFUTED panel-*split* (take a fixed
half). This probe tests it.

For each of the 1000 ARC-AGI training tasks whose train pairs the current code
(incl. existing compose) does NOT already solve:
  1. split each input into equal panels along a uniform single-colour separator;
  2. SELECT one panel by a value-agnostic selector (odd-one-out, densest, etc.);
  3. accept the selector only if it (a) names a panel on every train+test input,
     (b) the selected panel == the output directly (single-step), OR a single-step
     stage-2 schema re-fits the (selected-panel -> output) pairs, AND
     (c) the SAME program reproduces the held-out TEST output.

Reports per-selector the newly-folded task ids. Writes nothing. Pure diagnosis.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from program import synthesis as S

TRAIN_DIR = os.path.join("data", "ARC_AGI", "training")


# ---- panel splitting (value-agnostic, structural) --------------------------

def _uniform(line):
    return len(set(line)) == 1


def _split_axis(grid, axis):
    """Split ``grid`` into equal panels along ``axis`` (0=rows separators split
    vertically into row-blocks; 1=cols separators split into col-blocks).
    Separators = full uniform lines of a single shared colour. Returns the list
    of panels (each a grid) when there are >=2 equal-size panels divided by >=1
    separator, else None."""
    if axis == 1:
        grid = [list(r) for r in zip(*grid)]  # transpose: treat cols as rows
    H = len(grid)
    if H < 3:
        return None
    sep_rows = [i for i in range(H) if _uniform(grid[i])]
    if not sep_rows:
        return None
    sep_colour = grid[sep_rows[0]][0]
    # every separator must be the same colour, and a separator row must not be a
    # whole panel (so the colour genuinely delimits, not fills)
    if any(grid[i][0] != sep_colour or not _uniform(grid[i]) for i in sep_rows):
        return None
    # build panels = maximal runs of non-separator rows
    panels = []
    cur = []
    for i in range(H):
        if i in sep_rows:
            if cur:
                panels.append(cur)
                cur = []
        else:
            cur.append(grid[i])
    if cur:
        panels.append(cur)
    if len(panels) < 2:
        return None
    sizes = {len(p) for p in panels}
    if len(sizes) != 1:
        return None  # require equal-size panels (clean separator grid)
    if axis == 1:
        panels = [[list(r) for r in zip(*p)] for p in panels]  # transpose back
    return panels


def split_panels(grid):
    """Return (axis, panels) for the first axis that yields a clean split, else
    None."""
    for axis in (0, 1):
        p = _split_axis(grid, axis)
        if p is not None:
            return axis, p
    return None


# ---- panel selectors (value-agnostic) --------------------------------------

def _nonbg_count(panel):
    bg = _bg(panel)
    return sum(1 for row in panel for v in row if v != bg)


def _bg(panel):
    from collections import Counter
    c = Counter(v for row in panel for v in row)
    return c.most_common(1)[0][0]


def _ncolours(panel):
    return len({v for row in panel for v in row})


def _odd_one_out(panels):
    """The single panel differing from all others (others mutually equal)."""
    for i in range(len(panels)):
        rest = panels[:i] + panels[i + 1:]
        if all(r == rest[0] for r in rest) and panels[i] != rest[0]:
            return panels[i]
    return None


def _extremum(panels, key, pick_max):
    vals = [key(p) for p in panels]
    target = max(vals) if pick_max else min(vals)
    winners = [p for p, v in zip(panels, vals) if v == target]
    if len(winners) != 1:
        return None  # ambiguous selection is not value-agnostic
    return winners[0]


SELECTORS = {
    "odd_one_out": lambda ps: _odd_one_out(ps),
    "densest": lambda ps: _extremum(ps, _nonbg_count, True),
    "sparsest": lambda ps: _extremum(ps, _nonbg_count, False),
    "most_colours": lambda ps: _extremum(ps, _ncolours, True),
    "fewest_colours": lambda ps: _extremum(ps, _ncolours, False),
}


def select_panel(grid, selname):
    sp = split_panels(grid)
    if sp is None:
        return None
    _, panels = sp
    return SELECTORS[selname](panels)


# ---- fold test -------------------------------------------------------------

def reduce_inputs(selname, pairs):
    inter = []
    for p in pairs:
        g = select_panel(p["input"], selname)
        if g is None:
            return None
        inter.append(g)
    return inter


def fold_program(selname, pairs):
    """Return a (post_program, is_direct) if panel-select + (identity|single-step)
    reproduces every train pair, else None. is_direct=True means selected panel ==
    output (stage-2 identity)."""
    inter = reduce_inputs(selname, pairs)
    if inter is None:
        return None
    # direct: selected panel IS the output
    if all(inter[i] == pairs[i]["output"] for i in range(len(pairs))):
        return ([], True)
    # else re-fit a single-step stage-2
    pairs2 = [{"input": inter[i], "output": pairs[i]["output"]}
              for i in range(len(pairs))]
    for post in S._candidate_programs(pairs2):
        if not post:
            continue
        ok = True
        for i, p in enumerate(pairs):
            try:
                if S.run_program(post, inter[i]) != p["output"]:
                    ok = False
                    break
            except S._Unevaluable:
                ok = False
                break
        if ok:
            return (post, False)
    return None


def transfers_to_test(selname, post, task):
    """Does panel-select + post reproduce every held-out TEST output?"""
    tests = task.get("test", [])
    if not tests:
        return False
    for t in tests:
        if "output" not in t:
            return False
        red = select_panel(t["input"], selname)
        if red is None:
            return False
        if not post:  # direct
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
    files = sorted(os.listdir(TRAIN_DIR))
    folds = {k: [] for k in SELECTORS}
    folds_heldout = {k: [] for k in SELECTORS}
    applied = {k: 0 for k in SELECTORS}
    for idx, fn in enumerate(files):
        tid = fn[:-5]
        with open(os.path.join(TRAIN_DIR, fn)) as f:
            task = json.load(f)
        pairs = [{"input": p["input"], "output": p["output"]}
                 for p in task["train"]]
        hits = {}
        for name in SELECTORS:
            if reduce_inputs(name, pairs) is not None:
                applied[name] += 1
                res = fold_program(name, pairs)
                if res is not None:
                    hits[name] = res
        if hits:
            baseline = S.synthesize_task(pairs)
            if baseline is None:  # currently failing
                for name, (post, direct) in hits.items():
                    tag = "direct" if direct else (post[0][0] if post else "?")
                    folds[name].append((tid, tag))
                    if transfers_to_test(name, post, task):
                        folds_heldout[name].append((tid, tag))
        if (idx + 1) % 100 == 0:
            print(f"[{idx+1}/{len(files)}] "
                  + " ".join(f"{k}:fold={len(folds[k])},held={len(folds_heldout[k])}"
                             for k in SELECTORS), flush=True)

    print("\n===== RESULT (newly-folded currently-failing tasks) =====", flush=True)
    for name in SELECTORS:
        print(f"\n--- {name}: applied={applied[name]} "
              f"train-fold={len(folds[name])} held-out-fold={len(folds_heldout[name])} ---",
              flush=True)
        for tid, tag in folds[name]:
            ho = " [HELD-OUT OK]" if (tid, tag) in folds_heldout[name] else ""
            print(f"  {tid}  stage2={tag}{ho}", flush=True)


if __name__ == "__main__":
    main()
