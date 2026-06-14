"""
motion — target-position *expressions* for single-object moves (BACKLOG_LOOP.md
R1, §2.5-2b).

This is the heart of R1's "lift the selection" work. An object move is
`make_grid` + `coloring` (the two frozen transformations) whose only free
argument is *where the object's bbox top-left lands*. That destination is **not**
a literal coordinate baked per task — it is one of a small vocabulary of
*argument expressions*, each a function of (grid, object), **fitted from the
example comparison** (P3/P4: the answer's reason comes from COMM/DIFF, not a
guessed value). The user's own prose for easy000a says it plainly: move the
object "to the bottom-right, *or* to the fixed coordinate (5,5)" — i.e. a corner
relation *or* a constant, recognised from the examples.

Because the destination is re-derived from each task's own pairs (never stored as
a literal on the rule), ONE value-agnostic `object_motion` rule covers the whole
family — corner tasks (easy000c/g), constant-target tasks (easy000d/h) and
translation tasks (easy000e/f) — instead of one detector per variant (the §2.5-3
accretion trap). New destination expressions are added here, to the *argument*
vocabulary under `agent/`, never as new transformation primitives (F3).

Candidate expressions, tried most-structural first:

  * ``bottom_right`` — bbox top-left lands at ``(H - obj_h, W - obj_w)`` (the
    object sits flush in the bottom-right corner of its own grid).
  * ``offset``       — bbox top-left = source top-left + a constant ``(dr, dc)``
    (a pure translation; the delta is common to every pair).
  * ``constant``     — bbox top-left = a constant ``(r, c)`` (every pair's object
    lands at the same absolute position regardless of where it started).
  * ``to_anchor``    — bbox top-left = the position of *another object* in the
    same grid (the §2.5-1 *relational* target: the canonical gravity / attraction
    / alignment pattern where the destination is named not by a grid corner or a
    constant but by a second object). This is the first target expression whose
    argument is itself a *selection over the other objects*, not a grid-level or
    object-own-property reading. The minimal value-agnostic anchor is "the single
    other object" — when the moved object is one of exactly two, the anchor is the
    other, with no literal index. Tried LAST (after every grid-relative and
    constant reading) so it only claims a task no simpler expression explains —
    e.g. one where both the mover and the anchor sit at varying positions across
    pairs, defeating ``bottom_right`` / ``offset`` / ``constant``. A future iter
    lifts the anchor to a fitted *selector* over the other objects (§2.5-2b),
    generalising past the exactly-two case; until then ``fit_target`` declines
    when there is not exactly one other object on every pair.

The output grid *shape* is a second, orthogonal argument expression (see
``fit_output_shape`` / ``output_shape`` below). In the size-preserving move family
(easy000c–h) the output is the same shape as the input; a *resizing* move
(easy000i: 6×6 → 5×5, object to the top-left) needs the output shape re-derived
from the examples too — fitted, never a literal — so the same one
``object_motion`` rule covers resizing moves alongside in-place ones. Like the
target position, the shape's destination comes from the comparison (P3/P4), and
the most-structural reading wins (a relation over a coincidental constant).
"""


def obj_origin_extent(obj):
    """Return ``((row0, col0), (height, width))`` for the object's bbox."""
    r0, c0, r1, c1 = obj["bbox"]
    return (r0, c0), (r1 - r0 + 1, c1 - c0 + 1)


def fit_target(motions):
    """Fit a value-agnostic target-position expression across example pairs.

    `motions` is a list of per-pair dicts, each::

        {"src": (r, c), "dst": (r, c), "H": int, "W": int, "oh": int, "ow": int,
         "others": [(r, c), ...]}

    where ``src``/``dst`` are the input/output object bbox top-lefts, ``H``/``W``
    the (size-preserved) grid dims, ``oh``/``ow`` the object's bbox extent, and
    ``others`` the bbox top-lefts of the *unselected* input objects (the anchor
    candidates for the relational ``to_anchor`` reading; absent / empty for
    single-object grids).

    Returns a descriptor dict naming *where the object goes* as an expression
    consistent across every pair, or ``None`` if no single expression fits (so
    the matcher declines rather than guessing). Tried most-structural first so a
    relation (corner) wins over a coincidental constant when both happen to hold.
    """
    if not motions:
        return None

    # bottom_right: object flush to the bottom-right corner of each grid.
    if all(
        m["dst"] == (m["H"] - m["oh"], m["W"] - m["ow"])
        for m in motions
    ):
        return {"kind": "bottom_right"}

    # offset: a single translation delta explains every pair.
    deltas = {
        (m["dst"][0] - m["src"][0], m["dst"][1] - m["src"][1])
        for m in motions
    }
    if len(deltas) == 1:
        dr, dc = next(iter(deltas))
        return {"kind": "offset", "delta": [dr, dc]}

    # constant: every object lands at the same absolute position.
    dsts = {m["dst"] for m in motions}
    if len(dsts) == 1:
        r, c = next(iter(dsts))
        return {"kind": "constant", "pos": [r, c]}

    # to_edge: the object slides flush against one grid *edge* along a single
    # axis, keeping its other coordinate (the canonical gravity / fall / attraction
    # pattern). The free coordinate equals the source's, so it is a pure attraction
    # toward that edge across varying start positions and varying fall distances —
    # which is exactly what defeats `bottom_right` (a *corner*, both axes snapped),
    # `offset` (one fixed delta) and `constant` (one fixed destination). It is a
    # grid relation, so it is tried after those structural readings but before the
    # object-relational `to_anchor`. The `any(... moved)` guard keeps it from
    # claiming a static (no-move) set as a degenerate "already at the edge" fall.
    if any(m["src"] != m["dst"] for m in motions):
        for edge, dst_of in (
            ("bottom", lambda m: (m["H"] - m["oh"], m["src"][1])),
            ("top",    lambda m: (0,                m["src"][1])),
            ("left",   lambda m: (m["src"][0],       0)),
            ("right",  lambda m: (m["src"][0],        m["W"] - m["ow"])),
        ):
            if all(m["dst"] == dst_of(m) for m in motions):
                return {"kind": "to_edge", "edge": edge}

    # to_anchor: the object lands on *another object*'s position — the relational
    # target (§2.5-1). The destination is named by a fitted *selector* over the
    # other (unselected) objects (§2.5-2b), so the anchor is identified even when
    # several other objects are present: the selector says *which* one is the
    # anchor. Tried LAST so it only claims a task no grid-relative or constant
    # reading explains. For each pair the anchor is the other object sitting at the
    # moved object's destination; `fit_selector` then finds one input-only
    # criterion (unique / largest / odd-one-out / …) that names that anchor in
    # *every* pair, falling back to None (decline) when none does. The degenerate
    # exactly-one-other case fits the `unique` criterion, so the prior
    # single-other behaviour is preserved as a special case of the general lift.
    anchor = _fit_anchor(motions)
    if anchor is not None:
        return {"kind": "to_anchor", "anchor": anchor}

    return None


def _fit_anchor(motions):
    """Fit a value-agnostic *selector* over the other (unselected) objects that
    names the anchor — the object whose bbox top-left equals the moved object's
    destination — in every pair. Returns the selector descriptor, or None when no
    single criterion explains every pair (so `fit_target` declines `to_anchor`).

    Needs the full other-object dicts per pair (carried on each motion as
    ``other_objs``) to run the selection vocabulary; absent them it declines."""
    from agent.dsl_expr.selection import fit_selector, position_of

    anchor_selections = []
    for m in motions:
        others = m.get("other_objs")
        if not others:
            return None
        anchor_idxs = [
            i for i, o in enumerate(others) if position_of(o) == m["dst"]
        ]
        if len(anchor_idxs) != 1:
            return None
        anchor_selections.append({"objects": others, "selected": anchor_idxs[0]})
    return fit_selector(anchor_selections)


def fit_uniform_target(motions):
    """Fit ONE *per-object* displacement target that explains **every** object's
    move at once — the multi-object "map-all" case (the canonical gravity / "all
    objects fall" pattern), generalising the single-object move from select-one to
    map-all (§2.5-2b, BACKLOG_LOOP R1 "next gap").

    `motions` is a flat list of per-object move dicts (every object across every
    pair), each ``{"src","dst","H","W","oh","ow"}`` exactly as `fit_target`
    consumes — but here each entry is *one object among several*, not the lone
    selected one. Only the two **displacement** readings are admissible for a
    map-all move: a single uniform ``offset`` (translate the whole scene by one
    delta), or a per-object ``to_edge`` fall (every object slides flush to one grid
    edge along one axis, keeping its free coordinate — independent fall distances
    per object). The *absolute* readings `fit_target` also tries
    (``bottom_right`` / ``constant`` / ``to_anchor``) collapse every object onto a
    single spot, so they never describe a map-all move and are intentionally
    excluded here. Tried most-structural-first (a uniform translation over a fall),
    mirroring `fit_target`. Returns a descriptor resolvable by `target_position`
    (which already evaluates ``offset`` / ``to_edge`` per object), or ``None`` so
    the caller declines rather than guesses.
    """
    if not motions:
        return None

    # offset: a single translation delta moves every object on every pair (a pure
    # uniform shift of the whole scene). A zero delta is a no-op, not a move.
    deltas = {
        (m["dst"][0] - m["src"][0], m["dst"][1] - m["src"][1])
        for m in motions
    }
    if len(deltas) == 1:
        dr, dc = next(iter(deltas))
        if (dr, dc) != (0, 0):
            return {"kind": "offset", "delta": [dr, dc]}

    # to_edge: every object slides flush against one grid edge along a single axis,
    # keeping its free coordinate — gravity for the whole scene. Independent fall
    # distances per object are exactly what defeats `offset`. The `any(... moved)`
    # guard keeps a static set from reading as a degenerate "already at the edge".
    if any(m["src"] != m["dst"] for m in motions):
        for edge, dst_of in (
            ("bottom", lambda m: (m["H"] - m["oh"], m["src"][1])),
            ("top",    lambda m: (0,                m["src"][1])),
            ("left",   lambda m: (m["src"][0],       0)),
            ("right",  lambda m: (m["src"][0],        m["W"] - m["ow"])),
        ):
            if all(m["dst"] == dst_of(m) for m in motions):
                return {"kind": "to_edge", "edge": edge}

    return None


def _settle_order(objs, edge):
    """Indices of `objs` ordered so the object nearest the target `edge` settles
    first (it reaches the floor / wall before anything can pile on top of it). The
    settle order is what makes stacking deterministic — a later object rests on the
    cells an earlier one already claimed."""
    def key(i):
        r0, c0, r1, c1 = objs[i]["bbox"]
        if edge == "bottom":
            return -r1   # largest bottom row settles first
        if edge == "top":
            return r0    # smallest top row settles first
        if edge == "left":
            return c0    # smallest left col settles first
        if edge == "right":
            return -c1   # largest right col settles first
        return 0
    return sorted(range(len(objs)), key=key)


def simulate_gravity_settle(objs, H, W, edge):
    """Settle every object under gravity toward one grid `edge`, stacking on
    whatever has already come to rest — the *collision* generalisation of the
    independent ``to_edge`` fall. Each object slides straight along the fall axis
    (its free coordinate kept) as far as it can without leaving the grid or
    overlapping an already-settled cell; objects nearest the edge settle first
    (`_settle_order`). Returns a list of resolved bbox top-lefts aligned with the
    *input* `objs` order (so callers can `zip(objs, dsts)`), or ``None`` for an
    unknown edge. Unlike `target_position`, an object's destination here is **not**
    resolvable in isolation — it depends on the ones already piled below it — which
    is exactly why map-all gravity with stacking needs a joint simulation rather
    than one per-object expression."""
    dirs = {"bottom": (1, 0), "top": (-1, 0), "left": (0, -1), "right": (0, 1)}
    if edge not in dirs:
        return None
    dr, dc = dirs[edge]
    occupied = set()
    dsts = [None] * len(objs)
    for i in _settle_order(objs, edge):
        cells = list(objs[i]["pixels"].keys())
        off_r, off_c = 0, 0
        while True:
            nr, nc = off_r + dr, off_c + dc
            if all(
                0 <= r + nr < H and 0 <= c + nc < W and (r + nr, c + nc) not in occupied
                for (r, c) in cells
            ):
                off_r, off_c = nr, nc
            else:
                break
        for (r, c) in cells:
            occupied.add((r + off_r, c + off_c))
        r0, c0, _r1, _c1 = objs[i]["bbox"]
        dsts[i] = (r0 + off_r, c0 + off_c)
    return dsts


def _colored_cells(objs, offsets):
    """The ``{(row, col): colour}`` map of `objs` each shifted by its bbox-top-left
    delta to a resolved destination in `offsets` (aligned with `objs`)."""
    cells = {}
    for obj, dst in zip(objs, offsets):
        r0, c0, _r1, _c1 = obj["bbox"]
        dr, dc = dst[0] - r0, dst[1] - c0
        for (r, c), col in obj["pixels"].items():
            cells[(r + dr, c + dc)] = col
    return cells


def fit_gravity_settle(per_pair):
    """Fit a value-agnostic map-all **gravity-with-stacking** target — every object
    falls toward one grid edge and *piles up* on whatever settled before it
    (BACKLOG_LOOP R1 "next gap": the stacking case `fit_uniform_target` declines,
    because two objects in one column cannot both reach the floor). For each of the
    four edges, `simulate_gravity_settle` settles the input objects and the result's
    coloured-cell map is checked against the output's *exactly*; the first edge that
    reproduces **every** pair wins. The match is on coloured cells, not an
    object bijection, so it is robust to objects *merging* when they come to rest
    adjacent (two falling cells becoming one output blob) — the very case that
    breaks the equal-count bijection path. Returns ``{"kind": "gravity_settle",
    "edge": ...}`` or ``None`` (decline). Tried only as `fit_map_all_target`'s last
    resort, so a plain (non-colliding) fall is still read as the simpler ``to_edge``.
    """
    if not per_pair:
        return None
    for edge in ("bottom", "top", "left", "right"):
        ok = True
        moved_any = False
        for (H, W, objs_in, objs_out) in per_pair:
            dsts = simulate_gravity_settle(objs_in, H, W, edge)
            if dsts is None:
                ok = False
                break
            if any(
                (o["bbox"][0], o["bbox"][1]) != d for o, d in zip(objs_in, dsts)
            ):
                moved_any = True
            predicted = _colored_cells(objs_in, dsts)
            actual = {(r, c): col for o in objs_out for (r, c), col in o["pixels"].items()}
            if predicted != actual:
                ok = False
                break
        if ok and moved_any:
            return {"kind": "gravity_settle", "edge": edge}
    return None


def fit_map_all_target(per_pair):
    """Fit ONE uniform map-all displacement target across pre-gathered example
    pairs — the multi-object gravity / "all objects fall" reading, the
    select-one→map-all generalisation of the single-object move (§2.5-2b,
    BACKLOG_LOOP R1 "next gap"). `per_pair` is a list of ``(H, W, objs_in,
    objs_out)`` tuples, one per example pair; the caller guarantees each pair is
    size-preserving with ≥2 colour-objects (in/out counts may differ — see the
    gravity-settle fallback below).

    The input→output object **bijection** is fitted most-constrained-first by
    `selection.motion_bijection`: ``identity`` (by the colour-set + size + shape a
    move preserves — the *distinct*-object case) then the axis disambiguators
    ``vertical`` / ``horizontal`` (the column / row a fall keeps) for *identical*
    objects, which the identity key alone cannot tell apart. The first strategy
    whose per-object motions are colour-preserving on every pair AND fit one uniform
    `fit_uniform_target` wins — so distinct-object gravity reads exactly as before
    (zero regression) and identical-object gravity, previously declined, is resolved
    by the preserved axis. When *no* bijection-based uniform target fits — the
    canonical case being objects that **stack** (two can't both reach the floor, and
    a pile may merge distinct input objects into one output blob, breaking the
    equal-count bijection) — `fit_gravity_settle` is tried last: a joint settle
    simulation matched on coloured cells. Returns ``{"target", "evidence_count",
    "clean"}`` or ``None`` (decline) so the caller never guesses which object fell
    where.
    """
    from agent.dsl_expr.selection import (
        motion_bijection, MOTION_BIJECTION_STRATEGIES, position_of, color_of,
    )

    if not per_pair:
        return None
    for strategy in MOTION_BIJECTION_STRATEGIES:
        all_motions = []
        ok = True
        moved_any = True
        for (H, W, objs_in, objs_out) in per_pair:
            bij = motion_bijection(objs_in, objs_out, strategy)
            if bij is None:
                ok = False
                break
            pair_moved = False
            for oi, oj in bij:
                if color_of(oi) is None or color_of(oi) != color_of(oj):
                    ok = False  # colour not preserved → not a plain move
                    break
                (oh, ow) = obj_origin_extent(oi)[1]
                src, dst = position_of(oi), position_of(oj)
                if src != dst:
                    pair_moved = True
                all_motions.append({
                    "src": src, "dst": dst, "H": H, "W": W, "oh": oh, "ow": ow,
                })
            if not ok:
                break
            if not pair_moved:
                moved_any = False  # a static scene is not a fall
                break
        if not ok or not moved_any or not all_motions:
            continue
        target = fit_uniform_target(all_motions)
        if target is not None:
            return {
                "target": target,
                "evidence_count": len(per_pair),
                "clean": True,
            }

    # Last resort: gravity with *stacking* (objects pile up, defeating the
    # per-object `to_edge` fall and possibly merging objects so no equal-count
    # bijection exists). Matched on coloured cells by a joint settle simulation.
    settle = fit_gravity_settle(per_pair)
    if settle is not None:
        return {"target": settle, "evidence_count": len(per_pair), "clean": True}
    return None


def fit_output_shape(shapes):
    """Fit a value-agnostic output-grid-shape expression across example pairs.

    `shapes` is a list of per-pair dicts ``{"in": (h, w), "out": (h, w),
    "obj": (oh, ow), "count": int}`` giving the input and output grid dimensions,
    the (size-preserved) selected object's bbox extent, and the number of objects
    in the input. Returns a descriptor naming the output shape as an expression
    consistent across every pair, or ``None`` if none fits (so the caller declines
    rather than guessing). Tried most-structural first — an identity, then a
    relation (input + constant delta), then a coincidental absolute constant, then
    an *object-property* relation (one object's own extent), and finally an
    *object-count* relation (a grid-level feature) — mirroring `fit_target`'s
    ordering.
    """
    if not shapes:
        return None

    # same: the output is the same shape as the input on every pair.
    if all(s["out"] == s["in"] for s in shapes):
        return {"kind": "same"}

    # delta: a single (dh, dw) relates input shape to output shape on every pair.
    deltas = {
        (s["out"][0] - s["in"][0], s["out"][1] - s["in"][1])
        for s in shapes
    }
    if len(deltas) == 1:
        dh, dw = next(iter(deltas))
        return {"kind": "delta", "delta": [dh, dw]}

    # constant: every output grid is the same absolute size.
    outs = {s["out"] for s in shapes}
    if len(outs) == 1:
        h, w = next(iter(outs))
        return {"kind": "constant", "dims": [h, w]}

    # object_extent: every output grid is exactly the selected object's own bbox
    # extent — the output *size is a function of an object property*, the §2.1
    # "grid size is a function of an object's feature" concept and the §2.5-2b
    # lift of a property expression into the make_grid argument. Tried last (after
    # every input-relative reading) so it only claims a task that no input-shape
    # expression explains — e.g. a crop whose object differs in size across pairs,
    # which defeats both `delta` and `constant`. Needs the per-pair object extent,
    # carried on each shape entry as "obj"=(oh, ow); absent it, this declines.
    if all(
        s.get("obj") is not None and tuple(s["out"]) == tuple(s["obj"])
        for s in shapes
    ):
        return {"kind": "object_extent"}

    # object_count: every output grid is a square whose side equals the *number
    # of objects* in the input — the output size is a function of a grid-level
    # feature (the object count), the §2.1 "grid size is a function of an object's
    # feature" concept read at the grid level rather than from one object's extent
    # (which is `object_extent` above). Tried last (after every input-relative and
    # single-object reading) so it only claims a task no other expression explains
    # — e.g. one where input size is constant but the count, and thus the output
    # side, varies across pairs, defeating delta/constant/object_extent. Needs the
    # per-pair object count, carried on each shape entry as "count"; absent it (or
    # a non-square output), this declines.
    if all(
        s.get("count") is not None
        and tuple(s["out"]) == (s["count"], s["count"])
        for s in shapes
    ):
        return {"kind": "object_count"}

    return None


def output_shape(descriptor, in_dims, obj=None, count=None):
    """Resolve an output-shape descriptor to concrete ``(height, width)`` for one
    input grid. Inverse-paired with `fit_output_shape`. The optional `obj` is the
    selected object, needed only by the `object_extent` reading (whose output size
    is that object's own bbox extent); the optional `count` is the number of input
    objects, needed only by the `object_count` reading (whose output is a
    ``count x count`` square). Returns ``None`` for an unknown descriptor — or for
    `object_extent`/`object_count` missing its object/count — so callers decline
    rather than crash."""
    if not descriptor:
        return None
    h, w = in_dims
    kind = descriptor.get("kind")

    if kind == "same":
        return (h, w)
    if kind == "delta":
        dh, dw = descriptor["delta"]
        return (h + dh, w + dw)
    if kind == "constant":
        oh, ow = descriptor["dims"]
        return (oh, ow)
    if kind == "object_extent":
        if obj is None:
            return None
        (_origin, (oh, ow)) = obj_origin_extent(obj)
        return (oh, ow)
    if kind == "object_count":
        if count is None:
            return None
        return (count, count)
    return None


def map_all_destinations(target_desc, H, W, objs):
    """Resolve a *map-all* target descriptor to a per-object destination bbox
    top-left list, aligned with `objs`. For the independent readings
    (``offset`` / ``to_edge``) each object resolves on its own via
    `target_position`; for ``gravity_settle`` the whole scene is settled jointly
    (`simulate_gravity_settle`), because a stacking object's resting place depends
    on the ones already piled below it. Returns ``None`` (decline) when any
    object's destination is undetermined — so the renderer never guesses."""
    if not target_desc:
        return None
    if target_desc.get("kind") == "gravity_settle":
        return simulate_gravity_settle(objs, H, W, target_desc.get("edge"))
    dsts = []
    for obj in objs:
        dst = target_position(target_desc, (H, W), obj, objs)
        if dst is None:
            return None
        dsts.append(dst)
    return dsts


def target_position(descriptor, grid_dims, obj, objects=None):
    """Resolve a target descriptor to a concrete bbox top-left ``(row, col)`` for
    one grid + object. Inverse-paired with `fit_target`. The optional `objects` is
    the full list of objects in the grid, needed only by the relational
    ``to_anchor`` reading (whose destination is another object's position); absent
    it, ``to_anchor`` declines. Returns ``None`` for an unknown descriptor — or for
    ``to_anchor`` when the anchor is not uniquely determined — so callers decline
    rather than crash."""
    if not descriptor:
        return None
    (r0, c0), (oh, ow) = obj_origin_extent(obj)
    h, w = grid_dims
    kind = descriptor.get("kind")

    if kind == "bottom_right":
        return (h - oh, w - ow)
    if kind == "offset":
        dr, dc = descriptor["delta"]
        return (r0 + dr, c0 + dc)
    if kind == "constant":
        r, c = descriptor["pos"]
        return (r, c)
    if kind == "to_edge":
        # fall flush against one grid edge along one axis, free coordinate kept.
        edge = descriptor["edge"]
        if edge == "bottom":
            return (h - oh, c0)
        if edge == "top":
            return (0, c0)
        if edge == "left":
            return (r0, 0)
        if edge == "right":
            return (r0, w - ow)
        return None
    if kind == "to_anchor":
        if not objects:
            return None
        # The anchor is named by a fitted selector over the *other* objects
        # (identity-based exclusion, never ==), the value-agnostic relation fitted
        # by `fit_target`. `descriptor["anchor"]` is that selector descriptor;
        # resolve it over the others (the `unique` criterion covers the
        # single-other case). Declines (None) when the selector picks no other
        # object, mirroring the fit-side gate. Falls back to the single-other
        # reading when no anchor selector is recorded (legacy descriptor).
        from agent.dsl_expr.selection import select_object

        others = [o for o in objects if o is not obj]
        anchor_sel = descriptor.get("anchor")
        if anchor_sel is not None:
            anchor = select_object(others, anchor_sel)
            if anchor is None:
                return None
            (ar, ac), _extent = obj_origin_extent(anchor)
            return (ar, ac)
        if len(others) != 1:
            return None
        (ar, ac), _extent = obj_origin_extent(others[0])
        return (ar, ac)
    return None
