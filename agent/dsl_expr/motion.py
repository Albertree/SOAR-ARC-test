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

        {"src": (r, c), "dst": (r, c), "H": int, "W": int, "oh": int, "ow": int}

    where ``src``/``dst`` are the input/output object bbox top-lefts, ``H``/``W``
    the (size-preserved) grid dims, and ``oh``/``ow`` the object's bbox extent.

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


def target_position(descriptor, grid_dims, obj):
    """Resolve a target descriptor to a concrete bbox top-left ``(row, col)`` for
    one grid + object. Inverse-paired with `fit_target`. Returns ``None`` for an
    unknown descriptor so callers decline rather than crash."""
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
    return None
