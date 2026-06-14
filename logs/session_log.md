# SOAR-ARC Session Log

---
## Iter 28 — 2026-06-14 — branch test33

**Diagnosis**: iter27's next gap named the synthesizer grammar as the training
frontier — its 3 fixed schemas (identity / constant / object-reconstruction) emit
nothing on real ARC. The *smallest* defensible slice of "broaden the grammar" is one
new general schema: a **global colour substitution** (shape-preserved cell-wise
recolour) — the general case no single-colour `object_recolor` family fits, since
distinct colours map to distinct colours. But adding any 2nd synthesizer schema
first exposes a latent merge bug: all synthesizer rules collide on the coarse
`(synthesized_program, run_program)` skeleton, so a colour-map rule would be wrongly
folded into the already-generalised resize rule_004's covers. Both halves are this
iter's gap (the schema is inert/corrupting without the merge fix).

**Change**:
- `program/synthesis.py` — added the `cells_with_color` expression op (reads the
  *fixed input* grid, so selections never cascade off the running canvas and the
  program transfers to the test input, P5) + Schema 4 `_fit_color_map`: fits one
  colour map `c->f(c)` consistent across **all** pairs (the COMM reason — P3/P4) and
  emits one `coloring(cells_with_color(const c), const f(c))` step per *changed*
  colour. Declines (returns None) on shape change or inconsistent map. Module
  docstring updated.
- `agent/memory.py` — added `_rule_program` + `_program_skeleton` (collapses every
  `("const", VALUE)` to a wildcard) and a guard in `save_rule`'s merge loop: two
  synthesizer rules fold only when their *program* structure matches, so resize and
  colour-map each keep their own `covers>1` family instead of cross-contaminating.
- `data/ARC_madeup/color_remap_a.json`, `color_remap_b.json` (NEW, F1-exempt) — two
  colour-substitution tasks with the same 2-step skeleton but **divergent maps**
  ({2:3,4:5} vs {1:6,8:7}); confirmed INCORRECT (rule=identity) before the change.
  They ground program-level AU on the new schema: `unify()` lifts the two synthesized
  programs into ONE rule (rule_005, covers=2, trace, 4 `?v` holes).
- `tests/test_synthesis_colormap.py` (NEW, +9) — `cells_with_color` selection; the
  schema fits/declines (inconsistent map, shape change, identity); program transfers
  to the held-out test input; `_program_skeleton` separates resize from colour-map
  yet unifies colour-maps differing only in constants; two colour-map tasks fold into
  one covers=2 trace rule **without** contaminating a sibling resize rule.

**Probe before**: training 0/3 (microscope); easy_a 9/9, madeup 18/18; rules 4,
P1=P2=6.75, P3=0.75, P5=4, P6=1314; 159 tests.
**Probe after** : easy_a 9/9 (regression guard, rules 5->5 no re-mint), **madeup
20/20** (color_remap_a/b CORRECT via the colour-map schema -> folded into NEW
rule_005 covers=2 + anti_unification_trace, abstract program
`[coloring(cells_with_color(const ?v1), const ?v2), coloring(..(?v3), ?v4)]`); rules
4->5; P1=P2=5.8, P3=0.8; 168 tests (+9). A seed-7/limit-60 training scan also solved
**a real ARC-AGI-2 task (b1948b0a)** via the same general schema (generality evidence
beyond the authored tasks) — its lone covers=1 no-trace rule was *not* persisted
(would be §2.5-3 accretion dragging P3; it re-mints and lifts when a sibling real
colour-map task appears). No over-firing: 1/60 on real data, that 1 a genuine solve.

**Invariants**: forbidden=none (check_invariants CLEAN, exit 0); positives=**P3 +0.05
(0.75->0.8)** with rule_005 carrying a trace at birth (covers=2, not 1 — §2.5-4
litmus: the new rule is itself a generalization, not accretion). **P1/P2 -0.95** is
the documented honest cost of a genuinely-new capability landing as a new rule whose
covers (2) is below the running mean (the iter26 instrumentation pattern, smaller
dip). P4/P5/P6 flat — **no `active_operators.py` edit (F8 not engaged)**, all logic
in `program/` + `agent/memory.py`. F3 clean (no DSL primitive — a new *expression*
op + search schema, both compositions of the two frozen primitives). F2 clean (no
`_try_*`). rule_005 has condition+action.

**Next gap (note for future iter)**: the colour-map schema is single-step cell-wise;
the synthesizer still emits no *multi-step* / object-relational program, so real ARC
beyond pure recolour/resize/constant stays 0. The named frontier is unchanged —
object-level synthesis: emit selection as `cells_of(select(objects, predicate))` so
the search composes a *sequence* of object transforms (the only path that moves
structurally-transforming real ARC). A nearer step: a fitted *per-object* recolour
schema (recolour each object by a property-keyed map), which would let two such tasks
lift and start a 2nd covers>1 synthesizer family.

---
## Iter 27 — 2026-06-14 — branch test33

**Diagnosis**: iter26 wired the Slow-path synthesizer live but paid an honest
P1/P2/P3 cost — its rule_004 was covers=1 with **no anti_unification_trace**, and
iter26's named next gap was *program-level AU*: two synthesizer tasks sharing a
program skeleton but diverging in a leaf should lift via `unify()`, except
`_anti_unify_fields` lifted the whole `program` field to one opaque `?v`
(degenerate, uninstantiable) because it only handled the **leaf case** (`==` or
lift-whole). The smallest defensible step: make `unify()` *descend into nested
sequence terms* so the shared skeleton is preserved and only divergent leaves lift
— the genuine R3-via-synthesizer prize, recovering the iter26 cost the principled
way (covers↑ + trace, no accretion).

**Change**:
- `program/anti_unification.py` — added `_anti_unify_value` (recursive descent into
  equal-length sequences; dicts / ragged seqs / scalars still lift whole) + `_fresh_var`
  + `_normalize` (tuple↔list round-trip insensitivity, since synthesized programs are
  tuples in memory but lists once JSON-stored); rewrote `_anti_unify_fields` to route
  every key's values through `_anti_unify_value`. Descent is **sequence-only** — the
  `object_motion` `target` *dict* still lifts whole, so rule_002/rule_003 abstractions
  are untouched. Updated the module docstring.
- `program/synthesis.py` — added `contains_variable()` + a guard in `run_program` that
  raises `_Unevaluable` on a program still carrying `?vN` holes. An abstract synthesizer
  rule is re-synthesized per task on the Slow path, so the fast path / matcher must
  *decline* (not crash) on the lifted program — both already catch `_Unevaluable`.
- `data/ARC_madeup/resize_to_5x5.json` (NEW, F1-exempt) — a second no-mover resize
  (3x3 -> fixed 5x5) whose synthesized program shares the make_grid+paint_objects
  skeleton with resize_keep_objects (-> 6x6) but **diverges only in the fitted dim**
  (5 vs 6), grounding the structural lift. All families decline (same path as
  resize_keep_objects); only the synthesizer solves it.
- `tests/test_anti_unification.py` (+4) — nested-sequence leaf lift keeps skeleton +
  path-suffixed substitutions; tuple-vs-list identical programs -> no lift/no trace;
  dict-valued `target` still lifts whole; unequal-length seqs lift whole.
- `tests/test_synthesis_wired.py` (+2) — two divergent-dim resize tasks fold into ONE
  rule (covers=2, trace, structured `?v`-holed program); abstract program declines
  `run_program`/`_render_synthesized_program` rather than crashing.
- `docs/ANTI_UNIFICATION.md` — recursion-into-sequence-terms now in scope (was "out of
  scope for this iter").

**Probe before**: training 0/3 (microscope); easy_a 9/9, madeup 17/17; rules 4,
rule_004 covers=1 no-trace; P1=P2=6.5, P3=0.5, P5=4, P6=1314; 153 tests.
**Probe after** : training 0/3 (unchanged - synthesizer still returns None on real
ARC, no pollution); easy_a 9/9, **madeup 18/18** (resize_to_5x5 CORRECT via
synthesized_program -> folds into rule_004); rules still 4 (no accretion); **rule_004
covers 1->2 (resize_keep_objects + resize_to_5x5), anti_unification_trace set,
structured abstract program** `[make_grid([const,?v],[const,?v],[bg]),paint_objects([all_objects])]`;
P1=P2=6.75, P3=0.75; 159 tests (+6). Verified on a fresh run that both resize tasks
re-solve via slow-path re-synthesis (abstract rule declines the fast path by design).

**Invariants**: forbidden=none (check_invariants CLEAN, exit 0); positives=**P1 +0.25
(6.5->6.75), P2 +0.25, P3 +0.25 (0.5->0.75) - all three rising together** = the §2.5-4
litmus for genuine generalization (principled recovery of iter26's new-capability
cost: covers + trace, not a new rule file). P4/P5/P6 flat. **No active_operators.py
edit (F8 not engaged)** - all logic in program/. F3 clean (no DSL primitive added). F4
clean (rule_004 keeps condition+action).

**Next gap (note for future iter)**: the synthesizer grammar is still 3 fixed schemas
(identity / constant-common / object-reconstruction-onto-fitted-canvas) -> 0/40 on real
ARC-AGI-2. Program-level AU now works structurally, but it can only lift *what the
search produces*, and the search produces nothing for multi-STEP / object-relational
real tasks. The training frontier (per [[synthesizer_frontier]] iter-29 finding) is
**object-level synthesis**: emit selection as `cells_of(select(objects,predicate))`
rather than flat cells, so the synthesizer composes a *sequence* of transforms - a
large step, but the only one that moves real ARC.

---
## Iter 26 — 2026-06-14 — branch test33

**Diagnosis**: The Slow-path synthesizer substrate (`program/synthesis.py`, built
iter25) was OFF the live path — dead scaffolding (a 2nd NEUTRAL substrate iter would
be spinning). The named frontier (iters 21/23/24/25 all flagged it) is wiring modules
F/G onto the live `GeneralizeOperator` path so a transformation **no recognition
family expresses** is solved by general SEARCH over the two frozen primitives, the
§6.2 "discovered layer is data, not code" way — not by accreting a 21st fitted
arg-expr onto rule_002. Smallest defensible slice: wire `synthesize_task` as the
no-family-fired fallback and prove it on one authored task that exercises exactly the
capability no family has (a multi-object grid resize with **no single mover**).

**Change**:
- `data/ARC_madeup/resize_keep_objects.json` (NEW, F1-exempt) — 4×4 → fixed 6×6,
  every object kept in place, padded with background. Confirmed it **failed before**
  (INCORRECT, `rule=identity`): object_motion declines (zero moved), constant_output
  declines (outputs differ), object_recolor declines (no recolour). Only the
  synthesizer's schema-3 (`make_grid(fitted dims, bg)` ∘ `paint_objects`) solves it;
  verified `synthesize_task` reproduces all train pairs **and** the held-out test
  before wiring (empirical-first, per [[synthesizer_frontier]]).
- `agent/conditions/synthesized_program.py` (NEW) + auto-registered — the general
  synthesizer recognition slot (P5 3→4). Recognises a task by *outcome*: a
  value-agnostic program reproduces every example pair. ONE general matcher, not a
  per-shape detector (§2.5-3 anti-accretion).
- `agent/active_operators.py` — (a) ExtractPattern surfaces `patterns["synthesis_pairs"]`
  (raw train grids); (b) GeneralizeOperator gains `_synthesize_program` + a fallback
  branch (after the three families decline, before identity) that calls
  `synthesize_task`, gates the result through the registered matcher (recognition
  stays in the registry, mirroring `_matches_constant_output`), and emits a canonical
  `{condition: synthesized_program, action: {dsl: run_program, args: {program}}}` rule
  — the searched program carried as *data*; (c) PredictOperator +`_render_synthesized_program`
  runs the stored program on the test input (slow path) and via `_apply_rule` on the
  fast path (value-agnostic → reuses straight from a single input grid, R5-ready).
- `tests/test_synthesis_wired.py` (NEW, +8) — matcher fires/declines (wrong/empty/no
  pairs); resize task solved end-to-end + program transfers to test; **no hijack**
  (constant_output / object_motion still own their tasks); two same-program tasks
  fold into ONE rule (covers=2) via save_rule.

**Probe before**: training 0/3 (microscope); easy_a 9/9, madeup 16/16; rules 3,
rule_002 covers 20; P1=P2=8.333, P3=0.667, P5=3; 145 tests.
**Probe after** : training 0/3 (unchanged — synthesize_task returns None on real
ARC: 0/40 seed-7 scan, **0 new rules**, no pollution / no broken merge); easy_a 9/9
(no regression, 0 new rules — synthesizer does not hijack family tasks); **madeup
17/17** (resize_keep_objects CORRECT via `synthesized_program` → NEW rule_004,
covers=['resize_keep_objects']); rules 4; P1=P2=6.5, P3=0.5, P5=4; 153 tests (+8).

**Invariants**: forbidden=none (check_invariants CLEAN, exit 0); positives=**P5 +1
(3→4)** — the general modules-F/G recognition slot now exists on the live path. P1/P2
dip 8.333→6.5 and P3 0.667→0.5 are the documented **honest cost of a genuinely-new
capability** (new rule covers=1, denominator 3→4, no trace yet — exactly the iter15
object_recolor instrumentation trap, not accretion: this is the *general* mechanism,
not a 21st detector). P6 +105 lines on active_operators.py (F8 satisfied — co-touched
agent/conditions/ with the new matcher). F4 clean (rule_004 has condition+action).

**Next gap (note for future iter)**: the synthesizer is live but its rule carries
**no `anti_unification_trace`** — program-level AU is the real R3-via-synthesizer
prize: two synthesizer tasks sharing a skeleton but with *divergent programs* should
lift via `unify()` (currently `_absorb_or_lift` would lift the whole `program` field
to `?v`, an uninstantiable rule — unify needs to descend into the program's step
args). Closing that would recover the P1/P2/P3 cost the principled way (covers>1 +
trace). Also: the synthesizer's grammar is still 3 fixed schemas (identity / constant
/ object-reconstruction) — broadening it toward genuine multi-STEP composition is
what real ARC-AGI-2 needs (still 0/40).

---
## Iter 20 — 2026-06-14 — branch test33

**Diagnosis**: Training phase; probe 0/3 (real ARC-AGI-2, no smallest gap there —
hacking one is the F2 trap). Every §2.1 beginner concept is already exercised, and
an 8th selector-fold would read as §2.2 spinning. The *non-duplicate* smallest gap
is a documented one: `arbor-open-questions.md` Q-C3 ("Ranking util DSL 의 적정
set", module D) is **answered and "등록 대기"** — the 7-util set `(argmax, argmin,
nth_by_desc, sort_by, count, filter, unique)` was never registered. Every existing
selector names the *extreme* (rank-1 size) or the *odd-one-out* (unique count);
none can name a **ranked** member (the k-th by a property) — exactly the answered
ranking capability. (The *separate*, still-open item — `arbor-modules §2`
"2차 relation 미지원 / 가장 긴 derived 속성 표현", ranking over comparison
*receipts* — I deliberately did NOT touch; these utils rank a 1st-order per-object
property, surfaced in the ranking.py header per BACKLOG §5.)

**Change**:
- `agent/dsl_expr/ranking.py` (NEW) — registers the answered Q-C3 util set under
  `agent/` (NOT the frozen transformation DSL dir, §2.5-1/F3): `sort_by`, `count`,
  `filter_by`, `unique`, `nth_by_desc` (+ ascending mirror `nth_by_asc`), `argmax`,
  `argmin`. Decline-on-tie shared with selection.py: a ranked pick resolves only
  when the n-th **distinct** key value names exactly one item (value-agnostic, P5).
- `agent/dsl_expr/selection.py` — added `second_largest` / `second_smallest`
  selector kinds (size rank 2 from top/bottom) via `_nth_size_index` →
  `ranking.nth_by_*`; appended LAST in `_SELECTOR_KINDS` (zero regression — every
  extreme/position/odd-one-out selector still wins first). Refactored
  `_argextreme_index` to delegate to `ranking.argmax`/`argmin` (the rank-1 case) so
  every size selector shares one tie-aware backing vocabulary; added `_index_of`
  (identity-based, never `==`). Docstrings updated.
- `agent/dsl_expr/__init__.py` — export the `ranking` module.
- `data/ARC_madeup/mo_second_largest.json` (NEW, F1-exempt) — three strictly
  size-ordered objects; the **middle** (2nd-largest) moves to the bottom-right
  corner, others dropped. Authored to *fail* before the fix: `largest`→biggest,
  `smallest`→smallest, all colours+shapes distinct (odd_color/odd_shape decline),
  the middle at no position extreme → only a ranked selector names it. Confirmed
  pre-fix it would decline to identity (no `second_*` kind existed).
- `tests/test_ranking.py` (NEW, +9) — the util set: unique extreme, decline-on-tie,
  distinct-value ranks, ascending mirror, absent/tied-rank decline, pure sort,
  count/filter/unique.
- `tests/test_object_motion.py` (+4) — `second_largest`/`second_smallest` pick +
  decline-on-tie; `fit_selector` resolves to `second_largest` on the madeup train
  pairs when every extreme/odd-one-out criterion fails; end-to-end solve via the
  **same** rule object as easy000c (no accretion). NO `agent/active_operators.py`
  edit (F8 N/A): `fit_selector`/`select_object` dispatch the new kinds unchanged.

**Probe before**: training 0/3 (microscope); easy_a 9/9, madeup 12/12; rules 3,
rule_002 covers 16, P1=P2=7.0, P3=0.667.
**Probe after** : easy_a 9/9, madeup **13/13** (mo_second_largest CORRECT via
object_motion, folded into rule_002 covers 16→17, **no new rule**; solved via the
R5 stored fast path — the ranked selector re-fits on the abstract rule). 124 tests
pass (112+12).

**Invariants**: forbidden=none (check_invariants CLEAN, exit 0); positives=**P1
+0.333 (7.0→7.333), P2 +0.333 (7.0→7.333)** via covers union (rule count flat —
§2.5-4 litmus satisfied); P3/P4/P5 ±0; P6 ±0 (no active_operators edit). The new
ranking vocabulary grows the LHS under `agent/`, where §2.5-1 requires it.

**Next gap (note for future iter)**: ranked selection now exists (rank-2 by size),
but the genuinely-unproven **R4** rung — 2nd-order ranking over *comparison
receipts* (`ARCKG/comparison.py` edge-of-edge), the "가장 긴 derived 속성" still
recorded as an *open question* (`arbor-modules §2`, surfaced this iter) — remains
untouched; closing it needs a design decision on how derived/ranking properties are
represented, so it is BACKLOG §5 open-question-blocked, not a free smallest step.
Otherwise the standing frontiers are unchanged: cross-family AU (rule_001 ↔
rule_002 share no skeleton; needs a Slow-path synthesizer) and R5's done-when (a
stored rule reused on a *structurally different* task, still untested).

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

---
## Learning Loop -- 2026-06-14 17:45

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260614_174523.log

---
## Learning Loop -- 2026-06-14 17:45

- Split: None, Tasks: 11
- Correct: 11 / 11 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 4s
- Log: logs/learn_20260614_174526.log

---
## Learning Loop -- 2026-06-14 17:45

- Split: training, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 5s
- Log: logs/learn_20260614_174530.log

---
## Learning Loop -- 2026-06-14 17:48

- Split: None, Tasks: 2
- Correct: 1 / 2 (50.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 1s
- Log: logs/learn_20260614_174825.log

---
## Learning Loop -- 2026-06-14 17:51

- Split: None, Tasks: 12
- Correct: 11 / 12 (91.7%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 4s
- Log: logs/learn_20260614_175109.log

---
## Learning Loop -- 2026-06-14 17:52

- Split: None, Tasks: 12
- Correct: 11 / 12 (91.7%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 4s
- Log: logs/learn_20260614_175214.log

---
## Learning Loop -- 2026-06-14 17:52

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260614_175218.log

---
## Learning Loop -- 2026-06-14 17:52

- Split: None, Tasks: 12
- Correct: 12 / 12 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 4s
- Log: logs/learn_20260614_175250.log

---
## Learning Loop -- 2026-06-14 17:52

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260614_175254.log

---
## Learning Loop -- 2026-06-14 17:54

- Split: None, Tasks: 12
- Correct: 12 / 12 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 4s
- Log: logs/learn_20260614_175426.log

---
## Learning Loop -- 2026-06-14 17:54

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260614_175431.log

## Iter 18 — 2026-06-14 — branch test33

**Diagnosis**: Training phase. The probe's training tasks all fail (expected — real
ARC-AGI-2 is hard), so I escalated per §2.2 to the one §2.1 beginner concept no
madeup task yet exercises: **example pairs ≠ 2**. A scratch probe showed the
asymmetry cleanly — a *3*-pair single-object move solves (object_motion), but the
*1*-pair variant declines to identity. Root cause: the three condition matchers
hard-wire `min_evidence = 2`, so a single fully-determined pair is refused even
when a consistent selector/target/shape/scene all fit — the structure was wired to
expect exactly two pairs.

**Change**:
- `data/ARC_madeup/mo_one_pair.json` (new, F1-exempt): a single-train-pair
  single-object corner move — the smallest task isolating the one-pair concept,
  authored to *fail* under the old floor.
- `agent/conditions/object_motion.py`, `object_recolor.py`: lowered the
  `min_evidence` default 2→1. A single pair from which the fit functions still
  produce *non-None* selector/target/out_shape/scene (motion) or selector/source
  (recolor) is admissible — the minimal-assumption read of one example. Floor stays
  ≥1 so zero-pair declines.
- `agent/active_operators.py`: the two matching wrapper call sites pass
  `{"min_evidence": 1}` (was 2). `constant_output`'s call site **kept at 2**.
- `agent/conditions/constant_output.py`: **deliberately left at floor 2** — it is
  the degenerate hypothesis that trivially fits any single pair (one output is
  vacuously "all-equal") and would shadow a richer transformation on a one-pair
  task. Confirmed empirically: with floor 1 it mis-fired on mo_one_pair. The
  one-pair asymmetry (transformation matchers vs constancy) is documented in the
  matcher docstrings + session log here as the design rationale.
- `tests/test_object_motion.py`, `tests/test_object_recolor.py`: replaced the
  `needs_min_evidence` tests (which asserted the old floor=2) with three each:
  single fully-determined pair now *accepted*, zero pairs declined, explicit
  higher floor still honoured when a caller requests it.

**Probe before**: training 0/3 (microscope); easy_a 9/9, madeup 11/11; mo_one_pair
(new) INCORRECT via identity. Rules 3, covers mean 6.667.
**Probe after** : easy_a 9/9, madeup **12/12** (mo_one_pair CORRECT via
object_motion, folded into rule_002 covers 15→16, **no new rule**). 106 tests pass.

**Invariants**: forbidden=none; positives=P1 +0.333 (6.667→7.0), P2 +0.333
(6.667→7.0); P3/P4/P5/P6 held. Verdict CLEAN.

**Next gap (note for future iter)**: every §2.1 beginner concept is now exercised
by a madeup task and solved the intended way. The standing unfired mechanism is
**R5 fast-path reuse** — `active_agent._apply_rule` declines object_motion/recolor
(it cannot supply the example comparison the abstract `?v` rule needs to fill its
variables), so stored rules are always re-derived on the slow path (Reused: 0).
Closing it needs a reuse path that re-fits the rule's variables from a *new* task's
own examples. R4 (2nd-order edge / ranking) also remains unproven.

## Iter 18 [CLEAN] — 20260614_174523 — branch test33
- Probe: [17:45:35] Correct:     0 / 3  (0.0%)

---
## Learning Loop -- 2026-06-14 17:56

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260614_175604.log

---
## Learning Loop -- 2026-06-14 17:56

- Split: None, Tasks: 12
- Correct: 12 / 12 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 4s
- Log: logs/learn_20260614_175608.log

---
## Learning Loop -- 2026-06-14 17:56

- Split: training, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 5s
- Log: logs/learn_20260614_175612.log

---
## Learning Loop -- 2026-06-14 18:00

- Split: training, Tasks: 40
- Correct: 0 / 40 (0.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 115s
- Log: logs/learn_20260614_175822.log

---
## Learning Loop -- 2026-06-14 18:05

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 9
- Time: 3s
- Log: logs/learn_20260614_180526.log

---
## Learning Loop -- 2026-06-14 18:05

- Split: None, Tasks: 12
- Correct: 12 / 12 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 11
- Time: 4s
- Log: logs/learn_20260614_180529.log

---
## Learning Loop -- 2026-06-14 18:05

- Split: training, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 5s
- Log: logs/learn_20260614_180542.log

---
## Learning Loop -- 2026-06-14 18:07

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 9
- Time: 3s
- Log: logs/learn_20260614_180746.log

---
## Learning Loop -- 2026-06-14 18:07

- Split: None, Tasks: 12
- Correct: 12 / 12 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 11
- Time: 4s
- Log: logs/learn_20260614_180750.log

## Iter 19 — 2026-06-14 — branch test33

**Diagnosis**: Training phase; probe 0/3 and a 40-task scan was 0/40 — real
ARC-AGI-2 tasks (c9680e90 divider-gravity, 9f8de559 framed projection, …) need
substantial new capabilities, not a smallest step, and hacking one would be the F2
detector-accretion failure mode. The lowest genuinely-unproven rung is **R5
fast-path reuse** (iter 18's flagged next gap). Root cause found: `_apply_rule`
only handles `identity`, so **every** learned family rule (constant_output /
object_motion / object_recolor) declines on the fast path — they were re-derived on
the slow path every run (Reused: 0 forever). Their action args are holes filled
from the example comparison (§2.5-2b), so a single input grid can't apply them.

**Change**:
- `agent/active_agent.py`: added the Fast path for the three descriptor families.
  `_fit_descriptor_patterns` runs ExtractPattern once per task to re-fit the holes;
  `_reuse_descriptor_rule` (a) requires the stored rule's own condition matcher to
  fire on the fitted patterns, (b) **gates on the fitted rule reproducing every
  example output exactly** (rejects a superficial match), then (c) renders the test
  inputs via PredictOperator's existing make_grid+coloring renderers (no new
  transformation, CLAUDE.md §6.2). Patterns are fit once and shared across rules.
  This is value-agnostic reuse: the same stored abstraction re-fits to whatever the
  new task's comparison yields, not a literal replay.
- `tests/test_r5_reuse.py` (new, 6 tests): motion + constant reuse return the
  correct test prediction; cross-family offers decline (matcher gate); a 1-pair
  constant task declines under the floor-2 asymmetry; unknown type → None.
- No edit to `agent/active_operators.py` (F8 N/A), no frozen file, no new
  `_try_*`/`_apply_*`, no new DSL primitive. `procedural_memory/rule_00{1,2,3}.json`
  changed only in `times_reused` (now 4/30/6 — the R5 evidence; covers unchanged).

**Probe before**: training 0/3; easy_a 9/9, madeup 12/12, **Reused 0**. Rules 3,
covers mean 7.0.
**Probe after** : training 0/3 (0 errors, no false positives — the reproduction
gate rejects superficial matches); easy_a 9/9 **Reused 9**, madeup 12/12 **Reused
11**. 112 tests pass (106 + 6). `times_reused` 0→{4,30,6} persisted.

**Invariants**: forbidden=none; positives=P1..P6 all Δ0 → **NEUTRAL**. The reuse
blindspot is known (no P1–P6 measures fast-path reuse — covers grow identically on
either path, so P1/P2 are unchanged). This is real, named-rung work (R5 wired for
the first time, Reused 0→20 across the guards), not spinning; a neutral iter is
sanctioned (PROMPT.md §5, INVARIANTS §2/§3) and this is the first non-positive iter
after 14–18.

**Next gap (note for future iter)**: R5's Fast path now fires but is still gated by
covers-equivalence with the slow path, so no P-signal credits it — a candidate
*design* improvement is a reuse signal (Pn = stored-hit task-diversity) the user
would need to bless (don't self-edit the INVARIANTS contract). Otherwise R4
(2nd-order edge / ranking compare, `ARCKG/comparison.py`) is the remaining unproven
rung; and reuse currently only generalises within a family — a stored rule reused
on a *structurally different* task (true R5 done-when) is untested.

## Iter 19 [NEUTRAL] — 20260614_175604 — branch test33
- Probe: [17:56:17] Correct:     0 / 3  (0.0%)

---
## Learning Loop -- 2026-06-14 18:09

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 9
- Time: 3s
- Log: logs/learn_20260614_180937.log

---
## Learning Loop -- 2026-06-14 18:09

- Split: None, Tasks: 12
- Correct: 12 / 12 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 11
- Time: 4s
- Log: logs/learn_20260614_180940.log

---
## Learning Loop -- 2026-06-14 18:09

- Split: training, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 5s
- Log: logs/learn_20260614_180945.log

---
## Learning Loop -- 2026-06-14 18:19

- Split: None, Tasks: 13
- Correct: 13 / 13 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 12
- Time: 5s
- Log: logs/learn_20260614_181952.log

---
## Learning Loop -- 2026-06-14 18:20

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 9
- Time: 3s
- Log: logs/learn_20260614_182007.log

---
## Learning Loop -- 2026-06-14 18:20

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 9
- Time: 3s
- Log: logs/learn_20260614_182014.log

## Iter 20 [CLEAN] — 20260614_180937 — branch test33
- Probe: [18:09:50] Correct:     0 / 3  (0.0%)

---
## Learning Loop -- 2026-06-14 18:24

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 9
- Time: 3s
- Log: logs/learn_20260614_182406.log

---
## Learning Loop -- 2026-06-14 18:24

- Split: None, Tasks: 13
- Correct: 13 / 13 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 12
- Time: 5s
- Log: logs/learn_20260614_182409.log

---
## Learning Loop -- 2026-06-14 18:24

- Split: training, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 5s
- Log: logs/learn_20260614_182414.log

---
## Learning Loop -- 2026-06-14 18:29

- Split: training, Tasks: 60
- Correct: 0 / 60 (0.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 168s
- Log: logs/learn_20260614_182646.log

---
## Learning Loop -- 2026-06-14 18:32

- Split: training, Tasks: 60
- Correct: 0 / 60 (0.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 164s
- Log: logs/learn_20260614_183011.log

## Iter 21 — 2026-06-14 — branch test33

**Iter 21: no defensible step found — analysis only.**

**Diagnosis (grounded)**: Training phase. I scanned ~100 real ARC-AGI-2 training
tasks this iter — the seed-42 probe (0/3), a seed-7 ×60 run (0/60), plus iter-18's
×40 (0/40) — and **every single one falls to `rule=identity`: zero firings of any
of the three descriptor families** (constant_output / object_motion /
object_recolor). These are *not near-misses* a small fix could tip; the families
recognise single-dominant-transformation toy structure (one object moved, one
object recoloured, an all-equal output) and real ARC-AGI-2 tasks are multi-step
(c9680e90 = divider-gravity, e5790162 = colored-ray projection, 878187ab = framed
fill). The gap between "beginner curriculum mastered" and "real ARC" is the
**missing general Slow-path program synthesizer (modules F/G)** that composes
`make_grid`/`coloring` into multi-step programs — a large architectural piece, not
a smallest step — plus the relational / 2nd-order argument vocabulary those programs
need.

**State**: easy_a 9/9, madeup 13/13 (all §2.1 beginner concepts solved the intended
way). 3 rules, covers 2/17/3, P1=P2=7.33, P3=0.667, P4=932, P5=3, P6=1109. R0–R3
proven, R5 fast-path wired (iter 19). `background_of` already 0-is-canvas (verified —
not a gap here).

**Escalation paths evaluated and rejected (per §2.2/§5, in order)**:
- *A failing training task with a nameable small fix* — none exists: all-identity,
  no family engages, so there is no near-miss to repair, only the absent synthesizer.
- *A new transformation family/matcher for a real ARC pattern* — would land at
  covers=1, lowering P1 (§2.5-4 litmus: rule-count up without covers up = accretion,
  not progress); the documented `_try_*`/168-rule failure direction
  (`generalize_not_accrete_families`). Rejected.
- *Relational selection / target* (`adjacent`, "move toward object B", the canonical
  gravity/attraction pattern) — a genuinely missing and broadly-useful capability
  (§2.5-1 lists `same-color`/`adjacent` as LHS vocabulary to grow), but it is a
  *multi-iter* feature (new `agent/dsl_expr/relation.py` + ExtractPattern signal +
  fit integration + applier), not a smallest defensible single-commit step.
- *R4 — 2nd-order edge ranking* — **blocked on an open question**: `ranking.py`'s own
  docstring records that ranking over *comparison receipts* (`arbor-modules §2`
  "edge-of-edge", Q "가장 긴 derived 속성") is deliberately deferred, and BACKLOG_LOOP
  §5 says to surface (not invent) an answer when a rung touches an open question.
  Surfaced here; rung held.
- *Author another madeup task* — every §2.1 concept (size≠1, count≠1, multi-object
  selection, resize, unequal sizes, size↔property, pairs≠2) is already exercised and
  solved; a new one I can already pass is the busywork §2.2 explicitly forbids, and I
  found no selector gap that both fails today and is a *small* general extension.
- *Route rule_001 through AU to raise P3 0.667→1.0* — the two constant-output
  programs are identical (no varying args), so the "lift" would record zero
  substitutions: cosmetic P3-gaming, not a real generalization. Rejected.

**Change**: none. No code, no rule, no new task. (Working tree carries only
incidental probe-driven `times_reused` bumps and the snapshot/counter the loop
manages.)

**Probe before / after**: unchanged — easy_a 9/9, madeup 13/13, training 0/60. Rules
3, covers mean 7.33.

**Invariants**: forbidden=none; positives=all Δ0 → NEUTRAL by construction (a
no-op iter is sanctioned, PROMPT.md §5.3 / INVARIANTS §2–3). **Not** termination:
the system is *not* converged — the synthesizer frontier is real and large, just not
a one-iter step, so `_LOOP_COMPLETE.md` would be premature/dishonest (§2.2).

**Next gap (note for future iter)**: the single highest-value real frontier is the
**general Slow-path program synthesizer** (modules F/G) — a producer that searches
multi-step `make_grid`/`coloring` compositions with §2.5 argument expressions, so a
family can fire on a real multi-step task at all. Its prerequisite vocabulary is
**relational** selection/target (`adjacent`, "toward object B") — the canonical
gravity/projection pattern that every sampled training task needs and no current
selector can name. A defensible *first* slice for a future iter: seed
`agent/dsl_expr/relation.py` (`adjacent` / `toward`) as pure, tested util, driven by
one madeup gravity task authored to fail — then wire it as a fitted target in a
later iter. That is a real multi-step capability, not a detector; this iter declines
to half-build it rather than land broken scaffolding.

## Iter 21 [NEUTRAL] — 20260614_182406 — branch test33
- Probe: [18:24:19] Correct:     0 / 3  (0.0%)

---
## Learning Loop -- 2026-06-14 18:35

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 9
- Time: 3s
- Log: logs/learn_20260614_183528.log

---
## Learning Loop -- 2026-06-14 18:35

- Split: None, Tasks: 13
- Correct: 13 / 13 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 12
- Time: 5s
- Log: logs/learn_20260614_183531.log

---
## Learning Loop -- 2026-06-14 18:35

- Split: training, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 5s
- Log: logs/learn_20260614_183536.log

---
## Learning Loop -- 2026-06-14 18:41

- Split: None, Tasks: 14
- Correct: 13 / 14 (92.9%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 12
- Time: 5s
- Log: logs/learn_20260614_184129.log

---
## Learning Loop -- 2026-06-14 18:42

- Split: None, Tasks: 14
- Correct: 14 / 14 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 13
- Time: 5s
- Log: logs/learn_20260614_184200.log

---
## Learning Loop -- 2026-06-14 18:42

- Split: None, Tasks: 14
- Correct: 14 / 14 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 13
- Time: 5s
- Log: logs/learn_20260614_184210.log

---
## Learning Loop -- 2026-06-14 18:42

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 9
- Time: 3s
- Log: logs/learn_20260614_184221.log

---
## Iter 22 — 2026-06-14 — branch test33

**Diagnosis**: Training phase, probe 0/3 (all `rule=identity`) — real ARC-AGI-2
tasks need a multi-step synthesizer that is not a smallest step (iter 21's standing
analysis). The smallest *defensible, non-duplicate* gap is iter 21's own flagged
next frontier: every move-target the system can name (`bottom_right`, `offset`,
`constant`) is a function of the grid or the object's own bbox — none is **relational**
(destination = another object's position), yet the gravity / attraction / alignment
pattern that needs exactly that is ubiquitous in real ARC. That gap is a single,
general *argument-expression* extension (a new target kind), not a detector.

**Change**:
- `agent/dsl_expr/motion.py` — added the relational target expression `to_anchor`
  to `fit_target` (tried LAST, after every grid-relative/constant reading, so zero
  regression) and to `target_position` (new optional `objects` arg; resolves the
  anchor as the single *other* object, identity-based, declines otherwise). Minimal
  value-agnostic anchor = "the one other object"; a future iter lifts it to a fitted
  anchor *selector* over the others (§2.5-2b). Module + fn docstrings updated.
- `agent/active_operators.py` — `_object_motion` now records each pair's `others`
  (the unselected objects' bbox top-lefts, from G0 alone, P5) into the motions dict
  so `fit_target` can read the anchor; `_render_object_motion` passes the object
  list into `target_position`. (+11 lines; F8 satisfied by the co-touch to
  `agent/conditions/`.)
- `agent/conditions/object_motion.py` — matcher docstring now lists the relational
  `to_anchor` target alongside the corner/constant/translation readings.
- `data/ARC_madeup/mo_to_anchor.json` (NEW, F1-exempt) — a 2x2 mover + one anchor
  pixel, both at varying positions across 3 pairs, mover lands ON the anchor (drop
  scene). Authored to **fail** the prior vocabulary: per-pair deltas and absolute
  dsts all differ, the anchor is never at a corner, so only `to_anchor` fits.
- `tests/test_object_motion.py` (+6) — fit/resolve unit tests (fit; loses to a
  simpler constant; declines without a single other; resolve + declines without the
  object list / with >1 other) and two pipeline tests (solves end-to-end with
  target `to_anchor`; folds into the corner family via `save_rule` → one covers>1
  rule with a `?v` target + au trace).

**Probe before**: training 0/3; easy_a 9/9, madeup 13/13; rules 3, rule_002 covers
17, P1=P2=7.333, P3=0.667. 124 tests.
**Probe after** : easy_a 9/9, madeup **14/14** (mo_to_anchor CORRECT via
object_motion, folded into rule_002 covers 17→18, **no new rule**, solved through
the R5 stored fast path — the relational target re-resolves on the abstract rule).
130 tests pass (124+6).

**Invariants**: forbidden=none (check_invariants CLEAN, exit 0); positives=**P1
+0.333 (7.333→7.667), P2 +0.333 (7.333→7.667)** via covers union (rule count flat
— §2.5-4 litmus satisfied); P3/P4/P5 ±0; P6 −11 (active_operators grew by the
anchor-plumbing, the unavoidable cost of a new argument that the fit/render path
must carry — offset by all real logic living in `agent/dsl_expr/motion.py`). The
new target grows the LHS argument vocabulary under `agent/`, where §2.5-1 requires
it; no new `_try_*`, no new transformation primitive.

**Next gap (note for future iter)**: the relational target is now the *minimal*
two-object case — the anchor is hard-gated to "the single other object". The clear
next lift is a fitted **anchor selector** over the others (`unique`/`largest`/a
colour marker), so `to_anchor` survives a grid with 3+ objects and names *which* one
is the anchor — exactly the §2.5-2b selection-lift, climbed on a madeup task with a
distractor object. Beyond that, the standing frontier is unchanged: a general
multi-step Slow-path synthesizer (modules F/G) for real ARC-AGI-2, and R4 (2nd-order
edge ranking) which remains open-question-blocked.

## Iter 22 [CLEAN] — 20260614_183528 — branch test33
- Probe: [18:35:42] Correct:     0 / 3  (0.0%)

---
## Learning Loop -- 2026-06-14 18:46

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 9
- Time: 3s
- Log: logs/learn_20260614_184603.log

---
## Learning Loop -- 2026-06-14 18:46

- Split: None, Tasks: 14
- Correct: 14 / 14 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 13
- Time: 5s
- Log: logs/learn_20260614_184606.log

---
## Learning Loop -- 2026-06-14 18:46

- Split: training, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 5s
- Log: logs/learn_20260614_184612.log

---
## Learning Loop -- 2026-06-14 18:49

- Split: None, Tasks: 15
- Correct: 14 / 15 (93.3%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 13
- Time: 6s
- Log: logs/learn_20260614_184929.log

---
## Learning Loop -- 2026-06-14 18:50

- Split: None, Tasks: 15
- Correct: 15 / 15 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 14
- Time: 6s
- Log: logs/learn_20260614_185034.log

---
## Learning Loop -- 2026-06-14 18:51

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 9
- Time: 3s
- Log: logs/learn_20260614_185059.log

---
## Learning Loop -- 2026-06-14 18:52

- Split: training, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 5s
- Log: logs/learn_20260614_185238.log

---
## Iter 23 — 2026-06-14 — branch test33

**Diagnosis**: Iter 22 added the relational `to_anchor` target but hard-gated the
anchor to "the single other object" — it declines the moment a grid holds a
distractor. That was iter 22's own flagged next gap: lift the anchor to a fitted
*selector over the others* (§2.5-2b), so `to_anchor` names *which* of several
objects is the anchor. The smallest defensible step is to reuse the existing
selection vocabulary (`fit_selector`/`select_object`) for the anchor rather than
build new machinery, exercised on a madeup task that adds a distractor object.

**Change**:
- `agent/dsl_expr/motion.py` — `fit_target`'s `to_anchor` branch now fits an
  anchor *selector* over the other objects (new `_fit_anchor`): for each pair the
  anchor is the other object at the mover's destination, and `fit_selector` finds
  one input-only criterion (unique/largest/odd-one-out/…) naming it in every pair.
  Returns `{"kind":"to_anchor","anchor":<selector>}`. The single-other case fits
  `unique`, so prior behaviour is a special case of the general lift.
  `target_position` resolves the anchor via `select_object` over the others (with a
  legacy single-other fallback when no anchor selector is recorded). Module docstring
  updated.
- `agent/active_operators.py` — `_object_motion` now records each pair's full
  unselected object dicts (`other_objs`) alongside the positions (`others`), so
  `fit_target` can run the selection vocabulary over them (+6 lines; F8 satisfied
  by the co-touch to `agent/conditions/`).
- `agent/conditions/object_motion.py` — matcher docstring now describes the
  fitted anchor selector inside the relational target.
- `data/ARC_madeup/mo_anchor_select.json` (NEW, F1-exempt) — a 2×2 mover, a
  size-3 anchor bar, and a single-pixel distractor, all at varying positions; the
  mover lands on the anchor bar (the LARGEST other). Authored to **fail** iter 22's
  exactly-one-other gate: with two others the anchor needs a selector. The mover is
  the size extreme so the existing selector names which object moves; the new
  content is the anchor selection.
- `tests/test_object_motion.py` — updated the two iter-22 `to_anchor` tests to the
  new descriptor shape (`anchor` sub-expr); added `_pix`/`_blob` builders, a
  multi-other fit test (`largest`), a dst-matches-no-other decline test, and a
  pipeline test that solves `mo_anchor_select` with `anchor={"kind":"largest"}`.

**Probe before**: training 0/3; easy_a 9/9, madeup 14/14; rules 3, rule_002 covers
18, P1=P2=7.667, P3=0.667. 130 tests.
**Probe after** : easy_a 9/9, madeup **15/15** (mo_anchor_select CORRECT via
object_motion, folded into rule_002 covers 18→19, **no new rule**, solved through
the R5 stored fast path — the anchor selector re-resolves on the abstract rule).
training 0/3 (0 errors — no crash regression). 133 tests pass (130+3).

**Invariants**: forbidden=none (check_invariants CLEAN, exit 0); positives=**P1
+0.333 (7.667→8.0), P2 +0.333 (7.667→8.0)** via covers union (rule count flat —
§2.5-4 litmus satisfied); P3/P4/P5 ±0; P6 −6 (active_operators grew by the
other_objs plumbing, the cost of feeding the selector its material — all real
fitting logic lives in `agent/dsl_expr/motion.py`). The anchor selector grows the
LHS argument vocabulary under `agent/` by *reusing* the existing selection
vocabulary; no new `_try_*`, no new transformation primitive.

**Next gap (note for future iter)**: the relational target's anchor now spans the
full selector vocabulary (unique/size/position/odd-one-out/ranked). The standing
frontier is unchanged and larger: a general multi-step Slow-path *synthesizer*
(modules F/G) is what the training 0/3 actually needs — every easy/madeup win is a
single fitted argument expression, but real ARC-AGI-2 tasks chain several
transformations, which no current path composes. R4 (2nd-order edge ranking)
remains open-question-blocked.

## Iter 23 [CLEAN] — 20260614_184602 — branch test33
- Probe: [18:46:17] Correct:     0 / 3  (0.0%)

---
## Learning Loop -- 2026-06-14 18:54

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 9
- Time: 3s
- Log: logs/learn_20260614_185420.log

---
## Learning Loop -- 2026-06-14 18:54

- Split: None, Tasks: 15
- Correct: 15 / 15 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 14
- Time: 6s
- Log: logs/learn_20260614_185423.log

---
## Learning Loop -- 2026-06-14 18:54

- Split: training, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 5s
- Log: logs/learn_20260614_185429.log

---
## Learning Loop -- 2026-06-14 18:59

- Split: None, Tasks: 16
- Correct: 15 / 16 (93.8%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 14
- Time: 6s
- Log: logs/learn_20260614_185952.log

---
## Learning Loop -- 2026-06-14 19:03

- Split: None, Tasks: 16
- Correct: 16 / 16 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 14
- Time: 6s
- Log: logs/learn_20260614_190310.log

---
## Learning Loop -- 2026-06-14 19:03

- Split: None, Tasks: 16
- Correct: 16 / 16 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 14
- Time: 6s
- Log: logs/learn_20260614_190321.log

---
## Learning Loop -- 2026-06-14 19:04

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 9
- Time: 3s
- Log: logs/learn_20260614_190409.log

---
## Learning Loop -- 2026-06-14 19:07

- Split: training, Tasks: 30
- Correct: 0 / 30 (0.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 81s
- Log: logs/learn_20260614_190541.log

---
## Iter 24 — 2026-06-14 — branch test33

**Diagnosis**: Iter 23's own next-gap noted the selector vocabulary is complete and
the standing frontier is *composing* transformations — real tasks chain steps no
single family handles. The smallest defensible slice of that: a move that *also
recolours* the object (translate ∘ recolour). `object_motion` alone gates on colour
preserved; `object_recolor` alone gates on cells unchanged — so neither solves it,
yet it is one composition expressible by lifting the new colour into a fitted
argument expression on the existing move family (not a 4th family — §2.5-3/2b).

**Change**:
- `data/ARC_madeup/mo_move_recolor.json` (NEW, F1-exempt) — a 2×2 block that both
  moves to a constant position (0,0) and changes to a constant new colour (4),
  colours/positions varying across pairs. Authored to **fail**: confirmed INCORRECT
  (rule=identity) before the change.
- `agent/active_operators.py` — `_identify_move` now returns a 4-tuple with the
  object's *new colour*: when the colour-set+size match fails it falls back to a
  colour-invariant *shape*+size match (tried only after the colour-preserving match,
  so existing moves are identified byte-identically — zero regression) and reports
  the new colour. `_object_motion` records the per-pair new colour and fits one
  value-agnostic colour expression via the existing `fit_color_source`
  (another-object's-colour, or a fitted constant); a mix of recoloured and
  colour-preserving pairs declines. `GeneralizeOperator` rides the fitted colour as
  a second `place_object` arg (omitted for a pure move, so the colour-preserving
  rule dict is byte-for-byte unchanged and still merges). `PredictOperator` /
  `_render_object_motion` paint the moved object in the resolved new colour when
  recolouring, else its own colours.
- `agent/conditions/object_motion.py` — per-pair gate now accepts
  `color_preserved OR recolored`; when any pair recolours, the fitted `color`
  expression must be present (else decline). Docstring + schema comment updated
  (F8 satisfied by this co-touch to `agent/conditions/`).
- `tests/test_object_motion.py` — updated the three `_identify_move` tests to the
  4-tuple; added: recolour identification reports the new colour, `_object_motion`
  fits the constant colour expr, matcher requires the colour expr when recoloured,
  and pipeline solves `mo_move_recolor` via the same family carrying the colour arg.

**Probe before**: training 0/3; easy_a 9/9, madeup 15/16 (mo_move_recolor INCORRECT);
rules 3, rule_002 covers 19, P1=P2=8.0, P3=0.667. 133 tests.
**Probe after** : easy_a 9/9, madeup **16/16** (mo_move_recolor CORRECT via
object_motion, folded into rule_002 covers 19→20, **no new rule**). training 0/30
sampled — **0 errors, 0 spurious rules** (relaxed matcher does not over-fire on real
data). 137 tests pass.

**Invariants**: forbidden=none (check_invariants CLEAN, exit 0); positives=**P1
+0.333 (8.0→8.333), P2 +0.333 (8.0→8.333)** via covers union (rule count flat —
§2.5-4 litmus satisfied); P3/P4/P5 ±0; P6 −83 (active_operators grew by the
move∘recolour plumbing — the cost of feeding the new fitted colour argument; the
colour-fitting itself reuses `agent/dsl_expr`'s `fit_color_source`). No new family,
no new `_try_*`, no new transformation primitive — the new colour is one more fitted
LHS argument expression on the existing move family.

**Next gap (note for future iter)**: move∘recolour is the first *composition* of two
transformations expressed on one family by lifting an argument. The colour key is
dropped in the AU merge into rule_002 (its skeleton lacks colour), so the abstract
rule does not yet *carry* the colour as a `?v` variable — lifting divergent colour
expressions across two move∘recolour tasks (a second such task) is the next coverage
step. The larger frontier is unchanged: a general multi-step synthesizer (modules
F/G) for tasks whose solution is a *sequence* of transformations with observed
intermediate structure, which single-argument lifting cannot reach.

## Iter 24 [CLEAN] — 20260614_185419 — branch test33
- Probe: [18:54:34] Correct:     0 / 3  (0.0%)

---
## Learning Loop -- 2026-06-14 19:08

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 9
- Time: 3s
- Log: logs/learn_20260614_190841.log

---
## Learning Loop -- 2026-06-14 19:08

- Split: None, Tasks: 16
- Correct: 16 / 16 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 14
- Time: 6s
- Log: logs/learn_20260614_190845.log

---
## Learning Loop -- 2026-06-14 19:08

- Split: training, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 5s
- Log: logs/learn_20260614_190851.log

## Iter 25 — 2026-06-14T10:16:56Z — branch test33

**Diagnosis**: The training probe shows the real frontier plainly: on real ARC the
Slow path emits **nothing** (`--split training` → 0 correct, **+0 learned**, 0 rule
hits across 30 sampled tasks). The three families (constant_output, object_motion,
object_recolor) master easy_a + madeup but none of their *matchers* fire on real
data — they recognize hand-picked shapes, they do not **search**. Per `arbor.md`
Fast/Slow path and `arbor-modules.md` modules F/G, the missing piece is a general
Slow-path **synthesizer**: given a task's pairs, search compositions of the two
frozen primitives for a program reproducing every output. test33 had no synthesizer
module at all. Smallest defensible step toward it (the smaller half): build the
synthesizer's evaluator + a bounded search that *rediscovers the existing families'
program shapes by search*, off the live path, before wiring it in or feeding its
output to AU.

**Change**:
- `program/synthesis.py` (NEW) — `run_program(program, grid)` evaluates a program
  (list of steps) by composing ONLY `make_grid`/`coloring` via `apply_DSL` (adds no
  transformation vocabulary — F3 safe). Steps: `make_grid`, `coloring`, and an
  aggregate `paint_objects` (loops over *whatever* objects the input has — one
  structure-agnostic step, so a program stays consistent across pairs with differing
  object counts). A tiny expression evaluator resolves every argument from the
  *input* grid (P5: variables originate in G0), so a synthesized program transfers
  unchanged to the held-out test input. `synthesize_task(pairs)` searches three
  schemas — identity, constant/common output (rediscovers rule_001's
  `copy_common_output` as an explicit make_grid+coloring program), object
  reconstruction onto a fitted (`in_h`/`in_w` or shared-constant) canvas — and
  returns the first program reproducing **all** pairs, else `None`. A miss returns
  `None` honestly; it never falls back to a literal per-pair fit (§2.5-2: literal
  coordinate programs are the 168-rule failure mode and do not anti-unify).
- `tests/test_synthesis.py` (NEW, 8 tests) — evaluator composes only the two
  primitives; `paint_objects` reconstructs input objects; search synthesizes
  identity and (from the real `data/ARC_easy_a/easy000a.json`) constant-output,
  proving the general search reproduces a family's program *and* transfers to the
  test input; object-move returns `None` (honest miss); empty pairs → `None`.

**Probe before**: training 0/3 (0 learned, 0 hits); easy_a 9/9, madeup 16/16; rules
3, P1=P2=8.333, P3=0.667. 137 tests.
**Probe after** : unchanged on all probes (synthesizer is off the live path — zero
regression risk by construction). 145 tests pass (+8). Synthesizer rediscovers the
constant-output family's program purely by search over the two frozen primitives.

**Invariants**: forbidden=none (check_invariants CLEAN, no F1–F8). positives=all Δ0
(NEUTRAL) — this is substrate whose payoff lands when it is wired onto the
`GeneralizeOperator` path and its per-task programs are fed to `anti_unification`
(INVARIANTS §3 "scaffolding whose payoff lands in a later iter"). No new family, no
`_try_*`, no third DSL primitive — a *search* over compositions of the existing two.

**Next gap (note for future iter)**: two unwired steps remain before the synthesizer
moves a signal — (1) wire `synthesize_task` into `GeneralizeOperator` as the
fallback when no family matcher fires (produces a program for a task the matchers
miss), guarded so easy_a/madeup keep reusing their stored rules (no regression);
(2) grow the search grammar with a *target-fitting* schema (object move) so the
honest-miss case in `test_honest_miss_on_object_move` becomes a hit — at which point
two such task programs can be lifted by `unify()` (R3, P3↑). The synthesizer is the
general mechanism that should eventually let `_try_*`/family matchers be *deleted*
(P6), replacing recognition-by-shape with search.

## Iter 25 [NEUTRAL] — 20260614_190841 — branch test33
- Probe: [19:08:57] Correct:     0 / 3  (0.0%)

---
## Learning Loop -- 2026-06-14 19:18

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 9
- Time: 3s
- Log: logs/learn_20260614_191840.log

---
## Learning Loop -- 2026-06-14 19:18

- Split: None, Tasks: 16
- Correct: 16 / 16 (100.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 14
- Time: 6s
- Log: logs/learn_20260614_191844.log

---
## Learning Loop -- 2026-06-14 19:18

- Split: training, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 5s
- Log: logs/learn_20260614_191851.log

---
## Learning Loop -- 2026-06-14 19:27

- Split: None, Tasks: 17
- Correct: 16 / 17 (94.1%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 14
- Time: 6s
- Log: logs/learn_20260614_192725.log

---
## Learning Loop -- 2026-06-14 19:28

- Split: None, Tasks: 17
- Correct: 17 / 17 (100.0%)
- Rules: 3 -> 4 (+1 learned)
- Stored rule hits: 14
- Time: 6s
- Log: logs/learn_20260614_192837.log

---
## Learning Loop -- 2026-06-14 19:28

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 4 -> 4 (+0 learned)
- Stored rule hits: 9
- Time: 3s
- Log: logs/learn_20260614_192853.log

---
## Learning Loop -- 2026-06-14 19:29

- Split: training, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 4 -> 4 (+0 learned)
- Stored rule hits: 0
- Time: 5s
- Log: logs/learn_20260614_192857.log

---
## Learning Loop -- 2026-06-14 19:31

- Split: training, Tasks: 40
- Correct: 0 / 40 (0.0%)
- Rules: 4 -> 4 (+0 learned)
- Stored rule hits: 0
- Time: 110s
- Log: logs/learn_20260614_192910.log

## Iter 26 [CLEAN] — 20260614_191840 — branch test33
- Probe: [19:18:56] Correct:     0 / 3  (0.0%)

---
## Learning Loop -- 2026-06-14 19:34

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 4 -> 4 (+0 learned)
- Stored rule hits: 9
- Time: 3s
- Log: logs/learn_20260614_193449.log

---
## Learning Loop -- 2026-06-14 19:34

- Split: None, Tasks: 17
- Correct: 17 / 17 (100.0%)
- Rules: 4 -> 4 (+0 learned)
- Stored rule hits: 15
- Time: 6s
- Log: logs/learn_20260614_193453.log

---
## Learning Loop -- 2026-06-14 19:35

- Split: training, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 4 -> 4 (+0 learned)
- Stored rule hits: 0
- Time: 5s
- Log: logs/learn_20260614_193500.log

---
## Learning Loop -- 2026-06-14 19:44

- Split: None, Tasks: 18
- Correct: 18 / 18 (100.0%)
- Rules: 4 -> 4 (+0 learned)
- Stored rule hits: 15
- Time: 7s
- Log: logs/learn_20260614_194446.log

---
## Learning Loop -- 2026-06-14 19:45

- Split: None, Tasks: 18
- Correct: 18 / 18 (100.0%)
- Rules: 4 -> 4 (+0 learned)
- Stored rule hits: 14
- Time: 6s
- Log: logs/learn_20260614_194511.log

---
## Learning Loop -- 2026-06-14 19:45

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 4 -> 4 (+0 learned)
- Stored rule hits: 9
- Time: 3s
- Log: logs/learn_20260614_194518.log

## Iter 27 [CLEAN] — 20260614_193449 — branch test33
- Probe: [19:35:05] Correct:     0 / 3  (0.0%)

---
## Learning Loop -- 2026-06-14 19:48

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 4 -> 4 (+0 learned)
- Stored rule hits: 9
- Time: 3s
- Log: logs/learn_20260614_194856.log

---
## Learning Loop -- 2026-06-14 19:49

- Split: None, Tasks: 18
- Correct: 18 / 18 (100.0%)
- Rules: 4 -> 4 (+0 learned)
- Stored rule hits: 14
- Time: 7s
- Log: logs/learn_20260614_194859.log

---
## Learning Loop -- 2026-06-14 19:49

- Split: training, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 4 -> 4 (+0 learned)
- Stored rule hits: 0
- Time: 5s
- Log: logs/learn_20260614_194906.log

---
## Learning Loop -- 2026-06-14 19:55

- Split: None, Tasks: 7
- Correct: 1 / 7 (14.3%)
- Rules: 4 -> 4 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260614_195507.log

---
## Learning Loop -- 2026-06-14 19:56

- Split: None, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 4 -> 5 (+1 learned)
- Stored rule hits: 14
- Time: 7s
- Log: logs/learn_20260614_195624.log

---
## Learning Loop -- 2026-06-14 19:58

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 5 -> 5 (+0 learned)
- Stored rule hits: 9
- Time: 3s
- Log: logs/learn_20260614_195757.log

---
## Learning Loop -- 2026-06-14 20:00

- Split: training, Tasks: 60
- Correct: 1 / 60 (1.7%)
- Rules: 5 -> 6 (+1 learned)
- Stored rule hits: 0
- Time: 166s
- Log: logs/learn_20260614_195800.log

## Iter 28 [CLEAN] — 20260614_194855 — branch test33
- Probe: [19:49:11] Correct:     0 / 3  (0.0%)

---
## Learning Loop -- 2026-06-14 20:05

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 5 -> 5 (+0 learned)
- Stored rule hits: 9
- Time: 3s
- Log: logs/learn_20260614_200550.log

---
## Learning Loop -- 2026-06-14 20:06

- Split: None, Tasks: 20
- Correct: 20 / 20 (100.0%)
- Rules: 5 -> 5 (+0 learned)
- Stored rule hits: 14
- Time: 7s
- Log: logs/learn_20260614_200554.log

---
## Learning Loop -- 2026-06-14 20:06

- Split: training, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 5 -> 5 (+0 learned)
- Stored rule hits: 0
- Time: 5s
- Log: logs/learn_20260614_200602.log

---
## Learning Loop -- 2026-06-14 20:14

- Split: None, Tasks: 23
- Correct: 23 / 23 (100.0%)
- Rules: 5 -> 6 (+1 learned)
- Stored rule hits: 14
- Time: 8s
- Log: logs/learn_20260614_201359.log

---
## Learning Loop -- 2026-06-14 20:14

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 9
- Time: 3s
- Log: logs/learn_20260614_201425.log

## Iter 29 — 2026-06-14 — branch test33

**Diagnosis**: Training phase, probe 0/3 (all `rule=identity`). The Slow-path
synthesizer (`program/synthesis.py`, built iters 25–28) has 4 schemas — identity,
constant-output, object-reconstruct-onto-canvas, global colour-substitution — but
the most canonical ARC class is still unhandled: the **dihedral geometric
transforms** (flip / rotate / transpose). A scan of 1000 training tasks finds ≥7
that are a single whole-grid dihedral transform (flip_h 67a3c6ac, flip_v 68b16354,
rot180 3c9b0459+6150a2bd, transpose 74dd1130+9dfd6313, rot270 ed36ccf7) and the
synthesizer returned `None` on all of them. This is exactly the CLAUDE.md §6 case
("rotate/flip must be *discovered as compositions*, not hand-coded") and §2.5-1
gives flip_h as the canonical coordinate-expression example — so it is a search-
grammar gap, not a missing primitive. Picked it because it is general (one schema
covers all 8 maps), value-agnostic, common, and fires the R3 lift (multiple maps
sharing the make_grid+paint_remap skeleton → `unify()` lifts the map leaf to `?v`).

**Change**:
- `program/synthesis.py` — added `_DIHEDRAL` (7 coordinate maps, each a `(remap,
  swaps)`), a `paint_remap` step in `run_program` (paints every non-bg input cell,
  in its own colour, at its remapped position — composes ONLY the frozen `coloring`
  primitive, F3-safe), and **Schema 5** in `_candidate_programs` (yields one
  `make_grid(fitted dims) + paint_remap(name)` candidate per map; `synthesize_task`
  keeps the first reproducing every pair). Dims-swapping maps (transpose/rot90/
  rot270/anti) fit an `in_w × in_h` canvas.
- `data/ARC_madeup/{flip_h,flip_v,rot180}.json` (NEW, F1-exempt) — ground the R3
  lift: same output dims → shared make_grid+paint_remap skeleton, diverging only in
  the map leaf, so all three fold into ONE `covers=3` rule.
- `tests/test_synthesis.py` (+4) — flip_h discovered & transfers to held-out input;
  transpose swaps canvas dims; rot180 discovered; a non-symmetric task does not get
  mislabelled as a dihedral map (honest decline).

**Probe before**: training 0/3; easy_a 9/9, madeup 20/20; rules 5, P1=P2=5.8,
P3=0.8. 168 tests.
**Probe after** : easy_a 9/9, madeup 23/23 (incl. 3 new dihedral, all via
`synthesized_program`); rules 6; rule_006 = dihedral family `covers=3` (flip_h,
flip_v, rot180) with `anti_unification_trace`, map leaf lifted to `?v2`. P3
0.8→0.833. P1/P2 5.8→5.333 (arithmetic dilution by the covers=20 rule_002 — the
documented instrumentation trap; the new rule itself is covers=3, not an accreted
covers=1 detector). 172 tests. The same schema solves 7 real ARC-AGI-2 training
tasks (67a3c6ac/68b16354/3c9b0459/6150a2bd/74dd1130/9dfd6313/ed36ccf7), incl. their
held-out test inputs — generality, not memorised.

**Invariants**: forbidden=none (check_invariants CLEAN, exit 0). positives=P3
+0.033 (au_traced_frac); P1/P2 −0.467 (dilution, not accretion — covers up with
rule count, §2.5-4 litmus held); P4/P5/P6 Δ0. No `active_operators.py` edit (F8
N/A); no new `_try_*`/DSL primitive; the new transform is a coordinate expression
over the two frozen primitives, discovered by SEARCH.

**Next gap (note for future iter)**: the dims-swapping dihedral maps (transpose,
rot90, rot270, antitranspose) form a *second* skeleton family (in_w×in_h canvas) —
two such madeup/real tasks would lift them too. Beyond geometry, the dominant
training miss is same-size *conditional* recolours/rearrangements (gravity,
symmetry-repair, neighbourhood maps) that no current schema expresses; and P1/P2
remain pinned by rule_002's covers=20 — the instrumentation still punishes any new
family arithmetically, so P3 is the truer progress signal here.

## Iter 29 [CLEAN] — 20260614_200550 — branch test33
- Probe: [20:06:07] Correct:     0 / 3  (0.0%)

---
## Learning Loop -- 2026-06-14 20:17

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 9
- Time: 3s
- Log: logs/learn_20260614_201734.log

---
## Learning Loop -- 2026-06-14 20:17

- Split: None, Tasks: 23
- Correct: 23 / 23 (100.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 14
- Time: 8s
- Log: logs/learn_20260614_201737.log

---
## Learning Loop -- 2026-06-14 20:17

- Split: training, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 0
- Time: 5s
- Log: logs/learn_20260614_201745.log

---
## Learning Loop -- 2026-06-14 20:28

- Split: None, Tasks: 23
- Correct: 23 / 23 (100.0%)
- Rules: 5 -> 6 (+1 learned)
- Stored rule hits: 14
- Time: 8s
- Log: logs/learn_20260614_202828.log

---
## Learning Loop -- 2026-06-14 20:28

- Split: None, Tasks: 3
- Correct: 3 / 3 (100.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 0
- Time: 1s
- Log: logs/learn_20260614_202842.log

---
## Learning Loop -- 2026-06-14 20:29

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 9
- Time: 3s
- Log: logs/learn_20260614_202908.log

## Iter 30 — 2026-06-14 — branch test33

**Diagnosis**: Training phase, probe 0/3 (all `rule=identity` — the three sampled
tasks c9680e90/878187ab/e5790162 are conditional/spatial transforms no schema yet
expresses). Iter 29's next-gap note flagged that the dims-swapping dihedral maps
(transpose/rot90/rot270/antitranspose) form a *second* skeleton family because
their canvas is `in_w×in_h` not `in_h×in_w`, so the two-step `make_grid +
paint_remap` schema split flips (rule_006, covers=3) from transposes into separate
rules — and grounding the second family the iter-29 way would dilute P1/P2 *again*
via the covers=20 rule_002. The smaller, *non*-duplicative gap: **collapse the
schema so all eight dihedral maps share one program skeleton**, lifting them into a
single rule instead of two families (the §2.5-4 litmus — covers up, rule count
flat).

**Change**:
- `program/synthesis.py` — replaced the two-step dihedral candidate (`make_grid` +
  `paint_remap`) with a single `dihedral` step that builds its *own* correctly-sized
  canvas (dims swapped for the swap maps, read from `_DIHEDRAL`'s flag) and then
  paints the remap. It composes ONLY the two frozen primitives internally
  (`make_grid`→`coloring`), so it is F3-safe — exactly as `paint_objects` does. Now
  every map yields the same skeleton `[("dihedral", ("const", ?v))]`, so swap and
  non-swap maps anti-unify into ONE `covers>1` rule. Removed the now-dead
  `paint_remap` step. Schema 5 yields one single-step candidate per map.
- `procedural_memory/rule_006.json` — deleted the stale two-step flip-only rule and
  re-learned the unified rule: it now `covers` all six dihedral tasks — `flip_h`,
  `flip_v`, `rot180` (madeup) **plus** `74dd1130`, `9dfd6313` (transpose),
  `ed36ccf7` (rot270) (real ARC-AGI-2 training tasks the synthesizer already
  solves, folded in per PROMPT §2.2.3 "generalize across what is already solved").
  Program `[["dihedral", ["const", "?v1"]]]`, `anti_unification_trace` set.
- `tests/test_synthesis.py` — updated the 4 dihedral assertions to the single-step
  shape and added `test_swap_and_nonswap_dihedral_share_one_skeleton` (flip_h and
  transpose now produce the *same* `_program_skeleton` despite different map leaves
  — the unification payoff). 173 tests pass (was 172).

**Probe before**: training 0/3; easy_a 9/9, madeup 23/23; 6 rules, P1=P2=5.333,
P3=0.833. rule_006 = two-step flip family covers=3.
**Probe after** : easy_a 9/9, madeup 23/23 (unchanged guards); 6 rules; unified
rule_006 covers=6 (all 8 dihedral maps share its skeleton). All 7 real dihedral
training tasks (67a3c6ac/68b16354/3c9b0459/6150a2bd/74dd1130/9dfd6313/ed36ccf7)
still solve incl. held-out test inputs. P1/P2 5.333→5.833, P3 0.833 (flat).

**Invariants**: forbidden=none (check_invariants CLEAN, exit 0). positives=P1 +0.5,
P2 +0.5 (covers up *with* rule count flat — the §2.5-4 real-progress signature, the
opposite of iter 29's dilution); P3/P4/P5/P6 Δ0. No new `_try_*`/`_apply_*`; no new
DSL primitive (the `dihedral` step is a coordinate expression composing the two
frozen primitives, discovered by SEARCH); no `active_operators.py` edit (F8 N/A).

**Next gap (note for future iter)**: the dihedral family is now maximally general
(one rule, all 8 maps). The dominant remaining training miss is same-size
*conditional* transforms (gravity 1e0a9b12, ray/projection e5790162, occlusion
878187ab, symmetry-repair) — each needs a *selection/condition* the grammar can't
yet express (which cells move/recolour as a function of neighbourhood or alignment),
not another whole-grid map. That is genuinely new machinery (R4 second-order
relation / conditional selection), not a smallest step; the cheap geometric wins are
now exhausted.

## Iter 30 [CLEAN] — 20260614_201733 — branch test33
- Probe: [20:17:51] Correct:     0 / 3  (0.0%)

---
## Learning Loop -- 2026-06-14 20:33

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 9
- Time: 3s
- Log: logs/learn_20260614_203328.log

---
## Learning Loop -- 2026-06-14 20:33

- Split: None, Tasks: 23
- Correct: 23 / 23 (100.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 14
- Time: 8s
- Log: logs/learn_20260614_203332.log

---
## Learning Loop -- 2026-06-14 20:33

- Split: training, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 6 -> 6 (+0 learned)
- Stored rule hits: 0
- Time: 6s
- Log: logs/learn_20260614_203340.log

---
## Learning Loop -- 2026-06-14 20:37

- Split: None, Tasks: 3
- Correct: 3 / 3 (100.0%)
- Rules: 6 -> 7 (+1 learned)
- Stored rule hits: 0
- Time: 2s
- Log: logs/learn_20260614_203727.log

---
## Learning Loop -- 2026-06-14 20:37

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 7 -> 7 (+0 learned)
- Stored rule hits: 9
- Time: 3s
- Log: logs/learn_20260614_203743.log

---
## Learning Loop -- 2026-06-14 20:37

- Split: None, Tasks: 23
- Correct: 23 / 23 (100.0%)
- Rules: 7 -> 7 (+0 learned)
- Stored rule hits: 14
- Time: 8s
- Log: logs/learn_20260614_203747.log

## Iter 31 — 2026-06-14 — branch test33

**Diagnosis**: Training phase, probe 0/3 (c9680e90/878187ab/e5790162 are
same-size conditional transforms needing R4 machinery — not a smallest step, per
iter-30's note). Scanning all 1000 training tasks for a *general* gap whose fix is
a clean coordinate-expression composition of the two frozen primitives surfaced
**pixel scaling (block upsample)**: 51 tasks have integer-multiple output dims, and
3 are pure block-upsamples (`60c09cac`/`c59eb873` at 2×, `9172f3a0` at 3×) the
synthesizer cannot express — yet they share one skeleton with two distinct factor
pairs, the textbook R3 lift target (PROMPT §2.2.3 "generalize across what is
already solved").

**Change**:
- `program/synthesis.py` — added a `scale` step to `run_program` (makes an
  `rh·in_h × rw·in_w` canvas via `make_grid`, paints every cell's `rh×rw` block in
  its own colour via `coloring` — a value-agnostic coordinate expression composing
  ONLY the two frozen primitives, F3-safe, exactly like `dihedral`). Added Schema 6
  + `_fit_scale(pairs)`: fits one shared integer factor pair across all pairs, emits
  `[("scale", ("const",rh), ("const",rw))]`. Its `(("scale",("const",None),
  ("const",None)),)` skeleton lets two scale tasks with different factors lift via
  `unify()` into one `covers>1` rule.
- `procedural_memory/rule_007.json` (new) — learned from the 3 scale tasks: covers
  all three, program lifted to `[["scale", ["const","?v3"], ["const","?v4"]]]`,
  `anti_unification_trace` set (au across factors (2,2) and (3,3)). All 3 solve
  incl. held-out test inputs.
- `tests/test_synthesis.py` — +4 scale tests (2× discovery+transfer, non-square
  factors, declines on non-integer-multiple, factors-share-one-skeleton). 177 pass.

**Probe before**: training 0/3; easy_a 9/9, madeup 23/23; 6 rules, P1=P2=5.833,
P3=0.833.
**Probe after** : easy_a 9/9, madeup 23/23 (guards unchanged); 7 rules; new
rule_007 covers=3 (3 real ARC-AGI-2 scale tasks now solve via ONE lifted rule).
P1/P2 5.833→5.429, P3 0.833→0.857.

**Invariants**: forbidden=none (check_invariants CLEAN, exit 0). positives=P3
+0.024 (au-traced fraction up — AU genuinely fired across two factor pairs).
P1/P2 dipped −0.40: the documented saturation artifact — a covers=3 family lowers
the *mean* only because existing rules carry unusually high covers (rule_002=20);
the *absolute* solved count rose +3 with only +1 rule (3 tasks/rule, the efficient
direction §2.5-4). No new `_try_*`/`_apply_*`; no new DSL primitive (scale is a
coordinate expression composing the two frozen primitives, discovered by SEARCH);
no `active_operators.py` edit (F8 N/A).

**Next gap (note for future iter)**: the dominant remaining integer-multiple family
is *conditional tiling* (~47 tasks, e.g. fractal 007bbfb7: output is an rh×rw macro
grid of tiles, each tile = a copy of the input iff input[R][C] satisfies a
condition). That needs a per-macro-cell *selection/condition* keyed on the input
cell value — the §2.5-2b "fill the variable by a selector grounded in COMM/DIFF"
machinery, a genuine new capability rather than another whole-grid coordinate map.

## Iter 31 [CLEAN] — 20260614_203328 — branch test33
- Probe: [20:33:46] Correct:     0 / 3  (0.0%)

---
## Learning Loop -- 2026-06-14 20:41

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 7 -> 7 (+0 learned)
- Stored rule hits: 9
- Time: 3s
- Log: logs/learn_20260614_204107.log

---
## Learning Loop -- 2026-06-14 20:41

- Split: None, Tasks: 23
- Correct: 23 / 23 (100.0%)
- Rules: 7 -> 7 (+0 learned)
- Stored rule hits: 14
- Time: 8s
- Log: logs/learn_20260614_204111.log

---
## Learning Loop -- 2026-06-14 20:41

- Split: training, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 7 -> 7 (+0 learned)
- Stored rule hits: 0
- Time: 6s
- Log: logs/learn_20260614_204120.log

---
## Learning Loop -- 2026-06-14 20:45

- Split: None, Tasks: 2
- Correct: 2 / 2 (100.0%)
- Rules: 7 -> 8 (+1 learned)
- Stored rule hits: 1
- Time: 4s
- Log: logs/learn_20260614_204513.log

---
## Learning Loop -- 2026-06-14 20:47

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 8 -> 8 (+0 learned)
- Stored rule hits: 9
- Time: 3s
- Log: logs/learn_20260614_204749.log

---
## Learning Loop -- 2026-06-14 20:48

- Split: None, Tasks: 23
- Correct: 23 / 23 (100.0%)
- Rules: 8 -> 8 (+0 learned)
- Stored rule hits: 14
- Time: 8s
- Log: logs/learn_20260614_204753.log

## Iter 32 — 2026-06-14 — branch test33

**Diagnosis**: Training phase; probe 0/3 (c9680e90/878187ab/e5790162 are
conditional same-size transforms needing R4 machinery — not a smallest step).
Following iter-31's "next gap" note, the fractal / conditional self-tile family is
the next general capability: output is an `ih×iw` macro grid of `ih×iw` tiles where
macro-cell (R,C) is a copy of the input iff the input cell satisfies a condition.
A scan of all 1000 training tasks found **exactly two** pure fractal self-tiles
sharing one skeleton (`007bbfb7` 3×3→9×9, `5b6cbef5` 4×4→16×16, both "copy where
non-background") — a textbook R3/R5 generalization target the synthesizer could not
express (the §2.5-2b "fill the AU hole with a selector grounded in the
cell↔background comparison" case).

**Change**:
- `program/synthesis.py` — added a `fractal` step to `run_program` (makes the
  `ih²×iw²` canvas via `make_grid`, then for each macro-cell whose input cell
  satisfies a searched condition paints a full copy of the input via per-cell
  `coloring` — a value-agnostic composition of ONLY the two frozen primitives,
  F3-safe, same discipline as `dihedral`/`scale`). Added a `_FRACTAL_CONDS`
  searched condition vocabulary (`nonbg` / `isbg` — cell vs background; a
  *selection/recognition* predicate, not a transformation, so it lives in
  `program/`, not `DSL/`). Added Schema 7 + `_is_fractal_dims(pairs)` gate: yields
  one candidate per condition; `synthesize_task` keeps the first that reproduces
  every pair (same select-by-search as the dihedral maps). Its
  `[("fractal", ("const", ?v))]` skeleton lets two fractal tasks with divergent
  conditions lift via `unify()` into one covers>1 rule.
- `procedural_memory/rule_008.json` (new) — learned from `007bbfb7`; `5b6cbef5`
  then **reused it via the stored fast path** (R5 — a structurally different grid
  size, 4×4 vs 3×3, same general rule) and was folded into `covers=2`. Identical
  programs → plain covers-merge, null `anti_unification_trace` (same sanctioned
  path as rule_001's constant-output merge — trace is required only when AU
  actually lifts divergent leaves). All 3 example+test inputs of both tasks solve.
- `tests/test_synthesis.py` — +3 fractal tests (self-tile discovery + held-out
  transfer, declines on non-square macro dims, two conditions share one skeleton).
  180 pass.

**Probe before**: training 0/3; easy_a 9/9, madeup 23/23; 7 rules, P1=P2=5.429,
P3=0.857.
**Probe after** : easy_a 9/9, madeup 23/23 (guards unchanged); 8 rules; new
rule_008 covers=2 (2 real ARC-AGI-2 fractal tasks now solve via ONE general rule,
the 2nd via stored-rule reuse). P1/P2 5.429→5.0, P3 0.857→0.75.

**Invariants**: forbidden=none (check_invariants exit 2, no F-hit). positives=
NEUTRAL — the documented saturation/blindspot artifact (memory:
psignal_saturation_arithmetic, reuse_signal_blindspot): a covers=2 rule lowers the
*mean* covers against high-covers incumbents (rule_002=20), and P3 dips because an
identical-program merge legitimately carries no AU trace. No P-signal measures the
real wins here — absolute training-solved +2 with only +1 rule (the efficient
direction §2.5-4) and R5 reuse firing across a structurally different task. No new
`_try_*`/`_apply_*`; no new DSL primitive (fractal is a coordinate/selection
expression composing the two frozen primitives, discovered by SEARCH); no
`active_operators.py` edit (F8 N/A).

**Next gap (note for future iter)**: the 15 remaining fractal-dim tasks
(`0692e18c`, `27f8ce4f`, `cce03e0d`, …) use *recolored* or *positionally-keyed*
tiles (the tile is not a plain input copy — it is recolored, or placement is keyed
on a property other than non-background). Extending the fractal schema's tile from
"plain copy" to "copy-with-a-fitted-recolour", and its condition from cell-vs-bg to
a searched cell-value match, would fold several of those into the same family — but
verify each is genuinely the same skeleton first, not a new accreted special case.

## Iter 32 [NEUTRAL] — 20260614_204107 — branch test33
- Probe: [20:41:25] Correct:     0 / 3  (0.0%)

---
## Learning Loop -- 2026-06-14 20:49

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 8 -> 8 (+0 learned)
- Stored rule hits: 9
- Time: 3s
- Log: logs/learn_20260614_204949.log

---
## Learning Loop -- 2026-06-14 20:50

- Split: None, Tasks: 23
- Correct: 23 / 23 (100.0%)
- Rules: 8 -> 8 (+0 learned)
- Stored rule hits: 14
- Time: 8s
- Log: logs/learn_20260614_204952.log

---
## Learning Loop -- 2026-06-14 20:50

- Split: training, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 8 -> 8 (+0 learned)
- Stored rule hits: 0
- Time: 13s
- Log: logs/learn_20260614_205001.log

---
## Learning Loop -- 2026-06-14 20:56

- Split: None, Tasks: 7
- Correct: 6 / 7 (85.7%)
- Rules: 8 -> 8 (+0 learned)
- Stored rule hits: 1
- Time: 15s
- Log: logs/learn_20260614_205559.log

---
## Learning Loop -- 2026-06-14 20:56

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 8 -> 8 (+0 learned)
- Stored rule hits: 9
- Time: 3s
- Log: logs/learn_20260614_205644.log

---
## Learning Loop -- 2026-06-14 20:56

- Split: None, Tasks: 23
- Correct: 23 / 23 (100.0%)
- Rules: 8 -> 8 (+0 learned)
- Stored rule hits: 14
- Time: 8s
- Log: logs/learn_20260614_205647.log

## Iter 33 — 2026-06-14 — branch test33

**Diagnosis**: Training phase; probe 0/3 (c9680e90/878187ab/e5790162 = conditional
same-size transforms needing R4, not a smallest step). Following iter-32's "next
gap" note: a 1000-task scan found 17 fractal-dim (output (ih²,iw²)) tasks, but the
fractal schema only expressed `nonbg`/`isbg` (copy-where-cell-vs-background) and so
solved just 3. The dominant unsolved sub-family is **frequency-keyed** self-tiles:
copy the tile where the cell holds the grid's distinguished colour — and that
distinguished colour *varies per grid* (so it is value-agnostic, never a literal),
exactly the §2.5-2b "fill the AU hole with a comparison-grounded selector" case.

**Change**:
- `program/synthesis.py` — broadened the fractal selection vocabulary
  `_FRACTAL_CONDS` from 2 to 5 value-agnostic predicates: `most`/`least` (copy
  where the cell is the *unique* most-/least-frequent NON-background colour of
  this grid, via new `_distinguished_color`/`_color_eq` helpers — declines on a
  tie/absent extreme rather than guessing) and `all` (unconditional self-tile).
  Restructured each entry into a *predicate maker* `(grid, bg) -> (v->bool)|None`
  so the fractal step resolves the per-grid distinguished colour and declines
  cleanly when it does not resolve. `nonbg`/`isbg` behaviour byte-identical. NO new
  DSL primitive (a coordinate/selection expression composing the two frozen
  primitives, F3-safe), NO `_try_*` (F2-safe), NO `active_operators.py` edit
  (F8 N/A — all in `program/`).
- `procedural_memory/rule_008.json` — **regenerated by folding 5 real ARC-AGI-2
  fractal tasks** into the existing covers=2 fractal rule (27f8ce4f/c3e719e8/
  ad7e01d0 "most", 48f8583b "least", ccd554ac "all"). Their conditions diverge from
  the stored `nonbg`, so `save_rule` calls `unify()` → the condition leaf lifts to
  `?v` and an `anti_unification_trace` is written (was null). covers 2→7, one
  general rule, no accretion (rules 8→8). 6/7 reproduce held-out test too; ad7e01d0
  is train-consistent but its test has a frequency tie (its `most` hypothesis is
  underdetermined by its train — the normal ARC situation; covers is a
  train-reproduction relation, so it legitimately folds).
- `tests/test_synthesis.py` (+4) — `most`/`least`/`all` discovered by search +
  all share rule_008's one skeleton (so they lift, not accrete). 184 pass.

**Probe before**: training 0/3; easy_a 9/9, madeup 23/23; 8 rules; P1=P2=5.0,
P3=0.75; solved=40.
**Probe after** : easy_a 9/9, madeup 23/23 (guards unchanged, no new rules); 8
rules; rule_008 covers 2→7 (5 more real ARC-AGI-2 fractal tasks solve via ONE
general frequency-keyed rule); solved=45; P1/P2 5.0→5.625, P3 0.75→0.875.

**Invariants**: forbidden=none (check_invariants CLEAN). positives = **P1 +0.625,
P2 +0.625, P3 +0.125 — all three rise together** (the §2.5-4 real-progress
signature, opposite of the iter28/29/32 saturation dip: covers grew by 5 AND the
identical-program merge became a divergent-leaf AU lift, so the rule gained a
trace). P4/P5/P6 held.

**Next gap (note for future iter)**: 2 fractal-dim tasks remain genuinely outside
this vocab — `cce03e0d` (copy where cell == a *constant* colour, not a
frequency/bg selector — a literal that would only generalize if a sibling lifts it)
and `15696249` (the marker colour is named by neither frequency nor bg — likely a
positional/structural selector). The larger standing miss is unchanged: same-size
CONDITIONAL transforms (gravity/ray/occlusion — the probe's 3) need a
neighbourhood/alignment selector no schema yet expresses (R4-adjacent machinery).

## Iter 33 [CLEAN] — 20260614_204949 — branch test33
- Probe: [20:50:14] Correct:     0 / 3  (0.0%)

---
## Learning Loop -- 2026-06-14 21:00

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 8 -> 8 (+0 learned)
- Stored rule hits: 9
- Time: 3s
- Log: logs/learn_20260614_210050.log

---
## Learning Loop -- 2026-06-14 21:01

- Split: None, Tasks: 23
- Correct: 23 / 23 (100.0%)
- Rules: 8 -> 8 (+0 learned)
- Stored rule hits: 14
- Time: 8s
- Log: logs/learn_20260614_210054.log

---
## Learning Loop -- 2026-06-14 21:01

- Split: training, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 8 -> 8 (+0 learned)
- Stored rule hits: 0
- Time: 5s
- Log: logs/learn_20260614_210103.log

---
## Learning Loop -- 2026-06-14 21:06

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 8 -> 8 (+0 learned)
- Stored rule hits: 9
- Time: 3s
- Log: logs/learn_20260614_210625.log

---
## Learning Loop -- 2026-06-14 21:06

- Split: None, Tasks: 23
- Correct: 23 / 23 (100.0%)
- Rules: 8 -> 8 (+0 learned)
- Stored rule hits: 14
- Time: 8s
- Log: logs/learn_20260614_210628.log

---
## Learning Loop -- 2026-06-14 21:09

- Split: None, Tasks: 21
- Correct: 21 / 21 (100.0%)
- Rules: 8 -> 9 (+1 learned)
- Stored rule hits: 0
- Time: 16s
- Log: logs/learn_20260614_210851.log

---
## Learning Loop -- 2026-06-14 21:09

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 9 -> 9 (+0 learned)
- Stored rule hits: 9
- Time: 3s
- Log: logs/learn_20260614_210934.log

---
## Learning Loop -- 2026-06-14 21:09

- Split: None, Tasks: 23
- Correct: 23 / 23 (100.0%)
- Rules: 9 -> 9 (+0 learned)
- Stored rule hits: 14
- Time: 8s
- Log: logs/learn_20260614_210938.log

## Iter 34 — 2026-06-14 — branch test33

**Diagnosis**: Training phase; probe 0/3 (same-size conditional transforms — R4
machinery, not a smallest step). A full 1000-task scan showed the synthesizer
solves only 23 and that the single largest *unsolved, currently-expressible*
family is **dihedral tiling**: 43 tasks whose output is a `k×m` macro grid of
input-dim blocks, of which 21 are exactly a rigid (identity/mirror/rotate)
arrangement of input copies (0c786b71/46442a0e/7fe24cdd kaleidoscope family, …).
This is value-agnostic (a positional arrangement, never a colour), composes only
the two frozen primitives, and many tasks share one skeleton — the textbook §2.5
lift case, not accretion.

**Change**:
- `program/synthesis.py` — added **Schema 8: dihedral tiling**. New `_dihedral_grid`
  helper (identity + the 7 `_DIHEDRAL` maps, returns a transformed grid),
  `_fit_tile` fitter (resolves the shared `(k,m)` factor pair and the per-block
  transform *directly* — 8 transforms/block intersected across pairs, a fit, NOT
  an `8^(k·m)` enumeration; declines when no consistent arrangement exists), and a
  `tile` step in `run_program` that makes the `k·ih × m·iw` canvas (`make_grid`)
  and paints each block's transformed cells in their own input colour (`coloring`).
  Pure positional coordinate expression composing the two frozen primitives
  (§2.5-1, F3-safe); yielded LAST so simpler schemas (scale/fractal) win on
  overlap. NO new DSL primitive (F3-safe), NO `_try_*` (F2-safe), NO
  `active_operators.py` edit (F8 N/A — all in `program/`).
- `procedural_memory/rule_009.json` — **created by folding all 21 real ARC-AGI-2
  tiling tasks into ONE rule** (ran the agent's slow path on them; each discovers a
  `[("tile", k, m, pattern)]` program, all share the collapsed-const skeleton, so
  `save_rule`→`unify()` lifts the divergent `(k,m,pattern)` leaves to `?v` and
  writes an `anti_unification_trace`). covers=21, one general value-agnostic rule,
  no accretion (rules 8→9 for 21 solved tasks).
- `tests/test_synthesis.py` (+4) — plain replication (non-fractal dims), mirror
  kaleidoscope arrangement, declines-on-non-multiple, and the lift proof (two
  divergent arrangements share one skeleton). 188 pass.

**Probe before**: training probe 0/3; easy_a 9/9, madeup 23/23; 8 rules;
P1=P2=5.625, P3=0.875; solved≈45.
**Probe after** : easy_a 9/9, madeup 23/23 (guards unchanged); 9 rules; rule_009
covers=21 (21 more real ARC-AGI-2 tiling tasks solve via ONE general dihedral-tile
rule); P1/P2 5.625→7.333, P3 0.875→0.889.

**Invariants**: forbidden=none (check_invariants CLEAN). positives = **P1 +1.708,
P2 +1.708, P3 +0.014 — all three rise together** (the §2.5-4 real-progress
signature: covers grew by 21 via a genuine divergent-leaf AU lift, not 21 files).
P4/P5/P6 held.

**Next gap (note for future iter)**: 22 more `k×m`-dim tasks remain that are NOT
pure dihedral arrangements — their blocks are *content-conditional* (a block is the
input only where some object/colour predicate holds, or each block recolours), a
fractal-style per-block selector the tile schema does not yet express. The
standing miss is unchanged: same-size CONDITIONAL transforms (gravity/ray/
occlusion — the probe's 3) need a neighbourhood/alignment selector (R4-adjacent).

## Iter 34 [CLEAN] — 20260614_210050 — branch test33
- Probe: [21:01:08] Correct:     0 / 3  (0.0%)

---
## Learning Loop -- 2026-06-14 21:10

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 9 -> 9 (+0 learned)
- Stored rule hits: 9
- Time: 3s
- Log: logs/learn_20260614_211056.log

---
## Learning Loop -- 2026-06-14 21:11

- Split: None, Tasks: 23
- Correct: 23 / 23 (100.0%)
- Rules: 9 -> 9 (+0 learned)
- Stored rule hits: 14
- Time: 8s
- Log: logs/learn_20260614_211059.log

---
## Learning Loop -- 2026-06-14 21:11

- Split: training, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 9 -> 9 (+0 learned)
- Stored rule hits: 0
- Time: 5s
- Log: logs/learn_20260614_211108.log

---
## Learning Loop -- 2026-06-14 21:21

- Split: None, Tasks: 3
- Correct: 3 / 3 (100.0%)
- Rules: 9 -> 10 (+1 learned)
- Stored rule hits: 0
- Time: 4s
- Log: logs/learn_20260614_212146.log

---
## Learning Loop -- 2026-06-14 21:22

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 10 -> 10 (+0 learned)
- Stored rule hits: 9
- Time: 3s
- Log: logs/learn_20260614_212201.log

---
## Learning Loop -- 2026-06-14 21:22

- Split: None, Tasks: 23
- Correct: 23 / 23 (100.0%)
- Rules: 10 -> 10 (+0 learned)
- Stored rule hits: 14
- Time: 8s
- Log: logs/learn_20260614_212204.log

## Iter 35 — 2026-06-14 — branch test33

**Diagnosis**: Training phase; probe 0/3 (same-size conditional transforms — R4
neighbourhood machinery, deferred). Iter 34's "next gap" (22 leftover k×m-dim
tasks) turns out to be a *grab-bag*, not a family (verified: only 2 are even
self-tile-shaped, and those two use disjoint gates — chasing them = accretion,
forbidden). Scanning instead for a *coherent, value-agnostic, general* unsolved
family surfaced **symmetry completion**: same-dims output = the input with its
background holes restored from the grid's own dihedral symmetry (496994bd /
9ddd00f0 / 5751f35e). This is the textbook §2.5 case — the *reason* (P3/P4) is a
COMM ("the visible part obeys symmetry set S"), it composes only the two frozen
primitives, and three tasks with divergent S lift into one rule.

**Change**:
- `program/synthesis.py` — added **Schema 9: symmetry completion**. New
  `_consistent_syms` (the dihedral transforms the visible non-bg cells already
  obey — derived from the grid, never a literal), `_symfill_grid` (fill each bg
  hole from the first consistent image holding a non-bg value there), `_fit_symfill`
  fitter (task symmetry set = intersection of per-pair consistent sets; accepted
  only if it reproduces every pair *and* changes something), and a `symfill` step
  in `run_program` that copies the input and paints each resolved hole in its
  counterpart's own colour (`coloring`). Value-agnostic positional/colour
  expression composing only the two frozen primitives (§2.5-1, F3-safe); yielded
  LAST so simpler same-dims schemas (identity, colour-map) win on overlap. NO new
  DSL primitive (F3), NO `_try_*` (F2), NO `active_operators.py` edit (F8 N/A —
  all in `program/`).
- `procedural_memory/rule_010.json` — created by running the agent's slow path on
  the 3 tasks; each discovers `[("symfill", ("const", S))]`, they share the
  collapsed-const skeleton, so `save_rule`→`unify()` lifts the divergent symmetry
  sets to `?v2` and writes an `anti_unification_trace`. covers=3, ONE general
  value-agnostic rule, no accretion (rules 9→10 for 3 solved tasks). Held-out
  *test* grids of all three reproduce correctly — evidence the mechanism is
  general, not train-overfit.
- `tests/test_synthesis.py` (+3) — vertical-mirror hole restore (+ P5 transfer),
  declines-when-not-a-completion, and the lift proof (two divergent symmetry sets
  share one skeleton). 191 pass.

**Probe before**: training probe 0/3; easy_a 9/9, madeup 23/23; 9 rules;
P1=P2=7.333, P3=0.889; solved≈48.
**Probe after** : easy_a 9/9, madeup 23/23 (guards unchanged); 10 rules; rule_010
covers=3 (3 more real ARC-AGI-2 symmetry-completion tasks via ONE general rule);
P3 0.889→0.900.

**Invariants**: forbidden=none (check_invariants CLEAN, exit 0). positives =
**P3 +0.011** (a genuine divergent-leaf AU lift: symmetry set carried as `?v`).
P1/P2 dipped −0.43 — the documented *instrumentation trap* (memory
test33_rung_progress): a covers=3 family lowers the average in a pool dominated by
rule_009 (covers=21), even though it is real general capability. P4/P5/P6 held.

**Next gap (note for future iter)**: the standing miss is unchanged — same-size
CONDITIONAL transforms (the probe's gravity/ray/occlusion 3) need a
neighbourhood/alignment selector (R4-adjacent: edge-of-edge / per-cell
neighbour predicates), the first genuinely new *recognition* vocabulary (would
move P5) rather than another positional macro-grid schema.

## Iter 35 [CLEAN] — 20260614_211055 — branch test33
- Probe: [21:11:13] Correct:     0 / 3  (0.0%)

---
## Learning Loop -- 2026-06-14 21:23

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 10 -> 10 (+0 learned)
- Stored rule hits: 9
- Time: 3s
- Log: logs/learn_20260614_212341.log

---
## Learning Loop -- 2026-06-14 21:23

- Split: None, Tasks: 23
- Correct: 23 / 23 (100.0%)
- Rules: 10 -> 10 (+0 learned)
- Stored rule hits: 14
- Time: 8s
- Log: logs/learn_20260614_212344.log

---
## Learning Loop -- 2026-06-14 21:23

- Split: training, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 10 -> 10 (+0 learned)
- Stored rule hits: 0
- Time: 6s
- Log: logs/learn_20260614_212353.log

---
## Learning Loop -- 2026-06-14 21:44

- Split: None, Tasks: 23
- Correct: 23 / 23 (100.0%)
- Rules: 9 -> 9 (+0 learned)
- Stored rule hits: 14
- Time: 9s
- Log: logs/learn_20260614_214420.log

---
## Learning Loop -- 2026-06-14 21:44

- Split: None, Tasks: 1
- Correct: 1 / 1 (100.0%)
- Rules: 9 -> 9 (+0 learned)
- Stored rule hits: 0
- Time: 0s
- Log: logs/learn_20260614_214429.log

---
## Learning Loop -- 2026-06-14 21:47

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 10 -> 10 (+0 learned)
- Stored rule hits: 9
- Time: 3s
- Log: logs/learn_20260614_214737.log

---
## Learning Loop -- 2026-06-14 21:47

- Split: None, Tasks: 23
- Correct: 23 / 23 (100.0%)
- Rules: 10 -> 10 (+0 learned)
- Stored rule hits: 14
- Time: 9s
- Log: logs/learn_20260614_214741.log

---
## Learning Loop -- 2026-06-14 21:47

- Split: None, Tasks: 1
- Correct: 1 / 1 (100.0%)
- Rules: 10 -> 10 (+0 learned)
- Stored rule hits: 0
- Time: 0s
- Log: logs/learn_20260614_214750.log

## Iter 36 — 2026-06-14 — branch test33

**Diagnosis**: Training phase. A broad 180-task training sweep (seed 7) surfaced
the real gap behind a covers=1 mint: the synthesizer's colour-substitution schema
(Schema 4) emitted **one `coloring` step per changed colour**, so two colour-map
tasks that change a *different number* of colours get *different program
skeletons* (`[coloring]` vs `[coloring,coloring]`) and can never lift together.
Result: each changed-colour arity fragments into its own covers=1 family —
training task `b1948b0a` (single 6→2 map) was minting a fresh rule beside the
existing 2-colour `rule_005`. That is the §2.5-3/4 arity-keyed accretion (the
168-rule failure mode), and Schema 4 was the lone synthesizer schema *not* using
the one-step-with-one-const-leaf shape that `tile`/`fractal`/`symfill` all use.

**Change**:
- `program/synthesis.py` — collapsed Schema 4 to a single **`recolor_map`** step
  carrying the whole colour map as ONE const leaf (a tuple of `(from,to)` pairs).
  Added the `recolor_map` branch to `run_program` (composes ONLY the frozen
  `coloring` primitive — one `coloring` per pair, each selecting the *fixed*
  input's cells of that colour, so a source==target colour never cascades and the
  program transfers to the test input, P5). `_fit_color_map` now returns the
  single-step form. No new DSL primitive (F3), no `_try_*` (F2), no
  `active_operators.py` edit (F8 N/A — all in `program/`).
- `procedural_memory/rule_005.json` — migrated in place to the `recolor_map`
  abstract form (`[["recolor_map",["const",[["?v5","?v6"],["?v7","?v8"]]]]]`) with
  a freshly-written AU trace (`au_003.json`), then folded the real training task
  `b1948b0a` (a 1-colour map) into it via the sanctioned `save_rule` path —
  covers 2→**3**, *across changed-colour arity*, in ONE rule (the whole point).
  Kept rule_005's number deliberately: I found a latent `save_rule_to_ltm`
  numbering bug (`next_id = len(existing)+1` clobbers a higher-numbered file when
  a lower one was deleted — deleting rule_005 silently overwrote the symfill
  rule_010). Not this iter's target; avoided by migrating in place, noted here.
- `tests/test_synthesis_colormap.py` — updated assertions to the single-step form
  and added `test_recolor_map_of_different_arity_share_one_skeleton` +
  arity-crossing fold test (1-colour + two 2-colour → one covers=3 rule). 192 pass.

**Probe before**: training probe 0/3; easy_a 9/9, madeup 23/23; 10 rules; P1=6.9,
P2=6.9, P3=0.9; solved=69.
**Probe after** : easy_a 9/9, madeup 23/23 (guards unchanged); 10 rules (no new
file); rule_005 covers 2→3 (real ARC-AGI-2 task `b1948b0a` folded in, not minted
as a fresh covers=1 rule); P1 6.9→**7.0**, P2 6.9→**7.0**, P3 0.9 held.

**Invariants**: forbidden=none (check_invariants CLEAN, exit 0). positives =
**P1 +0.1, P2 +0.1** — and, structurally, the colour-map family can no longer
fragment by arity: every future colour-substitution task of any changed-colour
count now folds into this one rule instead of minting covers=1 rules.

**Next gap (note for future iter)**: same-size *conditional* transforms remain the
standing miss (probe's gravity/ray/occlusion: c9680e90 / e5790162 / 878187ab) —
each needs a per-cell neighbourhood/projection selector (the first genuinely new
*recognition* vocabulary, would move P5), not another whole-grid macro schema.
Also worth a cheap fix: the `save_rule_to_ltm` `len+1` id collision on a deleted
rule.

## Iter 36 [CLEAN] — 20260614_212340 — branch test33
- Probe: [21:23:58] Correct:     0 / 3  (0.0%)

---
## Learning Loop -- 2026-06-14 21:50

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 10 -> 10 (+0 learned)
- Stored rule hits: 9
- Time: 3s
- Log: logs/learn_20260614_215040.log

---
## Learning Loop -- 2026-06-14 21:50

- Split: None, Tasks: 23
- Correct: 23 / 23 (100.0%)
- Rules: 10 -> 10 (+0 learned)
- Stored rule hits: 14
- Time: 8s
- Log: logs/learn_20260614_215043.log

---
## Learning Loop -- 2026-06-14 21:50

- Split: training, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 10 -> 10 (+0 learned)
- Stored rule hits: 0
- Time: 6s
- Log: logs/learn_20260614_215052.log

---
## Learning Loop -- 2026-06-14 21:55

- Split: None, Tasks: 24
- Correct: 24 / 24 (100.0%)
- Rules: 10 -> 10 (+0 learned)
- Stored rule hits: 15
- Time: 9s
- Log: logs/learn_20260614_215451.log

---
## Learning Loop -- 2026-06-14 21:55

- Split: None, Tasks: 24
- Correct: 24 / 24 (100.0%)
- Rules: 10 -> 10 (+0 learned)
- Stored rule hits: 15
- Time: 9s
- Log: logs/learn_20260614_215503.log

---
## Learning Loop -- 2026-06-14 21:56

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 10 -> 10 (+0 learned)
- Stored rule hits: 9
- Time: 3s
- Log: logs/learn_20260614_215615.log

---
## Learning Loop -- 2026-06-14 21:56

- Split: None, Tasks: 24
- Correct: 24 / 24 (100.0%)
- Rules: 10 -> 10 (+0 learned)
- Stored rule hits: 15
- Time: 9s
- Log: logs/learn_20260614_215618.log

## Iter 37 — 2026-06-14 — branch test33

**Diagnosis**: Training phase; probe's 3 sampled tasks are all hard same-size
*conditional* transforms (diagonal gravity-with-obstacles c9680e90, ray
projection e5790162/878187ab) — no *small* gap there. The standing nameable gap
in the object-motion family was the absence of the canonical **gravity / fall**
target: an object sliding flush against one grid *edge* along a single axis
(keeping its free coordinate). `fit_target` had `bottom_right` (corner, both
axes), `offset`, `constant`, `to_anchor` — but no single-axis edge attraction, so
a task where objects fall from varying rows to the bottom edge keeping their
column was unsolved (defeats bottom_right/offset/constant; no anchor object).

**Change**:
- `agent/dsl_expr/motion.py` — added the `to_edge` target *expression* (the §2.5
  argument-vocabulary growth, in `agent/`, NOT the frozen DSL — no F3). `fit_target`
  now fits `{"kind":"to_edge","edge":bottom|top|left|right}` when every pair's dst
  is flush against that edge with the free coordinate kept; tried after the
  structural corner/translation/constant readings and before relational
  `to_anchor`, with an `any(...moved)` guard so a static set is never claimed a
  fall. `target_position` resolves the four edges. Fully contained in motion.py —
  no `active_operators.py` edit (F8 N/A), no `_try_*` (F2), no new transformation
  primitive (F3).
- `data/ARC_madeup/mo_gravity_bottom.json` — authored the minimal task that
  exposes the gap (single 2×2 object, varying start row+col, falls to bottom edge
  keeping column; the §2.2.2 sanctioned escalation when a training probe yields no
  small gap). It folds into the existing `object_motion` rule_002 via stored hit —
  **covers 20→21, no new rule minted** (the §2.5-3 win: a new capability lifts the
  family's coverage instead of accreting a covers=1 detector).
- `tests/test_object_motion.py` — 5 new tests for to_edge (four edges, corner
  precedence, static-decline, round-trip). 197 pass.

**Probe before**: training 0/3; easy_a 9/9, madeup 23/23; 10 rules; rule_002
covers 20; P1=7.0, P2=7.0.
**Probe after** : easy_a 9/9, madeup **24/24** (gravity task added & solved via
object_motion); 10 rules (no new file); rule_002 covers 20→**21**; P1 7.0→**7.1**,
P2 7.0→**7.1**.

**Invariants**: forbidden=none (check_invariants CLEAN, exit 0). positives=**P1
+0.1, P2 +0.1**; the object-motion family now expresses single-axis edge gravity
value-agnostically (re-fitted per task, never stored as a literal).

**Next gap (note for future iter)**: edge-gravity is still *single-object* (the
fast path selects one object). The probe's real misses (c9680e90/e5790162) are
*multi-object* gravity/ray — each object independently mapped — which needs the
place_object machinery generalized from select-one to map-all (a multi-object
apply), the genuinely new structural step. Also still open: the latent
`save_rule_to_ltm` `len+1` id-collision on a deleted rule (iter-36 note).

## Iter 37 [CLEAN] — 20260614_215039 — branch test33
- Probe: [21:50:57] Correct:     0 / 3  (0.0%)

---
## Learning Loop -- 2026-06-14 21:57

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 10 -> 10 (+0 learned)
- Stored rule hits: 9
- Time: 3s
- Log: logs/learn_20260614_215747.log

---
## Learning Loop -- 2026-06-14 21:58

- Split: None, Tasks: 24
- Correct: 24 / 24 (100.0%)
- Rules: 10 -> 10 (+0 learned)
- Stored rule hits: 15
- Time: 9s
- Log: logs/learn_20260614_215751.log

---
## Learning Loop -- 2026-06-14 21:58

- Split: training, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 10 -> 10 (+0 learned)
- Stored rule hits: 0
- Time: 6s
- Log: logs/learn_20260614_215800.log

---
## Learning Loop -- 2026-06-14 22:05

- Split: None, Tasks: 25
- Correct: 25 / 25 (100.0%)
- Rules: 10 -> 10 (+0 learned)
- Stored rule hits: 15
- Time: 9s
- Log: logs/learn_20260614_220513.log

---
## Learning Loop -- 2026-06-14 22:05

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 10 -> 10 (+0 learned)
- Stored rule hits: 9
- Time: 3s
- Log: logs/learn_20260614_220541.log

---
## Learning Loop -- 2026-06-14 22:05

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 10 -> 10 (+0 learned)
- Stored rule hits: 9
- Time: 3s
- Log: logs/learn_20260614_220549.log

---
## Learning Loop -- 2026-06-14 22:09

- Split: training, Tasks: 20
- Correct: 2 / 20 (10.0%)
- Rules: 10 -> 10 (+0 learned)
- Stored rule hits: 0
- Time: 59s
- Log: logs/learn_20260614_220804.log

## Iter 38 — 2026-06-14 — branch test33

**Diagnosis**: Training phase; the 3 sampled tasks (c9680e90 diagonal
gravity-with-obstacles, e5790162/878187ab ray projection) are all *multi-object*
conditional transforms — and the whole object-motion family was still
**select-one** (a fitted selector picks ONE object; others drop/preserve). The
canonical multi-object move — *gravity*, where **every** object falls by the same
per-object rule — had no path at all (iter-37's named "next gap": generalise
select-one → map-all). That is the smallest defensible structural step on the R1
frontier.

**Change**:
- `agent/dsl_expr/motion.py` — added `fit_uniform_target`: fits ONE *per-object*
  displacement target (`offset` or `to_edge`) that explains **every** object's
  move at once. Only the two displacement readings are admissible for map-all (the
  absolute `bottom_right`/`constant`/`to_anchor` collapse all objects onto one
  spot). Reuses the existing `target_position` resolver (already per-object).
- `agent/active_operators.py` — `ExtractPatternOperator._fit_map_all`: recognises a
  multi-object map-all scene (unique bijection by colour-set+size+shape, every
  object colour-preserved, ≥2 objects, one uniform target fits all), surfaced as
  `patterns["object_motion"]["map_all"]`, fully independent of the single-object
  analysis. Gated on ≥2 objects + "single-object analysis declined" so it never
  competes with the move family the select-one path already covers (zero
  regression). `PredictOperator._render_map_all_motion` applies the fitted target
  to *every* object via make_grid + coloring (the select-one→map-all generalisation
  of `_render_object_motion`). GeneralizeOperator records the map_all target as the
  same `place_object`/`target` action arg so a gravity task **folds into the move
  rule** (rule_002), and PredictOperator dispatches map-all rendering when no
  single-object selector fit.
- `agent/conditions/object_motion.py` — the matcher now also fires for the map_all
  case, *only* when the single-object fit declined (satisfies F8: active_operators
  edit accompanied by a conditions edit). No new condition.type (P5 unchanged) —
  map-all is the same `object_motion` recognition, generalised.
- `data/ARC_madeup/mo_gravity_multi.json` — authored the minimal task that exposes
  the gap (2–3 distinct-colour objects, varying rows/cols, all fall to the bottom
  edge keeping columns). It folds into rule_002 via the slow path — **covers 21→22,
  no new rule minted** (§2.5-3 win).
- `tests/test_object_motion.py` — 8 new tests (uniform-target fit/decline, map_all
  recognition + decline on single-object/ambiguous-bijection, render, end-to-end
  family membership, save_rule fold proving covers>1 with an au trace). 206 pass.

**Probe before**: training 0/3; easy_a 9/9, madeup 24/24; 10 rules; rule_002
covers 21; P1=7.1, P2=7.1.
**Probe after** : easy_a 9/9, madeup **25/25** (multi-object gravity added &
solved via object_motion); 10 rules (no new file); rule_002 covers 21→**22**;
P1 7.1→**7.2**, P2 7.1→**7.2**.

**Invariants**: forbidden=none (check_invariants CLEAN, exit 0). positives=**P1
+0.1, P2 +0.1**; the object-motion family now expresses multi-object map-all
gravity value-agnostically (re-fitted per task, never stored as a literal), folded
into the same rule as the single-object move family.

**Next gap (note for future iter)**: map-all gravity still requires an
*unambiguous* bijection (distinct colour+size+shape per object), so it declines on
*identical* objects falling (the common real case — needs column/axis matching to
say which object fell where). It is also pure displacement (offset/to_edge); the
probe's real misses (c9680e90/e5790162) add *obstacles/stacking* (an object stops
on another) and *rays* (objects grow), neither of which is a rigid translation —
those need a per-object stop-condition or a growth target, the next structural
steps.

## Iter 38 [CLEAN] — 20260614_215747 — branch test33
- Probe: [21:58:06] Correct:     0 / 3  (0.0%)

---
## Learning Loop -- 2026-06-14 22:10

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 10 -> 10 (+0 learned)
- Stored rule hits: 9
- Time: 3s
- Log: logs/learn_20260614_221048.log

---
## Learning Loop -- 2026-06-14 22:11

- Split: None, Tasks: 25
- Correct: 25 / 25 (100.0%)
- Rules: 10 -> 10 (+0 learned)
- Stored rule hits: 15
- Time: 9s
- Log: logs/learn_20260614_221052.log

---
## Learning Loop -- 2026-06-14 22:11

- Split: training, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 10 -> 10 (+0 learned)
- Stored rule hits: 0
- Time: 5s
- Log: logs/learn_20260614_221102.log

---
## Learning Loop -- 2026-06-14 22:17

- Split: None, Tasks: 26
- Correct: 26 / 26 (100.0%)
- Rules: 10 -> 10 (+0 learned)
- Stored rule hits: 15
- Time: 10s
- Log: logs/learn_20260614_221650.log

---
## Learning Loop -- 2026-06-14 22:17

- Split: None, Tasks: 26
- Correct: 26 / 26 (100.0%)
- Rules: 10 -> 10 (+0 learned)
- Stored rule hits: 15
- Time: 10s
- Log: logs/learn_20260614_221706.log

---
## Learning Loop -- 2026-06-14 22:17

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 10 -> 10 (+0 learned)
- Stored rule hits: 9
- Time: 3s
- Log: logs/learn_20260614_221715.log

---
## Learning Loop -- 2026-06-14 22:17

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 10 -> 10 (+0 learned)
- Stored rule hits: 9
- Time: 3s
- Log: logs/learn_20260614_221722.log

## Iter 39 — 2026-06-14 — branch test33

**Diagnosis**: Training phase. Iter-38 added multi-object map-all gravity but its
input→output bijection keyed only on (colour-set + size + shape), so it *declined*
on **identical** objects falling (the common gravity case) — it could not say which
fell where, the named "next gap". That is the smallest defensible structural step
on the R1 frontier: disambiguate the bijection by the coordinate a fall preserves.

**Change**:
- `agent/dsl_expr/selection.py` — new bijection vocabulary: `motion_bijection` +
  `MOTION_BIJECTION_STRATEGIES`. Strategies tried most-constrained-first:
  `identity` (colour+size+shape, the distinct-object case, unchanged) then the axis
  disambiguators `vertical` / `horizontal`, which add the column / row a fall keeps
  to the match key — so two *identical* objects in distinct columns (or rows) are
  matched by the coordinate gravity preserves. Value-agnostic (no literal index).
- `agent/dsl_expr/motion.py` — new `fit_map_all_target(per_pair)`: holds the
  strategy loop (bijection → colour-preservation check → `fit_uniform_target`),
  returning the first strategy whose motions fit ONE uniform target. `identity`
  still wins for distinct objects (zero regression); an axis strategy only claims an
  identical-object scene `identity` cannot resolve.
- `agent/active_operators.py` — `_fit_map_all` slimmed to gather per-pair objects
  (size-preserving, ≥2, equal-count) and delegate to `fit_map_all_target`. Net
  **−34 lines** (P6 ↑); the fitting logic now lives with the other `fit_*`
  functions in `motion.py`, so active_operators only gathers + calls.
- `agent/dsl_expr/__init__.py` — export `fit_map_all_target`.
- `data/ARC_madeup/mo_gravity_identical.json` — authored the minimal task that
  exposes the gap: two identical single-cell colour-5 objects in distinct columns,
  varying rows, all fall to the bottom edge. Solves via `object_motion` and **folds
  into rule_002** (covers 22→23, no new rule — §2.5-3 win).
- `tests/test_object_motion.py` — replaced the now-obsolete "declines ambiguous
  bijection" test (that case is now correctly resolved) with: resolves-identical-by-
  column, declines-stacked-identical (same column → still honestly declines, needs
  ordering), and three focused unit tests on `motion_bijection` / `fit_map_all_target`.
  210 pass.

**Probe before**: training 0/3; easy_a 9/9, madeup 25/25; 10 rules; rule_002
covers 22; P1=7.2, P2=7.2.
**Probe after** : easy_a 9/9, madeup **26/26**; 10 rules (no new file); rule_002
covers 22→**23**; P1 7.2→**7.3**, P2 7.2→**7.3**; P6 1467→**1433** (−34).

**Invariants**: forbidden=none (check_invariants CLEAN, exit 0). positives=**P1
+0.1, P2 +0.1, P6 −34 lines**. The map-all gravity family now resolves
identical-object falls value-agnostically (matched by the axis a fall preserves),
folded into the same move rule — no new detector, no new rule.

**Next gap (note for future iter)**: identical objects *stacked in the same column*
still decline (neither column nor row disambiguates — they need per-object fall
ordering / a stop-on-occupied rule, the gravity-with-stacking case). That is also
the heart of the probe's c9680e90 (gravity with obstacles): a falling object stops
on another rather than reaching the edge — a per-object stop-condition, the next
structural step on the motion frontier. The probe's e5790162/878187ab are ray
projection (objects *grow* toward a target), a separate non-rigid family.

## Iter 39 [CLEAN] — 20260614_221048 — branch test33
- Probe: [22:11:07] Correct:     0 / 3  (0.0%)

---
## Learning Loop -- 2026-06-14 22:20

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 10 -> 10 (+0 learned)
- Stored rule hits: 9
- Time: 3s
- Log: logs/learn_20260614_222039.log

---
## Learning Loop -- 2026-06-14 22:20

- Split: None, Tasks: 26
- Correct: 26 / 26 (100.0%)
- Rules: 10 -> 10 (+0 learned)
- Stored rule hits: 15
- Time: 10s
- Log: logs/learn_20260614_222043.log

---
## Learning Loop -- 2026-06-14 22:20

- Split: training, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 10 -> 10 (+0 learned)
- Stored rule hits: 0
- Time: 6s
- Log: logs/learn_20260614_222053.log

---
## Learning Loop -- 2026-06-14 22:28

- Split: None, Tasks: 27
- Correct: 27 / 27 (100.0%)
- Rules: 10 -> 10 (+0 learned)
- Stored rule hits: 15
- Time: 11s
- Log: logs/learn_20260614_222751.log

---
## Learning Loop -- 2026-06-14 22:29

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 10 -> 10 (+0 learned)
- Stored rule hits: 9
- Time: 3s
- Log: logs/learn_20260614_222933.log

---
## Learning Loop -- 2026-06-14 22:29

- Split: None, Tasks: 27
- Correct: 27 / 27 (100.0%)
- Rules: 10 -> 10 (+0 learned)
- Stored rule hits: 15
- Time: 10s
- Log: logs/learn_20260614_222936.log

## Iter 40 — 2026-06-14 — branch test33

**Diagnosis**: Training phase, R1 motion frontier. Iter-39's named next gap was the
*stacking* case: objects in one column that both fall toward an edge can't both reach
the floor — the map-all `to_edge` reading (each object resolves its destination
*independently*) cannot say the upper one rests on top of the lower. `fit_uniform_target`
honestly declined; the bijection path also breaks because a settled pile *merges*
distinct input objects into one output blob (unequal in/out object counts). This is
the smallest defensible structural step: a joint gravity-settle simulation that
pile-stacks — the collision generalisation of the independent fall.

**Change**:
- `agent/dsl_expr/motion.py` — new `simulate_gravity_settle(objs, H, W, edge)`:
  settles every object toward one edge, each sliding straight (free coordinate kept)
  until blocked by the grid or an already-settled cell; objects nearest the edge
  settle first (`_settle_order`), so stacking is deterministic. Returns per-object
  destinations aligned with input order. New `fit_gravity_settle(per_pair)`: for each
  edge, settles the inputs and checks the **coloured-cell map** reproduces every
  output exactly (cell-set match, not an object bijection — robust to the pile merging
  objects). New `map_all_destinations(...)`: the one resolver the renderer calls —
  per-object `target_position` for offset/to_edge, joint settle for `gravity_settle`.
  `fit_map_all_target` now falls back to `fit_gravity_settle` after the bijection
  strategies decline, so a plain (non-colliding) fall still reads as the simpler
  `to_edge` and gravity_settle only claims a genuine stacking scene (tried last,
  full reproduction-gated).
- `agent/active_operators.py` — `_fit_map_all` no longer requires equal in/out object
  counts (the settle fallback *wants* unequal counts; the bijection path declines on
  its own when they differ). `_render_map_all_motion` slimmed to call
  `map_all_destinations` once instead of looping `target_position`. Net **0 lines**
  (8/8) — no F8 trip, no `_try_*`.
- `agent/dsl_expr/__init__.py` — export the three new functions.
- `data/ARC_madeup/mo_gravity_stack.json` — authored the minimal stacking task (2–3
  single cells per column falling and piling at the bottom; in/out counts differ as
  cells merge). Solves via `object_motion` and **folds into rule_002** (no new rule —
  §2.5-3 win).
- `tests/test_object_motion.py` — the prior "declines stacked identical" test (whose
  own comment said stacking is "a later capability") now asserts it *resolves* via
  gravity_settle; added 5 focused unit tests (settle stacks a column, independent
  columns reach the floor, fit picks the unique edge, fit declines a non-gravity
  scene, end-to-end render round-trip). 215 pass.

**Probe before**: training 0/3; easy_a 9/9, madeup 26/26; 10 rules; rule_002
covers 24; P1=7.3, P2=7.3.
**Probe after** : easy_a 9/9, madeup **27/27**; 10 rules (no new file); rule_002
covers 24→**25**; P1 7.3→**7.4**, P2 7.3→**7.4**.

**Invariants**: forbidden=none (check_invariants CLEAN, exit 0). positives=**P1 +0.1,
P2 +0.1**; P6 net 0 (active_operators size unchanged). Map-all gravity now covers the
*stacking* case value-agnostically (joint settle matched on coloured cells), folded
into the same move rule — no new detector, no new rule.

**Next gap (note for future iter)**: gravity with a *barrier* — the probe's c9680e90
has a fixed 9-line that objects settle against from both sides (plus colour-specific
behaviour beyond rigid fall), which `simulate_gravity_settle` (edge only, no interior
obstacle) doesn't model. The probe's e5790162/878187ab are ray projection (objects
*grow* toward a target), a separate non-rigid family still unaddressed.
