# SOAR-ARC Session Log

---
## Iter 14 — 2026-06-14 — branch test33

**Diagnosis**: In `madeup` (7/7, easy_a 9/9) the object_motion selector vocabulary
names which object moves along three orthogonal dimensions — size
(largest/smallest), position (topmost/…/rightmost) and colour (odd_color) — but
**shape** is an unhandled fourth dimension: when several blobs are equal in size
*and* colour and none is at a position extreme, differing only in shape, no
selector fits and the move declines. Smallest defensible step: author a task that
isolates exactly that gap and add a value-agnostic `odd_shape` selector
(structure-identity odd-one-out), so the *same* one object_motion rule names the
acted-on object on the shape dimension too — lifting the selector, not adding a
detector (§2.5-2b).

**Change**:
- `data/ARC_madeup/mo_select_odd_shape.json` (NEW, F1-exempt) — four same-colour,
  same-size objects (three identical I-trominoes + one L-tromino); the odd-shaped
  one moves to the bottom-right corner, the rest preserved. Confirmed it **failed
  before** the fix (fell to a spurious `color_mapping`, INCORRECT) — every size,
  colour, position and `unique` selector declines, so only a shape criterion can
  name the moved object. Layouts chosen so no position selector picks the odd
  object in either pair (ties/wrong picks), forcing the fit through to `odd_shape`.
- `agent/dsl_expr/selection.py` — added `_shape_signature` (cells normalised to
  the bbox origin → translation-invariant) and `_odd_shape_index` (the object
  whose shape signature is unique among the objects; declines on tie / all-same /
  all-distinct, mirroring `_odd_color_index`); appended `"odd_shape"` LAST in
  `_SELECTOR_KINDS` and wired it into `_selection_index`. Updated `select_object`
  / `fit_selector` docstrings + the selector-vocabulary comment. Value-agnostic
  and G0-only (P5): keys on within-grid shape *uniqueness*, never a literal shape.
- `tests/test_object_motion.py` (+4) — `odd_shape` picks the L among I-trominoes;
  declines when all-same / two-of-each; is colour-agnostic (picks by shape even
  when colours differ); and `fit_selector` resolves to `odd_shape` on the madeup
  task's train pairs when size/position/colour all fail.
- NO `agent/active_operators.py` edit: the `preserve` scene already identifies the
  moved object by leftover-after-pixel-identity matching, so same-colour/same-size
  objects need no match-key change. F8 not engaged.

**Probe before**: easy_a 9/9; madeup 7/7 (mo_select_odd_shape absent); rules=2;
rule_002 covers=14; P1=P2=8.0; 82 tests.
**Probe after** : easy_a 9/9; madeup 8/8 (new task *merged* into object_motion);
rules=2 (no accretion); rule_002 covers=15, target still `?v1` + trace preserved;
**P1=P2=8.5**; 86 tests.

**Invariants**: forbidden=none (check_invariants CLEAN, exit 0); positives=**P1
+0.5 (8.0→8.5), P2 +0.5 (8.0→8.5)** via covers union (no new rule — §2.5-4 litmus
satisfied: coverage up, rule count flat); P3/P4/P5 ±0; P6 ±0 (no active_operators
edit). The new selector grows the LHS argument vocabulary under `agent/` (not the
frozen DSL dir), exactly where BACKLOG_LOOP §2.5-1 says it must.

**Next gap (note for future iter)**: selection is now size ∪ position ∪ colour ∪
shape — a broad spread; the remaining within-family gaps are *structural*, not new
scalar selectors: a move where **>1 object moves** (the iter12 note — `_identify_move`
still requires exactly one moved object) or where unselected objects transform.
The two standing big-ticket rungs are unchanged: **R5** (object_motion declines the
fast path because its args are fitted from the example comparison; stored hits 0)
and **cross-family AU** (rule_001 ↔ rule_002 share no skeleton — needs a Slow-path
synthesizer emitting per-pair programs with divergent args).

---
## Iter 13 — 2026-06-14 — branch test33

**Diagnosis**: Iters 5–12 climbed R1 by adding one more *fitted-expression
dimension* to the object_motion family each iter — every §2.1 concept is now
covered, but the work grew `active_operators.py` (P6 the wrong way) while the
lowest **unproven** rung, **R3 (anti-unification)**, stayed at **P3=0.0** for the
entire branch. The architectural blocker (iter10 correction): the save path never
called `unify()`, *and* every rule stored `action.args={}`, so no two rules ever
diverged for AU to lift. Smallest defensible R3 step: record the fitted *target
expression* (place_object's principal argument) on the rule and add the
sanctioned `save_rule()` that anti-unifies same-skeleton rules whose target
diverges — making `unify()` fire on real data for the first time. Safe because
`PredictOperator` re-derives the concrete target from WM patterns (never from
`args`), so recording the expression cannot change solving.

**Change**:
- `agent/memory.py` — new `save_rule()` (the CLAUDE.md §8 sanctioned save +
  the **only** `unify()` caller) + helpers `_rule_skeleton`, `_entry_to_view`,
  `_rule_to_view`, `_absorb_or_lift`, `_write_json`. Canonical
  `{condition, action}` rules sharing a skeleton `(condition.type, action.dsl)`
  are folded into ONE stored rule: identical args → plain covers-merge; divergent
  args → `unify()` lifts the divergent position to `?v`, writes the trace, unions
  covers. Already-abstract rules absorb new tasks without re-lift (idempotent —
  one trace per family). Legacy rules (no skeleton) fall back to `save_rule_to_ltm`.
- `agent/active_operators.py` — `GeneralizeOperator` records the fitted `target`
  expression in the object_motion rule's `action.args` (was `{}`). This is the
  argument expression AU lifts (§2.5-2); predict is unaffected.
- `agent/active_agent.py` — slow-path save now routes through `save_rule`
  (was `save_rule_to_ltm`). (F8 pairing for the active_operators edit.)
- `procedural_memory/rule_002.json` — regenerated: now the AU-abstract rule
  (`action.args.target = "?v1"`, `anti_unification_trace` set, covers all 14
  move tasks) instead of `args={}`. rule_001 unchanged.
- `tests/test_save_rule_au.py` (NEW, +5) — divergent-target lift, identical-args
  merge, abstract-absorb idempotency, skeleton-mismatch isolation, legacy fallback.
- `tests/test_object_motion.py` — updated to the new contract: WM rule carries a
  value-agnostic `{"kind":...}` target *expression* (not `args=={}`); the
  "one rule covers the family" invariant now asserted at the **storage** level
  (save all five → one rule, target `?v`, covers union, trace set).

**Probe before**: easy_a 9/9; madeup 7/7; rules=2; rule_002 covers=14, args={};
P1=P2=8.0; P3=0.0; 77 tests.
**Probe after** : easy_a 9/9; madeup 7/7; rules=2 (no accretion); rule_002 covers=14,
target lifted to `?v1` + `anti_unification_trace`; P1=P2=8.0; **P3=0.5**; 82 tests.

**Invariants**: forbidden=none (check_invariants CLEAN, exit 0); positives=**P3
+0.5 (0.0→0.5)** — first AU lift on this branch; P1/P2 held 8.0 (covers preserved
via union, no accretion — §2.5-4 litmus satisfied: P3 up, P1/P2 not down);
P4/P5 ±0; P6 +18 lines (the recorded-arg comment + save_rule wiring; F8 satisfied
by the memory.py pairing).

**Next gap (note for future iter)**: AU now fires but lifts only **one** field
(`target`). The other fitted argument expressions (`out_shape`, `selector`,
`scene`) are still re-derived per task and NOT recorded on the rule, so they are
not yet anti-unified — recording them would deepen the abstraction (more lifted
positions, P3-structure) the same value-agnostic way. The bigger standing
frontier is unchanged: **R5** (object_motion still declines the fast path because
predict needs the example comparison; stored hits 0) and a true **Slow-path
synthesizer** that emits per-pair programs whose divergent args AU lifts across
*different families* (rule_001 ↔ rule_002 share no skeleton yet).

---
## Iter 12 — 2026-06-14 — branch test33

**Diagnosis**: In `madeup` (authored 6/7) every §2.1 concept the object-motion
family reads is a *scalar* (target / output-shape / selector), and all produce a
*single-object* output — the iter-11 next-gap flagged the untouched structural
frontier: a task whose output **keeps the unselected objects** (output cardinality
> 1). `_object_motion` identified the moved object only when `len(objs_out) == 1`,
so any multi-object output declined → fell to identity. Smallest defensible step:
add the fitted **scene** expression (drop vs preserve) so the same one rule names
what becomes of the *other* objects, exposed by one authored task.

**Change**:
- `agent/active_operators.py` — new `ExtractPatternOperator._identify_move(objs_in,
  objs_out)` returns `(sel_idx, obj_out, scene)`: the existing single-output match
  is `scene="drop"`; a new branch recognises `scene="preserve"` (same object count
  in/out, every object but one byte-identical in place, exactly one moved). A fitted
  `scene` (all clean pairs must agree) joins target/out_shape/selector in the motion
  dict. `_render_object_motion` gains a `scene_desc` param: on `"preserve"` it
  repaints every unselected object at its G0 position (P5) before the moved object
  lands, declining if any cell falls off-grid. Rule dict unchanged
  (`place_object`, `args={}`) so it MERGES — no new family.
- `agent/conditions/object_motion.py` — matcher gate drops the per-pair `single_out`
  requirement (multi-object outputs are now valid) and adds a motion-level
  `scene is not None` requirement (the fate of the others must be named, not
  guessed). Docstring updated. (F8 pairing for the active_operators edit.)
- `data/ARC_madeup/mo_preserve_others.json` (NEW, F1-exempt) — 2 objects in, the
  `largest` moves to the bottom-right corner, the other is preserved unchanged;
  colours differ per pair (value-agnostic). Confirmed it failed → identity before
  the fix (declined: 2 output objects).
- `tests/test_object_motion.py` — `_motion` helper carries `scene`; +6 tests
  (matcher needs scene / fires for preserve; `_identify_move` drop/preserve/ambiguous;
  end-to-end preserve solves via the SAME rule object as easy000c).

**Probe before**: madeup 6/6; easy_a 9/9; rules=2; rule_002 covers=13; P1=P2=7.5;
71 tests.
**Probe after** : madeup 7/7 (mo_preserve_others *merged* into object_motion);
easy_a 9/9; rules=2 (no accretion); rule_002 covers=14; P1=P2=8.0; 77 tests pass.

**Invariants**: forbidden=none (check_invariants CLEAN); positives=P1 +0.5
(7.5→8.0), P2 +0.5 (7.5→8.0), P3/P4/P5 ±0, P6 +75 lines (identify + preserve
render; net add, no new matcher or primitive). F8 satisfied (active_operators
paired with conditions/object_motion.py).

**Next gap (note for future iter)**: object_motion now reads selector
(size∪position∪colour), target, output-shape (same/delta/constant/extent/count)
and scene (drop/preserve) — a broad spread, 7 authored madeup tasks, graduation
gate met pending the K=5 clean streak. The preserve render still assumes the
*other* objects are stationary; a task where >1 object moves, or where the
unselected ones transform too, is untouched. The standing big-ticket frontier is
unchanged: **R3** (P3=0.0 — `unify()` implemented but `save_rule_to_ltm` merges by
exact equality, args={} everywhere ⇒ no divergent skeleton to lift; needs a
Slow-path synthesizer) and **R5** (object_motion declines the fast path, stored
hits 0).

---
## Iter 11 — 2026-06-14 — branch test33

**Diagnosis**: In the `madeup` phase (authored 5/7) the remaining §2.1 concept
the structure could not yet express is **"grid size is a function of the object
*count*"** — distinct from the object-*extent* reading closed iter7. The
`fit_output_shape` vocabulary had only same / delta / constant / object_extent,
so a task whose output side equals the number of input objects falls through to
`identity`. Smallest defensible step: author one task isolating that concept and
add the single `object_count` output-shape *argument expression* so the existing
`object_motion` rule covers it (merge, no new family / detector / DSL primitive).

**Change**:
- `data/ARC_madeup/mo_size_by_count.json` (NEW, F1-exempt corner) — 2 pairs, both
  5×5 inputs with object counts 3 then 4; output is a count×count square holding
  the topmost object at (0,0). Inputs are constant size so the output sides (3,4)
  defeat `delta` (−2 vs −1), `constant`, and `object_extent` (1×1); only the
  object count explains them. Confirmed it failed → `identity` before the fix.
- `agent/dsl_expr/motion.py` — added the `object_count` reading to
  `fit_output_shape` (last, after `object_extent`, so no input-relative or
  single-object reading is overridden) + its resolver in `output_shape`
  (`count×count`; declines when no count supplied). Value-agnostic: the count is
  re-derived from each task's G0 (P5), never stored.
- `agent/active_operators.py` — `_object_motion` records each pair's input object
  count on the shape entry; `_render_object_motion` passes `len(objs)` to
  `output_shape` so the canvas side resolves per test input.
- `agent/conditions/object_motion.py` — docstring extended to name the
  `object_count` reading (F8 pairing for the active_operators edit; no logic
  change — the matcher already only requires *a* fitted `out_shape`).
- `tests/test_object_motion.py` — +4 tests: object_count fit, loses-to-input-
  relative ordering, declines on non-square output, resolver needs-count.

**Probe before**: madeup 5/5 (pre-authored set); easy_a 9/9; rules=2; rule_002
covers=12; P1=P2=7.0; 67 tests.
**Probe after** : madeup 6/6 (mo_size_by_count *merged* into object_motion, not a
new rule); easy_a 9/9; rules=2 (no accretion); rule_002 covers=13; P1=P2=7.5;
71 tests pass.

**Invariants**: forbidden=none (check_invariants CLEAN); positives=P1 +0.5
(7.0→7.5), P2 +0.5 (7.0→7.5), P3/P4/P5 ±0, P6 +7 lines (net add, no new matcher
or primitive). F8 satisfied (active_operators paired with conditions/ edit).

**Next gap (note for future iter)**: output-shape vocabulary now reads same /
delta / constant / object_extent / object_count; selection reads size ∪ position
∪ colour. The output-shape readings still only produce *square* count grids and
*single-object* outputs — a task whose output keeps the *unselected* objects, or
whose size is a non-square function of a feature, is untouched. The standing
big-ticket frontier is unchanged: **R3** (P3=0.0 — `unify()` is implemented but
the live `save_rule_to_ltm` merges by exact equality and never calls it; needs a
Slow-path synthesizer emitting per-pair programs with *divergent* args) and
**R5** (fast-path reuse: object_motion declines the fast path, stored hits 0).
## Iter 9 — 2026-06-14 — branch test33

**Diagnosis**: easy_a is mastered (9/9, clean-streak 4/5) and the #1 gap named
by every iter 5–8 is **R3 — anti-unification has never fired** (P3=0.0 the whole
branch): `program/anti_unification.py` was unimplemented `pass` stubs, and
`program/__init__.py` imported a non-existent `anti_unify`, so `import program`
was a latent `ImportError`. Iters 6/7/8 each did a selection/shape-lift folding
into rule_002 (+0.5 P1/P2); a 4th would be the §2.2 spinning failure. The
smallest defensible non-duplicate step is the keystone R3 deliverable already
fully specified in `docs/ANTI_UNIFICATION.md §1–§3`: implement the **leaf-case**
`unify()` (`==` value positions; recursive term-tree DP explicitly out of scope
per §2) and fix the import.

**Change**:
- `program/anti_unification.py` — replaced the stubs with the spec'd
  `unify(rules, *, episodic_memory_root)`, `UnifyResult` (with
  `.is_more_general()`), and `NoCommonSkeleton`. Skeleton-checks `condition.type`
  / `action.dsl`; field-wise anti-unifies `condition.params` + `action.args`
  (agree→deep-copy keep, disagree-or-absent→fresh `?vN`); strictest
  `min_evidence`; first-seen `covers` union; writes the immutable forensic trace
  JSON (`au_NNN.json`, forward-slash path matching RULE_FORMAT V5). `anti_unify`
  kept as a back-compat alias.
- `program/__init__.py` — export `unify`/`UnifyResult`/`NoCommonSkeleton`
  (+`anti_unify`); fixes the `ImportError`.
- `tests/test_anti_unification.py` — 17 tests: skeleton guards, leaf lifting,
  absent-key disagreement, sequential var numbering, no-aliasing deep-copy,
  covers union, trace shape + sequence increment, V5-regex compliance.
- `docs/ANTI_UNIFICATION.md §4` — corrected the false "wired in iter 6" claim;
  the `save_rule()` call site is **not** in `agent/memory.py` (live writer is
  still `save_rule_to_ltm`, equality-merge only), so AU sees no production
  traffic yet. Honest status note added.

**Probe before**: easy_a 9/9; rules=2; P1=P2=6.5; P3=0.0; `import program` raised
ImportError; 46 tests.
**Probe after** : easy_a 9/9 (unaffected — solver untouched); rules=2; P1=P2=6.5;
P3=0.0; `import program` OK; 63 tests pass.

**Invariants**: forbidden=none (check_invariants exit 0, CLEAN). positives: all
Δ=0 → **NEUTRAL** iter. This is foundational scaffolding (INVARIANTS §3): P3
cannot rise until a lifted rule is persisted into `procedural_memory/`, which
needs the `save_rule()` wiring AND pair-specific argument-expression rules to
lift — neither exists yet. Chosen over a 4th spinning selection-lift.

**Next gap (note for future iter)**: wire `unify()` into a sanctioned
`agent/memory.py:save_rule()` (CLAUDE.md §8 single call site) and feed it two
rules that share a skeleton but differ in args — but the deeper blocker is that
the live pipeline stores `action.args={}` and re-fits generalization in runtime
matchers, so there are no materialized argument-expression programs for `unify()`
to lift. Producing those (the Slow-path synthesizer, modules F/G) is the real
prerequisite for P3 to move off 0.

---
## Iter 5 — 2026-06-14 — branch test33

**Diagnosis**: easy_a was 8/9; the only blind spot was **easy000i**, which moves
a single object to (0,0) *while resizing the grid* (6×6 → 5×5). The `object_motion`
family declined it because the matcher required `grid_size_preserved` per pair and
the render built the output canvas at the *input* shape — there was no way to
express "the output grid is a different, fitted shape." This is the genuinely new
R1 capability (the R1→graduation step): an **output-shape argument expression**,
orthogonal to the already-lifted target-position expression. Smallest defensible
step: add that one expression to the *argument* vocabulary (no new transformation
primitive, no new matcher, no `_try_*`), so the same single rule covers resizing
moves alongside in-place ones.

**Change**:
- `agent/dsl_expr/motion.py` — added `fit_output_shape` (same / input+delta /
  constant, most-structural first, mirroring `fit_target`) + `output_shape`
  resolver. Value-agnostic: the output shape is re-derived from each task's
  comparison, never a literal (P3/P4).
- `agent/dsl_expr/__init__.py` — export the two new expressions.
- `agent/active_operators.py` — `_object_motion` now records per-pair output
  dims, fits an `out_shape` expression, and stops gating the geometry record on
  `grid_size_preserved` (motion H/W now use *output* dims so a corner target lands
  flush even on resize; unchanged for same-size tasks). `PredictOperator` reads
  `out_shape` and passes it to `_render_object_motion`, which builds the canvas at
  the fitted output shape (defaults to input shape when absent).
- `agent/conditions/object_motion.py` — matcher drops the per-pair
  `grid_size_preserved` requirement (resizes are allowed) and now also requires a
  fitted `out_shape`; in-place moves fit `out_shape == same`, so c–h are unchanged.
- `tests/test_object_motion.py` — added output-shape fitter/resolver tests, a
  matcher-declines-without-out_shape test, and an end-to-end resize task (easy000i)
  that resolves to the *same* rule object as the corner/constant/offset tasks.

**Probe before**: easy_a 8/9; rule_count 2; rule_002 covers=6 (c–h); P1/P2 4.0.
**Probe after** : easy_a 9/9; rule_count 2 (no accretion); rule_002 covers=7
(c–i, easy000i *merged*); P1/P2 4.5.

**Invariants**: forbidden=none (check_invariants CLEAN); positives=P1 +0.5
(4.0→4.5), P2 +0.5 (4.0→4.5), P5 ±0, P6 −37 lines (net add, no new matcher). All
30 unit tests pass.

**Next gap (note for future iter)**: easy_a is now 100% — the loop should graduate
toward `madeup` after K clean iters. The standing unfired big-ticket rungs are
**R3** (anti_unification: P3 still 0.0 — no rule has been *lifted* across a shared
skeleton by `unify()`; rule_001 and rule_002 each generalize within their own
matcher, not across) and **R5** (fast-path reuse: both `constant_output` and
`object_motion` decline the fast path because their arguments are fitted from the
example comparison, so stored-rule hits stay 0). A `madeup` task isolating
multi-object *selection* would be the natural next probe.

---
## Iter 1 — 2026-06-12 — branch test31

**Diagnosis**: Lowest unproven rung is **R0 (GRID-level COMM-copy)** — this is a
pre-iter clean-start node, so R0 is (re)built from scratch (BACKLOG_LOOP §3).
The constant-output family (easy0001/0005/0009/0013/000a/000b — *all training
outputs identical*, verified against the data) is R0's exact target, yet the
stale pipeline mislearns them as bogus `color_mapping` rules (probe: all
INCORRECT) and saves them with **no `condition`/`action`** (F4-violating dead
memory; the 진단#4 "dropped condition" failure). R0's build list calls for a
`constant_output` condition matcher plus the COMM signal it keys on — neither
existed (`agent/conditions/` was empty, P5=0). Smallest defensible step: lay
R0's *recognition* substrate (the smaller half; generation+prediction is a later
iter), not the whole COMM-copy path.

**Change**:
- `agent/conditions/__init__.py` (new) — the condition-matcher registry:
  `CONDITION_REGISTRY`, `register`/`get_matcher`/`match`, auto-import of sibling
  matchers. Recognition vocabulary (CLAUDE.md §6.3), separate from the frozen
  transformation DSL.
- `agent/conditions/constant_output.py` (new) — first matcher `constant_output`:
  fires when every example output grid is identical (Inter-Grid G1 COMM),
  value-agnostically covering the whole constant-output family with one module.
- `agent/active_operators.py` — `ExtractPatternOperator.effect` now surfaces the
  `output_invariant` signal (all example outputs equal? + `common_output` +
  `evidence_count`), the COMM evidence the matcher consumes. No new `_try_*`;
  net +19 lines (the COMM computation, not detector accretion). F8 companion =
  `agent/conditions/`.
- `procedural_memory/rule_001..003.json` (deleted) — schema-invalid (`condition`-
  less) `color_mapping` rules regenerated by the stale pipeline; INCORRECT in the
  probe; discarded per clean-start intent (Step 3 allows deleting schema-violating
  rules). This is why P1/P2 drop — they were illusory coverage from dead rules
  (진단#5), not real generalization.
- `tests/test_constant_output.py` (new) — unit (synthetic patterns) + integration
  (real `ExtractPatternOperator` on easy0001) proving matcher↔pipeline schema
  agreement. 7/7 pass.

**Probe before**: easy 0/3, easy_a 0/9; rules=3 (all condition-less); P1=1.33
**Probe after** : matcher not yet wired into generalize/predict, so solve-rate
unchanged (substrate iter); rules=0; P5=1; tree is F4-clean.

**Invariants**: forbidden=none; positives = P5 +1 (0→1). P1 −1.33, P2 −1.33
(removal of 3 invalid dead rules), P6 −19 (active_operators grew by the COMM
computation; not `_try_*`). Verdict CLEAN.

**Next gap (note for future iter)**: the matcher exists but nothing consumes it —
wire `GeneralizeOperator` to emit a canonical `{condition: constant_output,
action: make_grid+coloring}` rule (reconstructing `common_output` from the two
frozen primitives) and have `predict`/`save_rule_to_ltm` produce/persist it in
`{condition, action}` form. That both *solves* the constant-output family the
intended way and stops the stale pipeline from regenerating F4-dirty
`color_mapping` rules each probe.

---
## Learning Loop -- 2026-06-12 11:23

- Split: None, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 0 -> 1 (+1 learned)
- Stored rule hits: 0
- Time: 1s
- Log: logs/learn_20260612_112311.log

---
## Learning Loop -- 2026-06-12 11:23

- Split: None, Tasks: 9
- Correct: 0 / 9 (0.0%)
- Rules: 1 -> 3 (+2 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260612_112313.log

---
## Learning Loop -- 2026-06-14 15:01

- Split: None, Tasks: 9
- Correct: 0 / 9 (0.0%)
- Rules: 0 -> 2 (+2 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260614_150115.log

---
## Learning Loop -- 2026-06-14 15:10

- Split: None, Tasks: 9
- Correct: 2 / 9 (22.2%)
- Rules: 0 -> 1 (+1 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260614_151043.log

---
## Iter 2 — 2026-06-14 — branch test33

**Diagnosis**: R0 was half-built — the prior iter added the `output_invariant`
COMM evidence (ExtractPatternOperator) and the `constant_output` matcher, but
*nothing consumed them*: GeneralizeOperator ran only the legacy
`_try_recolor_sequential`/`_try_color_mapping`, so easy000a/b (constant-output)
were mis-generalized into per-task `color_mapping` rules that solved nothing
(probe 0/9) and were schema-dirty (no `condition`/`action`, latent F4). On top of
that the two frozen DSL primitives (`make_grid`/`coloring`) existed only as
orphaned `.pyc` with no source (the `cleanstart_orphaned_pyc` trap). Smallest
defensible step = close R0's prediction path: rebuild the DSL substrate and wire
the existing matcher → generalize → predict → save into one **value-agnostic**
COMM-copy rule.

**Change**:
- `procedural_memory/DSL/{__init__,apply,make_grid,coloring}.py` — rebuilt the
  two frozen transformation primitives + `apply_DSL` dispatcher as source (F3:
  exactly these two registered).
- `agent/active_operators.py` — GeneralizeOperator now consults the
  `constant_output` matcher *first* (via the condition registry, `_matches_
  constant_output`) and emits a canonical `{condition, action}` rule with
  `action.dsl=copy_common_output` and **no literal grid** (value-agnostic).
  PredictOperator reconstructs the common example output from `make_grid` +
  `coloring` (`_render_common_output`) — no new `_try_*`/`_apply_*`.
- `agent/memory.py` — `save_rule_to_ltm` now surfaces top-level
  `condition`/`action` when the rule carries them (F4-clean, F8 companion edit).
- `tests/test_constant_output.py`, `managers/arc_manager.py` — migrate the
  retired `easy0001` reference to the current `easy000a`; add `ARC_easy_a`/
  `ARC_madeup` to `load_task` candidate paths.
- Deleted stale F4-dirty untracked `rule_001/002.json` (legacy color_mapping);
  re-run produced one canonical `rule_001.json`.

**Probe before**: easy_a 0/9; rules=2 (color_mapping, dead, covers paper-only)
**Probe after** : easy_a 2/9; rules=1 constant_output, covers=[easy000a,easy000b]

**Invariants**: forbidden=none, positives=P1 1.0→2.0 (+1.0), P2 1.0→2.0 (+1.0),
P6 +86 lines (within F8: memory.py touched). Verdict CLEAN.

**Next gap (note for future iter)**: R0 slow path is done; the fast-path reuse
(`active_agent.solve` lines 60-75) still declines `constant_output` because
`_apply_rule(rule, input_grid)` cannot reconstruct the common output without the
examples — Stored-rule hits stay 0. Wiring value-agnostic reuse there (compute
common output from `task.example_pairs`) is R5. The lowest *unproven* rung is now
R1: easy000c–i need object-level analysis (color = input color, position fixed),
which the constant_output matcher correctly does not fire on.

## Iter 2 [CLEAN] — 20260614_150115 — branch test33
- Probe: easy_a: [15:01:18] Correct:     0 / 9  (0.0%)

---
## Learning Loop -- 2026-06-14 15:13

- Split: None, Tasks: 9
- Correct: 2 / 9 (22.2%)
- Rules: 1 -> 1 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260614_151338.log

---
## Learning Loop -- 2026-06-14 15:20

- Split: None, Tasks: 9
- Correct: 4 / 9 (44.4%)
- Rules: 0 -> 2 (+2 learned)
- Stored rule hits: 1
- Time: 3s
- Log: logs/learn_20260614_152034.log

---
## Learning Loop -- 2026-06-14 15:21

- Split: None, Tasks: 9
- Correct: 4 / 9 (44.4%)
- Rules: 0 -> 2 (+2 learned)
- Stored rule hits: 1
- Time: 3s
- Log: logs/learn_20260614_152136.log

---
## Iter 3 — 2026-06-14 — branch test33

**Diagnosis**: R0 (constant_output) is cleared; the lowest unproven rung is **R1
— object-level analysis** (BACKLOG_LOOP.md). The probe showed easy000c–i all
INCORRECT: the pipeline had no object-level perception, so the cell-diff path
mis-read a single moved object as a bg↔fg color_mapping (or fell to identity).
The smallest defensible R1 step is one *value-agnostic* family proven the
intended way: "move the single foreground object to the grid's **bottom-right
corner**, preserving colour/shape." easy000c (6×6) and easy000g (varying sizes)
both belong to it, so a single size-relative rule (target = the argument
expression `(H-1, W-1)`, not a literal) covers *both* — the R1 analogue of R0,
avoiding the §2.5-3/4 accretion trap (no per-task rule).

**Change**:
- `agent/dsl_expr/{__init__,selection}.py` (new) — the seed *selection/argument*
  vocabulary R1 calls for (`objects_of`, `unique_object`, `position_of`,
  `bottom_right_of`, `color_of`, `background_of`). Placed under `agent/` (not the
  frozen `procedural_memory/DSL/`) per BACKLOG_LOOP §2.5-1. Background is the
  canonical canvas colour 0 (test32 `background_convention_fix`), not
  most-frequent.
- `agent/conditions/object_corner_target.py` (new matcher, P5 +1) — fires when
  every example moves the unique object to the bottom-right corner with
  colour/shape/grid-size preserved. Consumes a new `object_motion` signal.
- `agent/active_operators.py` — ExtractPattern surfaces `object_motion`
  (per-pair single-object analysis via the seed vocabulary); Generalize emits a
  canonical `{condition, action}` object_corner_target rule (no literal target);
  Predict reconstructs the move from **make_grid + coloring** only
  (`_render_object_corner_target`), from G0 alone — so the fast path reuses it.
  No new `_try_*`/`_apply_*` (F2-clean); F8 companions = conditions/ + memory.py.
- `agent/memory.py` + `agent/active_agent.py` — `record_cover()`: fast-path
  reuse now records the newly-handled task in the rule's `covers` (it bumped
  `times_reused` but never extended covers, so genuine generalization
  undercounted P1/P2). This is the reuse-side analogue of the slow-path covers
  merge.
- `tests/test_object_corner_target.py` (new) — selection vocab + matcher + an
  end-to-end check that easy000c and easy000g resolve to the *same* rule object.
  15/15 pass.

**Probe before**: easy_a 2/9; rules=1 (constant_output, covers a,b); P1/P2=2.0, P5=1
**Probe after** : easy_a 4/9; rules=2 (constant_output covers a,b;
object_corner_target covers c,g via reuse); P1/P2=2.0, P5=2

**Invariants**: forbidden=none; positives = P5 +1 (1→2). P1/P2 held at 2.0 (the
two new solved tasks folded into one covers=2 rule — no accretion). P6 +123
lines (active_operators grew; F8 companion = conditions/ + memory.py). Verdict
CLEAN.

**Next gap (note for future iter)**: the remaining easy_a families are other
*argument expressions* of the same object-move skeleton — constant-target
(easy000d → (1,2), easy000h → (4,4)), constant-offset/translation (easy000e
+1/-1, easy000f 0/+1), and grid-resize+corner (easy000i, 6×6→5×5 top-left).
Each is a new matcher over the same `object_motion` signal; the prize is getting
R3 `anti_unification.unify()` to lift these sibling object-move rules into one
`place_object(target=$expr)` rule with covers>1, instead of one matcher per
family.

---
## Learning Loop -- 2026-06-14 15:24

- Split: None, Tasks: 9
- Correct: 4 / 9 (44.4%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 2
- Time: 3s
- Log: logs/learn_20260614_152404.log

## Iter 3 [CLEAN] — 20260614_151338 — branch test33
- Probe: easy_a: [15:13:41] Correct:     2 / 9  (22.2%)

---
## Learning Loop -- 2026-06-14 15:24

- Split: None, Tasks: 9
- Correct: 4 / 9 (44.4%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 2
- Time: 3s
- Log: logs/learn_20260614_152429.log

---
## Learning Loop -- 2026-06-14 15:33

- Split: None, Tasks: 9
- Correct: 8 / 9 (88.9%)
- Rules: 1 -> 2 (+1 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260614_153343.log

## Iter 4 — 2026-06-14 — branch test33

**Diagnosis**: R1 is the lowest unproven rung and iter3's own next-gap note
warned that the remaining easy_a move tasks (d,e,f,h constant/translation
targets) would each become a *separate* matcher — the §2.5-3 accretion trap.
The real R1 content (§2.5-2b) is the *selection / target expression*: the
move's destination is a value-agnostic argument expression fitted from the
example comparison (the user's easy000a prose says "bottom-right *or* fixed
(5,5)"), not a literal per task. The smallest defensible step that does NOT
accrete is to generalize the corner-only matcher into ONE `object_motion`
mechanism whose target is fitted from {corner, constant, translation}.

**Change**:
- `agent/dsl_expr/motion.py` (new) — the target-position *expression* vocabulary
  (`fit_target` → corner/offset/constant, `target_position`, `obj_origin_extent`).
  Fitted from the example comparison; tried most-structural first. Placed under
  `agent/` (not the frozen DSL dir) per §2.5-1. Exported via `dsl_expr/__init__`.
- `agent/conditions/object_motion.py` (new) — replaces `object_corner_target.py`
  (git rm'd). Fires when every pair is an object/size/grid-preserving single
  move AND one target expression fits all pairs. P5 net 0 (one matcher swapped
  for a more general one).
- `agent/active_operators.py` — ExtractPattern now computes per-pair move
  geometry (src/dst/dims) and fits the target expression; Generalize emits one
  `object_motion` rule with `action.args = {}` (NO literal target, so every move
  task's rule dict is identical → save_rule merges covers); Predict renders via
  `_render_object_motion` (make_grid + coloring) using the fitted target read
  from patterns. Removed the corner-specific renderer + the object_corner_target
  branch in `_apply_rule` (object_motion declines the fast path like
  constant_output, since its target needs the example comparison). No new
  `_try_*`/`_apply_*` (F2-clean); F8 companion = conditions/ edits.
- `procedural_memory/rule_002.json` — deleted (superseded object_corner_target);
  regenerated as the unified object_motion rule.
- `tests/test_object_motion.py` (new, replaces test_object_corner_target.py) —
  fitter (corner/constant/offset), matcher, and end-to-end that c/d/e/g resolve
  to the *same* rule object. 16/16 pass (23/23 suite).

**Probe before**: easy_a 4/9; rules=2 (constant_output covers a,b;
object_corner_target covers c,g); P1/P2=2.0, P5=2
**Probe after** : easy_a 8/9; rules=2 (constant_output covers a,b; object_motion
covers c,d,e,f,g,h — ONE rule); P1/P2=4.0, P5=2

**Invariants**: forbidden=none; positives = P1 +2.0 (2.0→4.0), P2 +2.0
(2.0→4.0). P5 held (matcher swap), P6 +60 lines (F8 companion = conditions/).
The six new solved tasks folded into ONE covers=6 rule — generalization, not
accretion. Verdict CLEAN.

**Next gap (note for future iter)**: only easy000i remains in easy_a — it
*resizes* the grid (6×6 → 5×5) and moves the object to top-left, so object_motion
declines (grid_size_preserved=False). Closing it needs (a) a `top_left` target
expression and (b) an output-grid-shape expression (the "grid size changes"
concept, §2.1). That output-shape reasoning is the genuinely new capability —
distinct from the in-place move family — and likely the R1→graduation step.
Separately, R3 (anti_unification) and R5 (fast-path reuse of comparison-fitted
rules) remain unfired.

## Iter 4 [CLEAN] — 20260614_152429 — branch test33
- Probe: easy_a: [15:24:32] Correct:     4 / 9  (44.4%)

---
## Learning Loop -- 2026-06-14 15:35

- Split: None, Tasks: 9
- Correct: 8 / 9 (88.9%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260614_153540.log

---
## Learning Loop -- 2026-06-14 15:40

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260614_154037.log

## Iter 5 [CLEAN] — 20260614_153540 — branch test33
- Probe: easy_a: [15:35:43] Correct:     8 / 9  (88.9%)

---
## Learning Loop -- 2026-06-14 15:43

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260614_154322.log

---
## Learning Loop -- 2026-06-14 15:51

- Split: None, Tasks: 2
- Correct: 2 / 2 (100.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 1s
- Log: logs/learn_20260614_155158.log

---
## Learning Loop -- 2026-06-14 15:52

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260614_155216.log

---
## Iter 6 — 2026-06-14 — branch test33

**Diagnosis**: easy_a is mastered (9/9), so per PROMPT §2.2/§5 the move is to
escalate by exposing the next gap rather than polish it. The object-move path
hardcoded `unique_object` in both `_object_motion` (analysis) and
`_render_object_motion` (prediction): the instant a grid holds >1 object the path
declines — the structure cannot name *which* object the rule acts on (the §2.1
"multi-object selection" concept, BACKLOG_LOOP R1 §2.5-2b selection-lift). That is
the smallest defensible next gap: lift object selection from the degenerate
`unique` to a *fitted selector expression*, exactly as `target`/`out_shape` are
already fitted.

**Change**:
- `agent/dsl_expr/selection.py` — added `select_object` + `fit_selector` (and
  helpers) with a small input-only selector vocabulary `unique`/`largest`/
  `smallest` (argextreme by size, declines on ties). Value-agnostic, G0-only (P5).
- `agent/dsl_expr/__init__.py` — export the two new functions.
- `agent/active_operators.py` — `_object_motion` now identifies the moved object
  in each pair by matching the single output object's colour-set+size back to an
  input object, records `(objects, selected idx)`, and fits a `selector` alongside
  `target`/`out_shape`. `_render_object_motion` resolves the fitted selector via
  `select_object` instead of `unique_object`. Predict threads `selector` through.
  (Net +36 lines; companion edit to `agent/conditions/` satisfies F8.)
- `agent/conditions/object_motion.py` — gate per-pair on `single_out`+
  `selected_ok` (was `single_in`) and require a fitted `selector` (plus target,
  out_shape). Docstrings updated.
- `data/ARC_madeup/mo_select_largest.json`, `mo_select_smallest.json` — two new
  authored tasks isolating multi-object selection (largest vs smallest moves to
  the bottom-right corner, others dropped). Proves the fitter *chooses* among
  criteria, not a hardcoded "largest".
- `tests/test_object_motion.py` — updated matcher helper to the new pair keys;
  added selector unit tests + an end-to-end multi-object test asserting it
  resolves to the SAME rule object as the single-object family.

**Probe before**: easy_a 9/9; rules=2; P1/P2=4.5/4.5
**Probe after** : easy_a 9/9; madeup 2/2; rules=2; rule_002 covers 7→9 (c–i +
  both madeup); P1/P2=5.5/5.5

**Invariants**: forbidden=none, positives=P1 +1.0, P2 +1.0 (CLEAN). 39 tests pass.

**Next gap (note for future iter)**: multi-object selection now covers size
extremes only; richer selectors (by colour, by position, by uniqueness-of-a-
property) and multi-object *outputs* (where unselected objects survive) are
untouched. R3 (anti_unification, P3=0) and R5 (fast-path reuse, stored hits 0)
remain the two standing big-ticket unfired rungs.

## Iter 6 [CLEAN] — 20260614_154322 — branch test33
- Probe: easy_a: [15:43:25] Correct:     9 / 9  (100.0%)

---
## Learning Loop -- 2026-06-14 15:54

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260614_155401.log

---
## Learning Loop -- 2026-06-14 16:01

- Split: None, Tasks: 3
- Correct: 2 / 3 (66.7%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 1s
- Log: logs/learn_20260614_160152.log

---
## Learning Loop -- 2026-06-14 16:03

- Split: None, Tasks: 3
- Correct: 3 / 3 (100.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 1s
- Log: logs/learn_20260614_160259.log

---
## Learning Loop -- 2026-06-14 16:03

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260614_160300.log

---
## Iter 7 — 2026-06-14 — branch test33

**Diagnosis**: easy_a is mastered (9/9), so per PROMPT.md §2.2/§5 the iter
escalated by authoring a `data/ARC_madeup/` task exposing the next unhandled
§2.1 concept — *the output grid size is a function of an object's property*.
`fit_output_shape` only knew input-relative readings (same / input+delta /
absolute constant), so a crop whose object differs in size across pairs fits
none of them: the new `crop_to_object` task fell to `identity` (confirmed by
running the madeup probe first). This is the §2.5-2b "lift a property
expression into the argument" gap, not a missing detector.

**Change**:
- `agent/dsl_expr/motion.py` — added an `object_extent` output-shape *argument
  expression* (output size = the selected object's own bbox extent), fitted last
  so it never overrides an input-relative reading; `output_shape()` resolves it
  from the object (declines, doesn't crash, when no object is supplied).
- `agent/active_operators.py` — ExtractPattern now carries each pair's object
  extent on the `shapes` entry; the render threads the selected object into
  `output_shape()`. No new `_try_/_apply_`, no new transformation primitive.
- `agent/conditions/object_motion.py` — docstring updated to document the new
  `object_extent` reading (recognition contract stays accurate; the matcher
  already required `out_shape is not None`, so no logic change).
- `data/ARC_madeup/crop_to_object.json` — the authored task (exempt corner).
- `tests/test_object_motion.py` — 3 new tests for the fitter + resolver.

**Probe before**: easy_a 9/9; madeup 2/3 (crop_to_object INCORRECT=identity);
rule_count=2, P1=P2=5.5.
**Probe after** : easy_a 9/9 (regression guard holds); madeup 3/3, all via the
*same* `object_motion` rule (module uniformity); rule_count still 2,
rule_002.covers 9→10, P1=P2=6.0.

**Invariants**: forbidden=none (checker CLEAN, exit 0); positives=P1 +0.5,
P2 +0.5 (P3/P4/P5 flat). F8 satisfied — active_operators.py change paired with
an agent/conditions/ touch.

**Next gap (note for future iter)**: the crop solves the intended way but still
merges by *exact rule equality*, not by anti-unification — R3 remains unfired
(P3=0). `program/anti_unification.py` is still unimplemented stubs and
`program/__init__.py` imports a non-existent `anti_unify` (ImportError). The
remaining §2.1 concepts are "example pairs ≠ 2" and grid-size driven by object
*count* (vs extent); but the larger frontier is producing pair-specific
argument-expression programs for AU to actually lift.

## Iter 7 [CLEAN] — 20260614_155401 — branch test33
- Probe: easy_a: [15:54:04] Correct:     9 / 9  (100.0%)

---
## Learning Loop -- 2026-06-14 16:05

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260614_160537.log

---
## Learning Loop -- 2026-06-14 16:10

- Split: None, Tasks: 4
- Correct: 4 / 4 (100.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 2s
- Log: logs/learn_20260614_161046.log

---
## Learning Loop -- 2026-06-14 16:11

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260614_161148.log

---
## Iter 8 — 2026-06-14 — branch test33

**Diagnosis**: easy_a is mastered (9/9) and the move family resolves to one
value-agnostic `object_motion` rule, but the *selector* vocabulary in
`agent/dsl_expr/selection.py` only knew `unique`/`largest`/`smallest` — a
size-only dimension. A multi-object task whose acted-on object is named by
*position* (not size) could not be expressed, the named gap from
`test33_rung_progress` ("richer selectors by position untouched"). This is the
§2.1 multi-object-selection concept (BACKLOG_LOOP R1, §2.5-2b "lift the
selection"): grow the LHS argument vocabulary, not a detector.

**Change**:
- `agent/dsl_expr/selection.py`: added position selectors `topmost` /
  `bottommost` / `leftmost` / `rightmost` to `_SELECTOR_KINDS` via a new
  `_position_index` helper (unique bbox-edge extreme, declines on tie). Ordered
  AFTER the size extremes so a size-describable selection is still preferred
  (zero regression). No transformation primitive added (F3-clean); the fit/render
  paths in `active_operators.py` route through `select_object`/`_selection_index`
  generically, so no operator edit was needed (F8 not engaged).
- `data/ARC_madeup/mo_select_topmost.json` (F1-exempt corner): a 3-object move
  where the moved object is the smallest in pair 1 and the largest in pair 2, so
  every size selector declines and only `topmost` fits both pairs — the task
  fails without the new vocabulary and merges into rule_002 with it.
- `tests/test_object_motion.py`: +4 tests (positional select, tie-decline,
  topmost-fits-when-size-fails, size-preferred-over-position).

**Probe before**: easy_a 9/9; rules=2; rule_002 covers=10; P1/P2=6.0
**Probe after** : easy_a 9/9, madeup 4/4; rules=2 (no accretion); rule_002
covers=11 (mo_select_topmost merged); P1/P2=6.5

**Invariants**: forbidden=none; positives=P1 +0.5 (6.0→6.5), P2 +0.5 (6.0→6.5),
P3/P4/P5/P6 unchanged. 46 tests pass (was 42).

**Next gap (note for future iter)**: P3 (au_traced_frac) is still 0.0 — every
generalization so far is *within* one matcher's fitter; `anti_unification.unify()`
has never lifted across two rules with a shared arg-expr skeleton, and
`program/anti_unification.py` remains unimplemented stubs (`program/__init__.py`
imports a non-existent `anti_unify`). Remaining §2.1 concept untouched: grid size
as a function of object *count* (vs extent, done iter7).

## Iter 8 [CLEAN] — 20260614_160536 — branch test33
- Probe: easy_a: [16:05:39] Correct:     9 / 9  (100.0%)

---
## Learning Loop -- 2026-06-14 16:13

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260614_161323.log

## Iter 9 [NEUTRAL] — 20260614_161323 — branch test33
- Probe: easy_a: [16:13:26] Correct:     9 / 9  (100.0%)

---
## Learning Loop -- 2026-06-14 16:20

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260614_162050.log

> **PHASE GRADUATION** at iter 10 — easy_a → madeup.
> All of data/ARC_easy_a solved 100% for 5 consecutive iters (K=5).
> The loop now authors its own beginner tasks under data/ARC_madeup/ (§2.2)
> and must solve them via the structure, unaided, before attempting ARC training.

---
## Learning Loop -- 2026-06-14 16:25

- Split: None, Tasks: 5
- Correct: 4 / 5 (80.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 2s
- Log: logs/learn_20260614_162536.log

---
## Learning Loop -- 2026-06-14 16:26

- Split: None, Tasks: 5
- Correct: 5 / 5 (100.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 2s
- Log: logs/learn_20260614_162624.log

---
## Learning Loop -- 2026-06-14 16:26

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260614_162632.log

---
## Iter 10 — 2026-06-14 — branch test33

**Diagnosis**: Iter 10 is the first `madeup`-phase iter (easy_a graduated at K=5).
The selection vocabulary (`agent/dsl_expr/selection.py`) could name the acted-on
object by *size* (largest/smallest, iters ≤6) and *position* (topmost/…, iter8),
but had no *colour-identity* criterion. So the §2.1 multi-object-selection concept
on its third orthogonal dimension — several equal-size blobs, none at a position
extreme, the colour odd-one-out moves — was unexpressible. Confirmed by authoring
`mo_select_odd_color` and watching the structure fall back to `rule=identity`.

**Change**:
- `agent/dsl_expr/selection.py`: added the `odd_color` selector — `_odd_color_index`
  picks the object whose single colour is unique among the objects (declines on a
  tie / all-distinct / no-singleton, like the size & position selectors). Appended
  last in `_SELECTOR_KINDS` and wired into `_selection_index`, so `fit_selector`,
  `select_object` and the predict renderer all route through it generically — no
  edit to `active_operators.py` (F8 not engaged), no new transformation (F3-clean),
  no `_try_*`/matcher (F2-clean). Keys on within-grid colour *uniqueness*, never a
  literal colour value, so it stays value-agnostic / G0-only (P5).
- `data/ARC_madeup/mo_select_odd_color.json` (F1-exempt corner): 2-pair move where
  the moved object is equal-size to the others, never a position extreme, and its
  colour differs per pair (3, then 5) — so every size/position/literal-colour
  criterion declines and only `odd_color` fits both pairs; merges into rule_002.
- `tests/test_object_motion.py`: +4 tests (odd_color select, decline-on-all-distinct
  / no-singleton, fit when size+position fail, end-to-end same-rule-object).

**Probe before**: easy_a 9/9; madeup 4/5 (odd_color INCORRECT→identity); rules=2;
rule_002 covers=11; P1/P2=6.5
**Probe after** : easy_a 9/9 (regression guard holds); madeup 5/5, all via the
*same* `object_motion` rule (module uniformity); rules=2 (no accretion);
rule_002 covers=12; P1/P2=7.0. 67 tests pass (was 46).

**Invariants**: forbidden=none (checker CLEAN, exit 0); positives=P1 +0.5
(6.5→7.0), P2 +0.5 (6.5→7.0), P3/P4/P5/P6 flat. P6 lines unchanged confirms F8
not engaged.

**Next gap (note for future iter)**: P3 (au_traced_frac) is still 0.0 — the move
family unifies by *exact rule equality* in `save_rule_to_ltm` (args always `{}`),
so `anti_unification.unify()` (fully implemented, but only reachable via a
non-existent `save_rule()`) has nothing to lift; wiring it now would be inert
until a Slow-path synthesizer emits per-pair programs with *divergent* args. The
selection dimensions (size/position/colour) are now covered; remaining §2.1
concept untouched is grid size as a function of object *count* (vs extent), which
is a non-move family and likely needs its own fitted output-shape reading.

## Iter 10 [CLEAN] — 20260614_162050 — branch test33
- Probe: easy_a: [16:20:53] Correct:     9 / 9  (100.0%)

---
## Learning Loop -- 2026-06-14 16:29

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260614_162916.log

---
## Learning Loop -- 2026-06-14 16:29

- Split: None, Tasks: 5
- Correct: 5 / 5 (100.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 2s
- Log: logs/learn_20260614_162919.log

---
## Learning Loop -- 2026-06-14 16:33

- Split: None, Tasks: 6
- Correct: 5 / 6 (83.3%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 2s
- Log: logs/learn_20260614_163259.log

---
## Learning Loop -- 2026-06-14 16:33

- Split: None, Tasks: 6
- Correct: 5 / 6 (83.3%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 2s
- Log: logs/learn_20260614_163321.log

---
## Learning Loop -- 2026-06-14 16:34

- Split: None, Tasks: 6
- Correct: 6 / 6 (100.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 2s
- Log: logs/learn_20260614_163444.log

---
## Learning Loop -- 2026-06-14 16:35

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260614_163502.log

## Iter 11 [CLEAN] — 20260614_162915 — branch test33
- Probe: madeup: [16:29:21] Correct:     5 / 5  (100.0%) | easy_a: [16:29:18] Correct:     9 / 9  (100.0%)

---
## Learning Loop -- 2026-06-14 16:37

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260614_163657.log

---
## Learning Loop -- 2026-06-14 16:37

- Split: None, Tasks: 6
- Correct: 6 / 6 (100.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 2s
- Log: logs/learn_20260614_163700.log

---
## Learning Loop -- 2026-06-14 16:45

- Split: None, Tasks: 7
- Correct: 7 / 7 (100.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 2s
- Log: logs/learn_20260614_164516.log

---
## Learning Loop -- 2026-06-14 16:45

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260614_164519.log

---
## Learning Loop -- 2026-06-14 16:45

- Split: None, Tasks: 7
- Correct: 7 / 7 (100.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 2s
- Log: logs/learn_20260614_164527.log

---
## Learning Loop -- 2026-06-14 16:45

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260614_164530.log

## Iter 12 [CLEAN] — 20260614_163657 — branch test33
- Probe: madeup: [16:37:03] Correct:     6 / 6  (100.0%) | easy_a: [16:37:00] Correct:     9 / 9  (100.0%)

---
## Learning Loop -- 2026-06-14 16:47

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260614_164729.log

---
## Learning Loop -- 2026-06-14 16:47

- Split: None, Tasks: 7
- Correct: 7 / 7 (100.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 2s
- Log: logs/learn_20260614_164732.log

---
## Learning Loop -- 2026-06-14 17:00

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 1 -> 2 (+1 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260614_170048.log

---
## Learning Loop -- 2026-06-14 17:00

- Split: None, Tasks: 7
- Correct: 7 / 7 (100.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 2s
- Log: logs/learn_20260614_170052.log

---
## Learning Loop -- 2026-06-14 17:01

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260614_170101.log

---
## Learning Loop -- 2026-06-14 17:01

- Split: None, Tasks: 7
- Correct: 7 / 7 (100.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 2s
- Log: logs/learn_20260614_170104.log

## Iter 13 [CLEAN] — 20260614_164729 — branch test33
- Probe: madeup: [16:47:34] Correct:     7 / 7  (100.0%) | easy_a: [16:47:32] Correct:     9 / 9  (100.0%)

---
## Learning Loop -- 2026-06-14 17:03

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260614_170307.log

---
## Learning Loop -- 2026-06-14 17:03

- Split: None, Tasks: 7
- Correct: 7 / 7 (100.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 2s
- Log: logs/learn_20260614_170311.log

---
## Learning Loop -- 2026-06-14 17:10

- Split: None, Tasks: 8
- Correct: 7 / 8 (87.5%)
- Rules: 2 -> 3 (+1 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260614_171042.log

---
## Learning Loop -- 2026-06-14 17:11

- Split: None, Tasks: 8
- Correct: 8 / 8 (100.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260614_171138.log

---
## Learning Loop -- 2026-06-14 17:11

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260614_171148.log

## Iter 14 [CLEAN] — 20260614_170307 — branch test33
- Probe: madeup: [17:03:13] Correct:     7 / 7  (100.0%) | easy_a: [17:03:10] Correct:     9 / 9  (100.0%)

---
## Learning Loop -- 2026-06-14 17:14

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260614_171456.log

---
## Learning Loop -- 2026-06-14 17:15

- Split: None, Tasks: 8
- Correct: 8 / 8 (100.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260614_171500.log

---
## Learning Loop -- 2026-06-14 17:29

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260614_172955.log

---
## Learning Loop -- 2026-06-14 17:30

- Split: None, Tasks: 10
- Correct: 10 / 10 (100.0%)
- Rules: 2 -> 3 (+1 learned)
- Stored rule hits: 0
- Time: 4s
- Log: logs/learn_20260614_172958.log

## Iter 15 — 2026-06-14 — branch test33

**Diagnosis**: The object_motion family is saturated across selection (size/position/colour/shape), output-shape (extent/count) and scene (drop/preserve) dimensions — every §2.1 madeup concept now merges into rule_002, so adding a 5th arg-expr would be near-duplicate spinning. The genuinely-missing capability is a *non-positional* transformation: the structure can MOVE an object but has never CHANGED a colour the intended (value-agnostic) way — the only recolour handling is the legacy value-keyed `_try_color_mapping`, which bakes a literal input→output colour map and cannot generalise to a held-out colour. Picked this gap because it is a real new transformation family AND it is the first chance to fire `unify()` on genuinely divergent args (the R3 prize, inert all branch), since two recolour tasks with swapped (selector,source) share a skeleton but diverge.

**Change**:
- `agent/dsl_expr/recolor.py` (new): `fit_color_source` / `color_source` — the new colour as an argument expression `color_of(select_object(inputs, source))`, fitted from the example comparison, never a literal. Reuses the existing selector vocabulary.
- `agent/conditions/object_recolor.py` (new matcher, P5 +1): fires on an in-place recolour with both a target *selector* and a colour *source* fitted.
- `agent/active_operators.py`: ExtractPattern surfaces an `object_recolor` signal (`_object_recolor` + `_identify_recolor`: one object, same cells, single new colour, others byte-identical, grid preserved); GeneralizeOperator emits a `{condition:object_recolor, action:recolor_object, args:{selector,source}}` rule (checked before the legacy `_try_color_mapping`); PredictOperator renders via `_render_object_recolor` (make_grid + coloring only), re-deriving both selectors from this task's own patterns so the recorded args never affect solving.
- `agent/dsl_expr/__init__.py`: export the two new expressions.
- `data/ARC_madeup/recolor_to_largest.json`, `recolor_to_smallest.json` (new, F1-exempt): mirror tasks (selector/source swapped) so their args diverge and force an AU lift.
- `tests/test_object_recolor.py` (new, +14 tests incl. the AU-lift end-to-end).

**Probe before**: easy_a 9/9, madeup 8/8; rules 2; P1/P2=8.5; P3=0.5; P5=2.
**Probe after** : easy_a 9/9, madeup 10/10 (both recolour tasks solved via `object_recolor`); rules 3; rule_003 = AU-lifted abstract recolour (args `?v1`/`?v2`, covers=2, anti_unification_trace set).

**Invariants**: forbidden=none (F8 satisfied: active_operators paired with new agent/conditions/ matcher + memory.py save path; F2/F3 clean — recolour is make_grid+coloring, matcher not `_try_*`). positives=P3 0.5→0.667 (+0.167), P5 2→3 (+1). P1/P2 8.5→6.33 (down) — the honest, expected cost of a brand-new family (covers=2) against a mean dominated by rule_002's covers=15; recovers as the recolour family generalises, exactly as object_motion did at covers=2 in iter3. 100 tests pass (+14).

**Next gap (note for future iter)**: P1/P2 mechanically punish any new family while one rule (covers≈15) dominates the mean — the instrumentation biases toward feeding rule_002 over building new capability. The real frontier now: a *cross-family* AU lift (object_motion ↔ object_recolor share the `select_object` selection skeleton but differ in action.dsl, so unify() can't bridge them without object-level lifting), and R5 fast-path reuse (both families still decline the input-only fast path because args are fitted from the example comparison).

## Iter 15 [CLEAN] — 20260614_171456 — branch test33
- Probe: madeup: [17:15:03] Correct:     8 / 8  (100.0%) | easy_a: [17:14:59] Correct:     9 / 9  (100.0%)

---
## Learning Loop -- 2026-06-14 17:32

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260614_173208.log

---
## Learning Loop -- 2026-06-14 17:32

- Split: None, Tasks: 10
- Correct: 10 / 10 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260614_173212.log

---
## Learning Loop -- 2026-06-14 17:35

- Split: None, Tasks: 11
- Correct: 10 / 11 (90.9%)
- Rules: 3 -> 4 (+1 learned)
- Stored rule hits: 0
- Time: 4s
- Log: logs/learn_20260614_173508.log

---
## Learning Loop -- 2026-06-14 17:35

- Split: None, Tasks: 11
- Correct: 10 / 11 (90.9%)
- Rules: 4 -> 4 (+0 learned)
- Stored rule hits: 1
- Time: 3s
- Log: logs/learn_20260614_173541.log

---
## Learning Loop -- 2026-06-14 17:36

- Split: None, Tasks: 11
- Correct: 11 / 11 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260614_173558.log

---
## Learning Loop -- 2026-06-14 17:36

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260614_173606.log

---
## Learning Loop -- 2026-06-14 17:36

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260614_173613.log

## Iter 16 — 2026-06-14 — branch test33

**Diagnosis**: The object_recolor family (new iter15) could only name the new colour as `color_of(select_object(inputs, source))` — another object's colour. A recolour whose target colour appears on NO input object (and varies in the object's *own* colour across pairs) fits neither that source-selector nor the legacy value-keyed color map, so the structure declined and a spurious overfit recolor_sequential rule leaked. This is the recolour analog of object_motion's corner-vs-constant target split: the missing reading is a *constant* colour fitted from the example agreement (exactly how constant_output/R0 fits its common grid).

**Change**:
- `agent/dsl_expr/recolor.py`: `fit_color_source` gains a `constant` fallback — tried AFTER every source-selector (most-structural-first), returns `{kind:constant,color:c}` only when the new colour is one value agreed across all pairs; `color_source` resolves a constant descriptor to its colour directly. Value-agnostic in the constant_output sense: the constant is re-fitted from each task's own examples at solve time, supplied by training outputs not test G1 (P5-clean).
- `data/ARC_madeup/recolor_to_constant.json` (new, F1-exempt): largest object recoloured to fixed colour 2 (absent from every input, object's own colour varies 3/5/7) — confirmed FAILED before (declined -> spurious recolor_sequential), now solved via object_recolor.
- `tests/test_object_recolor.py`: replaced the now-obsolete "declines when no object has colour" test with constant-fallback / constant-disagreement-declines / selector-preferred-over-constant / constant-resolution coverage (+2 net).
- Deleted the leaked `procedural_memory/rule_004.json` (overfit recolor_sequential from the pre-fix failed run).

**Probe before**: easy_a 9/9, madeup 10/11 (recolor_to_constant INCORRECT); rules 3; P1/P2=6.33; P3=0.667; P5=3.
**Probe after** : easy_a 9/9, madeup 11/11 (constant task via object_recolor); rules 3; rule_003 covers 2->3 (absorbed into the abstract `?v1/?v2` rule, trace intact).

**Invariants**: forbidden=none (no active_operators.py edit -> F8 not engaged; render/generalize route through color_source generically; F2/F3 clean). positives=P1 6.33->6.67 (+0.33), P2 6.33->6.67 (+0.33); P3/P5 held. 102 tests pass (+2).

**Next gap (note for future iter)**: recolor source now = {another-object's-colour} U {constant}; still no *relational* colour reading (e.g. new colour = colour absent from a fixed palette, or swap two objects' colours). Bigger standing frontiers unchanged: cross-family AU lift (object_motion <-> object_recolor share select_object but differ in action.dsl — needs object-level lifting) and R5 fast-path reuse (still 0; both families fit args from the example comparison the input-only fast path can't supply).

## Iter 16 [CLEAN] — 20260614_173208 — branch test33
- Probe: madeup: [17:32:15] Correct:     10 / 10  (100.0%) | easy_a: [17:32:11] Correct:     9 / 9  (100.0%)

---
## Learning Loop -- 2026-06-14 17:38

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260614_173810.log

---
## Learning Loop -- 2026-06-14 17:38

- Split: None, Tasks: 11
- Correct: 11 / 11 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260614_173813.log

> **PHASE GRADUATION** at iter 17 — madeup → training.
> data/ARC_madeup/ (11 tasks) + easy_a solved 100% for 5 consecutive iters (K=5).
> The structure now expresses task-specific rules for beginner concepts unaided.
> Probe now samples data/ARC_AGI/training/ (ARC-AGI-2). easy_a + madeup kept as regression guard.

---
## Learning Loop -- 2026-06-14 17:39

- Split: training, Tasks: 12
- Correct: 0 / 12 (0.0%)
- Rules: 3 -> 6 (+3 learned)
- Stored rule hits: 0
- Time: 26s
- Log: logs/learn_20260614_173846.log

---
## Learning Loop -- 2026-06-14 17:43

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260614_174304.log

---
## Learning Loop -- 2026-06-14 17:43

- Split: None, Tasks: 11
- Correct: 11 / 11 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 4s
- Log: logs/learn_20260614_174307.log

---
## Learning Loop -- 2026-06-14 17:43

- Split: training, Tasks: 12
- Correct: 0 / 12 (0.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 25s
- Log: logs/learn_20260614_174325.log

## Iter 17 — 2026-06-14 — branch test33

**Diagnosis**: First training-phase iter (graduated easy_a→madeup→training this
iter). A self-run training probe (`--split training --limit 12 --shuffle --seed
42`) scored 0/12 but **minted 3 new rules** (3→6) — and all three were the legacy
format (top-level `rule`, **no `condition` key**), overfit single-`covers` literal
colour maps that did not even generalize to test. Root cause: the closed `_try_*`
family still contained two superseded color-transform detectors
(`_try_recolor_sequential`, `_try_color_mapping`) that fire whenever the
principled families decline, baking literals into conditionless per-task rules —
arbor.md 진단 #4/#5, the 168-rule accretion failure mode in miniature.

**Change**:
- `agent/active_operators.py`: removed the two legacy color-transform strategies
  and their appliers — `_try_recolor_sequential`, `_check_sort_key`,
  `_try_color_mapping`, `_apply_recolor_sequential`, `_apply_color_mapping`, and
  the now-orphaned `_group_positions` helper — plus their two call sites in
  `GeneralizeOperator.effect` and two dispatch arms in `_apply_rule`. These are
  superseded by the value-agnostic `object_recolor` family (iters 15/16).
  CLAUDE.md §5.1 ("Removal of methods superseded by anti-unification") + INVARIANTS
  P6. Net −162 lines; pure deletion (F8 exception).
- Deleted the 3 spurious conditionless rules the diagnostic probe created
  (`rule_004/005/006.json`, untracked — never committed).

**Probe before**: training 0/12, but probe **added 3 conditionless overfit rules**
(3→6); easy_a 9/9, madeup 11/11.
**Probe after** : training 0/12 with **0 rules discovered** (3→3, no pollution);
easy_a 9/9 (no new rules), madeup 11/11 (no new rules). 102 tests pass.

**Invariants**: forbidden=none, positives=P6 Δ+162 lines removed (1271→1109);
P1/P2/P3/P4/P5 held (6.667 / 6.667 / 0.667 / 932 / 3). Verdict CLEAN.

**Next gap (note for future iter)**: training is 0/N — no principled family fires
on real ARC-AGI-2 tasks. With the legacy wrong-way detectors gone, the path is
clear to take on one failing training task for a *nameable* reason and add a
*general* mechanism (new compare capability / condition matcher / fitted arg-expr)
rather than a literal detector. R5 fast-path reuse still unfired.

## Iter 17 [CLEAN] — 20260614_173809 — branch test33
- Probe: madeup: [17:38:16] Correct:     11 / 11  (100.0%) | easy_a: [17:38:12] Correct:     9 / 9  (100.0%)
