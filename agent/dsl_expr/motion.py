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

`top_left` and grid-resize targets are deliberately *not* here yet — no current
task exercises them, and an untested candidate is dead vocabulary. They join when
a task (e.g. easy000i, which resizes) needs them.
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
