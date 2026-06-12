# SOAR-ARC Session Log

---
## Iter 11 — 2026-06-12T13:44 — branch test31

**Diagnosis**: R0/R1/R3 cleared and iter 10 revived the Fast path, but the
lifted abstraction `rule_002` (place_object, `target_mode="?v1"`) still could
**not be reused** — `applicable_rule` deliberately skipped it because its
anti-unification hole was unfilled, so easy_a c–i fell to the Slow path every
run (Reused 2/9). This is the §2.5-2b gap named by iter 9 **and** iter 10: "an
AU product is incomplete until its variable is *filled* — by a *selection*
grounded in comparison, not invented." The smallest defensible step is to fill
the hole over the **bounded, already-known** filling domain {fixed, displacement,
corner} by example-reproduction — explicitly NOT inventing a new derive-expression
(that is the held open question Q-B3/Q-B4), so the rung stays on the defensible
side iter 10 vetted.

**Change**:
- `agent/variable_resolution.py` (new) — `resolve_variable(task, candidates,
  instantiate, render)`: selects the first candidate filling (priority-ordered,
  bounded domain) whose instantiated rule **reproduces every example output**.
  The choice is grounded in the example comparisons (P3/P4), never invented; a
  task supporting no candidate yields None (so the rule is *not* falsely reused).
  Selection vocabulary → lives under `agent/`, not `procedural_memory/DSL/`
  (§2.5-1, F3-safe). It does NOT invent a new filling — that's Q-B3/Q-B4.
- `agent/active_operators.py` — `_render_place_object` now fills an unresolved
  `target_mode="?vN"` hole via `resolve_variable` over `PLACE_OBJECT_FILLINGS`
  (order = slow-path build priority, so a self-applied abstraction and a freshly
  built concrete rule resolve identically) before rendering. `resolve_variable`
  invokes the render only with concrete modes → no recursion. New module helper
  `_with_target_mode` instantiates a candidate without mutating the stored rule.
  No new `_try_*`/`_apply_*`; net +51 lines (the resolution wiring), F8 companion
  = `agent/memory.py`.
- `agent/memory.py` — `applicable_rule` now *admits* a runtime-resolvable
  abstraction: a `?vN` hole listed in `_RUNTIME_RESOLVABLE` ({place_object:
  {target_mode}}) is filled at render time, so the rule passes the fast path with
  its dispatch type stamped (hole left in place — resolution stays at apply time,
  never baked into a per-task literal). Holes with no resolver still return None
  (slow path re-derives; the open-Q "invent a filling" case stays held).
- `agent/active_agent.py` — fast path now **prefers a concrete rule over a
  runtime-resolved abstraction** (stable sort on "has unresolved var"). Required:
  a constant-output task's examples are *also* consistent with "move the single
  object to a fixed cell" (genuine ambiguity), so without this the abstract
  place_object rule preempted `constant_output` and mispredicted the test
  (regressing seed-42 easy0001 1/3→0/3). Occam / P1: don't descend to the
  object-level filling when a grid-level rule already explains the task.
- `tests/test_variable_resolution.py` (new, 5) — resolver unit cases: picks the
  reproducing candidate; None when none reproduce; deterministic priority on a
  genuine tie; None on empty examples; ignores half-missing pairs.
- `tests/test_fast_path_reuse.py` — updated the two tests my change re-aimed
  (the abstract rule now *self-applies* instead of falling through), added a
  skip-test for a hole with no resolver and a no-false-reuse test (easy0005
  supports no filling → declines to Slow path). Suite 72→**79** pass.

**Probe before**: easy 1/3, easy_a 9/9 (**Reused 2**), full easy 6/16 (Reused 4);
rules=2 (covers 6+9); P1=7.5 P2=7.5 P3=0.5 P4=247 P5=5
**Probe after** : easy 1/3 (**no regression** — easy0001 still correct via
`constant_output`, 0002/0003 ill-posed → correct abstain), easy_a 9/9 (**Reused
2→9** — c–i now reuse the *abstract* `place_object` rule via `stored(easy000e)`,
the lifted abstraction self-applying across all three fillings), full easy 6/16
(**Reused 4→6**, correctness identical); rules=2 unchanged; P1–P5 unchanged.

**Invariants**: forbidden=**none** (F1/F2/F3 clean; F8 companion present —
active_operators +51 accompanied by memory.py). positives = all flat → verdict
**NEUTRAL** (checker exit 2). This is the INVARIANTS §3 case again: P1–P6 has
**no signal measuring reuse rate**, so making the AU-lifted abstraction
*self-applying* (its whole purpose) — observable only as easy_a Reused 2→9 —
scores neutral despite being the central §2.5-2b / R5 work. Correctness is
preserved everywhere (verified against a pristine-tree baseline before/after).

**RUNG R5 (variable-resolution half) — evidence**: per BACKLOG §5 (4 criteria):
(1) *works*: pipeline + fast path run error-free; easy_a 9/9. (2) *module
uniformity*: c–i are now reused through **one** abstract rule (covers=9) whose
single variable is filled by **one** selection mechanism — no per-task branch,
no per-filling rule; the {fixed, displacement, corner} fillings are *selected*,
not hand-dispatched. (3) *approaches answer*: predictions equal known outputs
exactly. (4) *search sanity*: bounded 3-candidate selection, deterministic.
R5's done-when ("stored-rule hit generalizes across *structurally different*
tasks, not literal reuse") is met for the move family — the abstraction reused
across three structural variants. The *other* R5 half (Q-B3 "invent a new
derive-expression", e.g. easy0007/0008 target==2·colour) remains held/surfaced,
untouched.

**Next gap (note for future iter)**: the abstraction now self-applies, so the
remaining functional easy failures (0007/0008/0010/0011/0015/0016) are the pure
**variable-origin invention** case (Q-B3/Q-B4) — out of bounded scope. Two
defensible non-open routes remain: (a) R4 — author a `data/ARC_madeup/` task
needing 2nd-order (edge-of-edge) compare, which would also move P5; or (b)
surface a *design proposal* for variable-origin resolution to the user (per
BACKLOG §5, do not silently invent). Also worth noting: no P-signal measures
reuse, so two reuse-enabling iters (10, 11) both read neutral — if the user wants
reuse rewarded, a P7 (stored-hit rate / covers-via-reuse) would capture it.

---
## Iter 8 — 2026-06-12 — branch test31

**Diagnosis**: easy_a stood at 8/9 — only easy000i remained, named by iter 7 as
the last R1 graduation member. It is the same top-left *corner* placement the
corner filling already handles, differing in exactly one thing: the output grid
**resizes** (6×6→5×5), which the size-preserving render path could not express
(`make_grid` copied the input dims). The smallest defensible step is to make
`make_grid`'s height/width an *argument expression* derived value-agnostically
from the examples (§2.5-1), so the existing corner filling — not a new one —
covers the resized member.

**Change**:
- `agent/dsl_expr/__init__.py` — new relation `output_dims(pair_dims,
  test_in_dims)`: derive the test output canvas size from how the example
  outputs relate to their inputs — *size-preserved* (out==in per pair → track the
  test input, handles size-varying easy000g) or *constant output size* (all
  outputs one size → that size, handles easy000i 6×6→5×5). None when neither
  relation holds (no guess). Read from COMM/DIFF of dims (P3/P4); argument
  material, so under `agent/`, not `procedural_memory/DSL/` (F3-safe, §2.5-1).
- `agent/active_operators.py` — (a) `_object_transition` surfaces
  `outsize_constant`/`outsize` (the COMM of example output dims) alongside
  `outsize_preserved`; (b) `_render_place_object` now derives the output canvas
  size via `output_dims` and uses it for `make_grid`, the bounds check, *and* the
  grid_dims passed to the corner target derivation — so a resized corner resolves
  against the *output* bounds. Size-preserved tasks derive their own input dims →
  behavior unchanged. The render skeleton (erase via fresh `make_grid`, paint at
  `f(target)` via `coloring`) is unchanged; only the *canvas dimensions* became a
  derived argument. No new `_try_*`/`_apply_*`.
- `agent/conditions/single_object_move_relative_corner.py` — relaxed the
  size-preservation guard from `outsize_preserved` to `outsize_preserved OR
  outsize_constant`. The corner is invariant against either reading of the
  output bounds, so the resize is the *same* corner filling — it folds into
  `place_object`'s `?v1` abstraction (covers grows, no new rule, §2.5-4). No new
  matcher (P5 unchanged); this is the F8 companion for the active_operators edit.
- `procedural_memory/rule_002.json` — the place_object abstraction's `covers`
  grew `[c,d,e,f,h,g] → [+i]` by subsumption (target_mode="corner", `?v1`). Rule
  count stays 2; trace unchanged. Not a new file — iter-6's AU machinery folded it.
- `tests/test_place_object.py` / `tests/test_place_object_corner.py` — converted
  the two now-stale "i is unsupported / declines" assertions into positive
  coverage (i fires the corner matcher via `outsize_constant`; renders the exact
  5×5 output end-to-end) + 3 `output_dims` unit cases (preserved / constant /
  undecidable). Suite 63/63 pass.

**Probe before**: easy 1/3, easy_a **8/9**; rules=2 (covers 6); P1=6.0, P2=6.0
**Probe after** : easy 1/3 (unchanged — easy0001 CORRECT; easy0002/0003 are
genuinely ambiguous, output not a deterministic function of input, correctly left
identity), easy_a **9/9** (a,b constant_output; c–i all one place_object
abstraction); rules=**2** (covers **7**); P1=**6.5**, P2=**6.5**

**Invariants**: forbidden=none (F8 companion present: conditions/ + dsl_expr/
edits). positives = **P1 +0.5, P2 +0.5** → verdict CLEAN. §2.5-4 litmus holds:
covers rose while rule *count* stayed 2 — generalization by subsumption, not
accretion. P5 flat (relaxed an existing matcher, did not add one). P6 −40
(active_operators grew by the outsize signal + dims derivation; allowed, F8
companion present). P3/P4 flat.

**RUNG R1 CLEARED** (BACKLOG_LOOP §5):
- (1) *works*: pipeline runs error-free; easy_a 9/9, easy000c–i all solved.
- (2) *module uniformity*: c–i are handled by **one** `place_object` rule
  (covers=7), the three fillings (fixed/displacement/corner) differing *only* in
  `action.args.target_mode` — the single R3 variable — with **no per-task
  branches**. The resize did not add a filling; it became a derived `make_grid`
  argument shared by all corner members.
- (3) *approaches answer*: predictions equal the known outputs exactly.
- (4) *search sanity*: deterministic, no brute force.
- Signals moved: easy_a 7/9→9/9 over iters 7–8; P1/P2 6.0→6.5; rule count held
  at 2 throughout. The easy_a graduation milestone (R1 done-when) is met.
- Next rung premise: R1's object-level analysis + the §2.5-2b selection/dimension
  vocabulary are now in place, so R2 (episodic-writer verification) / R4 (2nd-order
  relation) become the lowest unproven work.

**Next gap (note for future iter)**: R1 is cleared; re-diagnose to the next
lowest-unproven rung. P4 already reads 247 episodic entries, so R2's writer may
already be wired — verify it emits exactly one attempt folder per solve (the
BACKLOG R2 done-when) rather than assuming. The latent R5 issue persists
(unchanged since iter 4/6): the fast path reads `entry["rule"]`, absent in the
new schema, so abstractions are learned but not reused across runs — that is the
R5 (skill reuse) gap, not R1.

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
## Learning Loop -- 2026-06-12 11:38

- Split: None, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 0 -> 1 (+1 learned)
- Stored rule hits: 0
- Time: 1s
- Log: logs/learn_20260612_113815.log

---
## Learning Loop -- 2026-06-12 11:38

- Split: None, Tasks: 9
- Correct: 0 / 9 (0.0%)
- Rules: 1 -> 3 (+2 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260612_113817.log

---
## Learning Loop -- 2026-06-12 11:49

- Split: None, Tasks: 3
- Correct: 1 / 3 (33.3%)
- Rules: 0 -> 1 (+1 learned)
- Stored rule hits: 0
- Time: 2s
- Log: logs/learn_20260612_114907.log

---
## Learning Loop -- 2026-06-12 11:49

- Split: None, Tasks: 16
- Correct: 4 / 16 (25.0%)
- Rules: 1 -> 1 (+0 learned)
- Stored rule hits: 0
- Time: 8s
- Log: logs/learn_20260612_114908.log

---
## Learning Loop -- 2026-06-12 11:49

- Split: None, Tasks: 9
- Correct: 2 / 9 (22.2%)
- Rules: 1 -> 1 (+0 learned)
- Stored rule hits: 0
- Time: 4s
- Log: logs/learn_20260612_114916.log

---
## Learning Loop -- 2026-06-12 11:50

- Split: None, Tasks: 1
- Correct: 1 / 1 (100.0%)
- Rules: 1 -> 1 (+0 learned)
- Stored rule hits: 0
- Time: 1s
- Log: logs/learn_20260612_115042.log

---
## Iter 2 — 2026-06-12 — branch test31

**Diagnosis**: R0's recognition substrate existed (iter 1's `constant_output`
matcher) but **had no consumer** — `GeneralizeOperator` still ran the two
hand-coded color detectors (`_try_color_mapping`/`_try_recolor_sequential`),
which mis-solved the constant-output family (probe: easy0001 INCORRECT) and
saved condition-less `color_mapping` rules through the unvalidated
`save_rule_to_ltm` (F4-dirty dead memory — the probe kept regenerating
rule_001..003). The smallest defensible step that closes a *real* gap is to
wire the matcher end-to-end (recognition → make_grid/coloring action →
prediction → validated persistence) and **delete** the superseded detectors —
the exact "kill the hand-coded special case" the architecture wants.

**Change**:
- `procedural_memory/DSL/{make_grid,coloring,apply,__init__}.py` (new) — the two
  (and only two) frozen transformation primitives + `apply_DSL` dispatcher. R0
  substrate; explicitly allowed (PROMPT.md Step 3), F3-safe (only these two
  registered). Source had been stripped at the clean-start node (only stale
  pyc remained); now restored.
- `agent/memory.py` — add `RuleSchemaError`, `validate_rule()`, and `save_rule()`:
  the validated successor to `save_rule_to_ltm`, persisting `{condition, action}`
  rules and **deduplicating by (condition.type, action)** so one value-agnostic
  rule absorbs a whole family via a growing `covers` (not one rule per task).
  Marked as the single anti-unification call site (CLAUDE.md §8; AU lift is R3).
- `agent/active_operators.py` — `GeneralizeOperator` now consults the matcher
  registry (`match("constant_output", patterns)`) and emits the value-agnostic
  `copy_common_output` `{condition, action}` rule; `PredictOperator` renders it
  by replaying `make_grid ∘ coloring` over the COMM of the example outputs
  (P5: never the test pair's own G1). **Removed** the four hand-coded detector/
  applier methods (`_try_recolor_sequential`, `_check_sort_key`,
  `_try_color_mapping`, `_apply_recolor_sequential`, `_apply_color_mapping`,
  `_group_positions`) — net −95 lines (P6). No new `_try_*`/`_apply_*`; the
  existing `_apply_rule` def line is left byte-identical (F2-safe).
- `agent/active_agent.py` — route learning through `save_rule`; only persist a
  rule carrying `condition`+`action` (identity / condition-less results are no
  longer written → the F4-dirty regeneration is fixed at the source).
- `procedural_memory/rule_001..003.json` (deleted) — schema-invalid dead memory.

**Probe before**: easy 0/3, easy_a 0/9; rules=3 (all condition-less); P1=1.33
**Probe after** : easy0001 CORRECT (the family the intended way); easy000a AND
easy000b both CORRECT via the *same module*; one rule (`copy_common_output`)
covers 6 constant-output tasks; P1=6.0, P2=6.0.

**Invariants**: forbidden=none; positives = P1 +4.67 (1.33→6.0), P2 +4.67
(1.33→6.0), P6 +95 lines removed (619→524). P3/P4/P5 neutral. Verdict CLEAN.

### RUNG R0 CLEARED — GRID-level COMM-copy
- **(1) Works**: pipeline runs error-free; the `constant_output` matcher → 
  `copy_common_output` action → make_grid/coloring render path solves every
  constant-output task it sees.
- **(2) Module uniformity**: easy0001/0005/0009/0013/000a/000b are solved by
  **one** module and converge to **one** rule (`covers`=6) — no per-task branch,
  no per-task rule. The differing fixed output is derived from each task's
  example-output COMM at apply time, never hard-coded (value-agnostic proof:
  easy000a and easy000b have *different* fixed outputs, same module).
- **(3) Approaches the answer**: exact correct grids, reconstructed from the two
  frozen primitives.
- **(4) Search sanity**: deterministic, no brute force.
- Signals moved: P1/P2 1.33→6.0, P6 −95. R1's premise (a clean, value-agnostic
  GRID-level path that produces liftable `{condition, action}` rules) is now met.

**Next gap (note for future iter)**: R1 — object-level analysis. easy000c–i
(the easy_a remainder, still 2/9) need G0 object detection + a seed
property/relation/selection vocabulary (`position-of`/`color-of`/`unique`/
`argmax`, located under `agent/` not `DSL/` per BACKLOG §2.5-1) and OBJECT-level
`compare`, so a moving single pixel → fixed corner is solved by *selecting* the
object and reading its position/color into `coloring` args (the lift R3 then
unifies). That is the graduation-blocking rung.

---
## Iter 3 — 2026-06-12 — branch test31

**Diagnosis**: R0 is cleared (iter 2); the lowest unproven rung is **R1 —
object-level analysis**. The probe shows easy000c–i still INCORRECT via
`identity`: the pipeline has no object-level recognition at all, so a single
foreground object moved with its color/shape preserved (the whole easy000c–i
family — verified: every pair has one non-bg object in G0 and G1, color & size
preserved, position changed) is invisible to it. Following the same two-step
shape that cleared R0 (iter 1 laid the `constant_output` *recognition*
substrate, iter 2 wired it), the smallest defensible step is R1's recognition
substrate — the seed object-selection/property vocabulary + an object-level
matcher — **not** the generation+lift, which is a later iter.

**Change**:
- `agent/dsl_expr/__init__.py` (new) — the seed *argument-expression* vocabulary
  (BACKLOG §2.5-1/2b): `objects_of` (canonical foreground objects via
  `ARCKG.hodel`), `unique` (selection), `color_of`/`size_of`/`position_of`
  (properties). Pure, symbolic, side-effect-free (P7). Located under `agent/`,
  **not** `procedural_memory/DSL/`, so the F3 transformation-freeze is honored
  while the argument vocabulary grows where the checker does not apply.
- `agent/active_operators.py` — `ExtractPatternOperator` now surfaces an
  `object_transition` signal (per-pair single-object COMM/DIFF: all_single /
  color_preserved / shape_preserved / moved), computed via the seed vocabulary
  so the reads are lift-ready expressions (`unique(objects_of(G))`,
  `color_of`,…), not ad-hoc cell scans. +61 lines; no new `_try_*`/`_apply_*`
  (F2-safe); F8 companion = `agent/conditions/`.
- `agent/conditions/single_object_move.py` (new) — second matcher: fires when
  every example pair relocates one color/shape-preserved object. Recognizes the
  easy000c–i family value-agnostically (fixed target c–f, relative corner g/h,
  resized grid i); the differing target is *not* part of recognition (derived
  at apply time — the R3 lift). P5 +1.
- `tests/test_single_object_move.py` (new) — vocabulary + unit + integration
  (matcher fires on real `object_transition` for all of easy000c–i; rejects a
  recolor-in-place task built on disk, proving it discriminates on the
  COMM/DIFF, not on "one object exists"). 11 tests; suite 18/18 pass.

**CLAUDE.md §6.1 ↔ arbor-dsl-taxonomy §3 conflict (surfaced per BACKLOG §2.5-1)**:
§6.1 says "no new `def` under `procedural_memory/DSL/`"; taxonomy §3 says
property/relation/util hand-coding is allowed and *should* grow. Resolution
taken: the frozen contract binds only the *transformation* directory
(`procedural_memory/DSL/*.py`, what F3 checks), so the new property/selection
vocabulary lives in `agent/dsl_expr/`. No frozen contract violated; the conflict
is noted, not silently resolved.

**Probe before**: easy 1/3, easy_a 2/9; rules=1 (covers=6); P1=6.0, P5=1
**Probe after** : easy 1/3, easy_a 2/9 (unchanged — substrate iter; matcher not
yet consumed by `generalize`, exactly as iter 1 preceded iter 2's R0 wiring);
rules=1 (covers=6); P5=2. R0 family (easy000a/b, easy0001) still CORRECT — no
regression.

**Invariants**: forbidden=none; positives = P5 +1 (1→2). P6 −61 (active_operators
grew by the object_transition computation; allowed — F8 companion present, no
`_try_*`). P1–P4 neutral. Verdict CLEAN.

**Next gap (note for future iter)**: wire `single_object_move` end-to-end — have
`GeneralizeOperator` emit a `{condition: single_object_move, action: place_object}`
pair-specific program that reads the object via the seed vocabulary
(`position_of(unique(objects_of(G0)))`, `color_of(...)`) and renders it as
`coloring`(erase source) ∘ `coloring`(paint target) over a `make_grid`/reused
canvas, then have `predict` apply it from the test G0 only (P5). Because c–i
share that skeleton, the resulting pair-programs are exactly the R3
anti-unification input — do NOT let each task mint its own permanent literal
rule (§2.5-3); the target-position expression (fixed `(5,5)` vs grid
bottom-right) is the variable the lift must abstract.

---
## Iter 4 — 2026-06-12 — branch test31

**Diagnosis**: R1's recognition substrate exists (iter 3: seed vocabulary +
`single_object_move` matcher + `object_transition` signal) but nothing consumes
it — the move family (easy000c–i) still resolves to `identity`. Following iter
2's R0 wiring shape, the smallest defensible step is to wire the *generation* of
the simplest sub-case: the **fixed-target** movers (object lands on the same cell
across every example pair). That cell is derivable value-agnostically as the COMM
of the example output positions, so one `place_object` rule covers the whole
sub-case; the relative/corner/resized members (e/f/g/i) need different target
fillings and are left as the R3-lift variable (§2.5-2b), not forced now.

**Change**:
- `agent/conditions/single_object_move_fixed_target.py` (new) — second matcher:
  the *applicability condition* for the fixed-cell filling of `place_object`
  (§2.5-2b: an abstraction's hole needs a filling rule). Fires only when the
  moved object lands on a constant cell across all pairs **and** grid size is
  preserved. General predicate (any fixed-cell mover), not a per-task detector.
  P5 2→3; also the F8 companion for the active_operators edit.
- `agent/active_operators.py` — (a) `ExtractPatternOperator._object_transition`
  now also surfaces `target_constant` / `target_cell` (the COMM of example
  output positions) / `outsize_preserved`, all from the seed vocabulary;
  (b) `GeneralizeOperator` emits a value-agnostic `place_object` rule when the
  fixed-target matcher fires (after constant_output, so a/b keep their R0 path);
  (c) `PredictOperator._render_place_object` relocates the test object onto the
  derived cell via `make_grid` ∘ `coloring` — target read from example outputs,
  colour/cells read from test G0 (never its absent G1, P5), nothing hard-coded.
  No new `_try_*`/`_apply_*` (F2-safe; helpers are `_build_*`/`_render_*`).
- `procedural_memory/rule_002.json` (new, learned) — one value-agnostic rule,
  `condition.type=single_object_move_fixed_target`, `action.dsl=place_object`,
  `covers=[easy000c, easy000d, easy000h]` via dedup (not one rule per task);
  `anti_unification_trace=null`, consistent with rule_001 (AU lift is R3).
- `tests/test_place_object.py` (new) — registry + unit + real-signal + true
  end-to-end (pipeline renders the exact known test output for c/d/h; emits
  identity, *not* an overfit literal, for e/f/g/i). 10 tests; suite 28/28 pass.

**Probe before**: easy 1/3, easy_a 2/9; rules=1 (covers=6); P1=6.0, P5=2
**Probe after** : easy 1/3 (unchanged — 0002/0003 out of scope, no false fire),
easy_a **5/9** (a,b constant_output; **c,d,h place_object**; e/f/g/i correctly
identity); rules=2 (covers 6 + 3); P5=3. R0 family unregressed.

**Invariants**: forbidden=none (F8 companion present: new conditions/ file).
positives = **P5 +1 (2→3)** → verdict CLEAN. P1 6.0→4.5, P2 6.0→4.5, P6 −138:
expected dips from adding a *genuinely new general skeleton* (a second rule, more
code), not overfit accumulation — covers/P2 for rule_002 rises as more movers
solve. P3/P4 flat.

**Next gap (note for future iter)**: the relative-target movers are now the
glaring hole — e/f (constant displacement Δ=position_of(G1)−position_of(G0),
equal across pairs) and g (relative corner (H−1,W−1)) each need their own
*target-filling* matcher + render branch, mirroring this iter's fixed-target one.
Once two such fillings exist, `place_object`'s several pair-programs share the
"select object → erase source → paint at f(target)" skeleton differing only in
`f` — the exact `anti_unification.unify()` input for R3 to lift into one rule
whose target is a variable. (Also latent: the fast path reads `entry["rule"]`,
absent in the new schema, so stored rules never reuse — re-discovered each run.)

- Split: None, Tasks: 3
- Correct: 1 / 3 (33.3%)
- Rules: 1 -> 1 (+0 learned)
- Stored rule hits: 0
- Time: 2s
- Log: logs/learn_20260612_115229.log

---
## Learning Loop -- 2026-06-12 11:52

- Split: None, Tasks: 9
- Correct: 2 / 9 (22.2%)
- Rules: 1 -> 1 (+0 learned)
- Stored rule hits: 0
- Time: 4s
- Log: logs/learn_20260612_115231.log

---
## Learning Loop -- 2026-06-12 11:59

- Split: None, Tasks: 3
- Correct: 1 / 3 (33.3%)
- Rules: 1 -> 1 (+0 learned)
- Stored rule hits: 0
- Time: 1s
- Log: logs/learn_20260612_115908.log

---
## Learning Loop -- 2026-06-12 11:59

- Split: None, Tasks: 9
- Correct: 2 / 9 (22.2%)
- Rules: 1 -> 1 (+0 learned)
- Stored rule hits: 0
- Time: 4s
- Log: logs/learn_20260612_115910.log

---
## Learning Loop -- 2026-06-12 12:00

- Split: None, Tasks: 3
- Correct: 1 / 3 (33.3%)
- Rules: 1 -> 1 (+0 learned)
- Stored rule hits: 0
- Time: 1s
- Log: logs/learn_20260612_120039.log

---
## Learning Loop -- 2026-06-12 12:00

- Split: None, Tasks: 9
- Correct: 2 / 9 (22.2%)
- Rules: 1 -> 1 (+0 learned)
- Stored rule hits: 0
- Time: 4s
- Log: logs/learn_20260612_120041.log

---
## Learning Loop -- 2026-06-12 12:08

- Split: None, Tasks: 9
- Correct: 5 / 9 (55.6%)
- Rules: 1 -> 2 (+1 learned)
- Stored rule hits: 0
- Time: 4s
- Log: logs/learn_20260612_120814.log

---
## Learning Loop -- 2026-06-12 12:08

- Split: None, Tasks: 3
- Correct: 1 / 3 (33.3%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 1s
- Log: logs/learn_20260612_120828.log

---
## Learning Loop -- 2026-06-12 12:11

- Split: None, Tasks: 3
- Correct: 1 / 3 (33.3%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 1s
- Log: logs/learn_20260612_121155.log

---
## Learning Loop -- 2026-06-12 12:12

- Split: None, Tasks: 9
- Correct: 5 / 9 (55.6%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260612_121157.log

---
## Learning Loop -- 2026-06-12 12:17

- Split: None, Tasks: 9
- Correct: 7 / 9 (77.8%)
- Rules: 0 -> 3 (+3 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260612_121712.log

---
## Learning Loop -- 2026-06-12 12:19

- Split: None, Tasks: 3
- Correct: 1 / 3 (33.3%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 1s
- Log: logs/learn_20260612_121932.log

---
## Iter 5 — 2026-06-12 — branch test31

**Diagnosis**: R1's fixed-target filling landed (iter 4: easy000c/d/h), and the
iter-4 note named the next hole — the *relative-target* movers. The lowest
unproven step within R1 is the **second target-filling**: the constant-
displacement movers (easy000e Δ=(1,-1), easy000f Δ=(0,1)), where the object
moves by one Δ across all pairs but lands on *different* cells (verified against
the data). The fixed-target matcher correctly declines them (target not
constant), so they resolved to `identity`. This is the *smaller half* of iter
4's note (displacement only; the relative-corner g and resized i are left for a
later filling), and it is exactly the §2.5-2b/§5(R3) setup: two fillings of the
*same* `place_object` skeleton differing only in the target function `f`.

**Change**:
- `agent/conditions/single_object_move_constant_displacement.py` (new) — second
  *filling* matcher: fires when every pair shares one Δ (COMM of the per-pair
  position DIFFs) with grid size preserved. General predicate (any constant-
  offset mover), disjoint from `single_object_move_fixed_target` on the data
  (constant cell ⇒ varying Δ and vice-versa). P5 3→4; F8 companion for the
  active_operators edit.
- `agent/active_operators.py` — (a) `_object_transition` now also surfaces
  `displacement_constant` / `displacement` (the COMM Δ), via the seed vocabulary;
  (b) `GeneralizeOperator` emits a `place_object` rule with
  `action.args.target_mode="displacement"` when that matcher fires (after the two
  prior matchers; all disjoint); (c) `_render_place_object` is refactored to
  derive its target through a new `_derive_place_target(rule, task, src_pos)` that
  branches on `target_mode` — "fixed" (default; COMM of example output positions,
  unchanged behaviour) vs "displacement" (test object position + COMM Δ). The
  render skeleton (erase source via fresh `make_grid`, paint translated cells via
  `coloring`) is now *shared* across both fillings; only `f` differs — the R3
  variable. No new `_try_*`/`_apply_*` (helpers are `_build_*`/`_derive_*`/
  `_render_*`).
- `procedural_memory/rule_003.json` (new, learned) — value-agnostic,
  `condition.type=single_object_move_constant_displacement`,
  `action.dsl=place_object`, `args.target_mode=displacement`, `covers=[easy000e,
  easy000f]` via dedup (not one rule per task); `anti_unification_trace=null`
  (AU lift is R3). rule_001/002 unchanged (covers preserved).
- `tests/test_place_object_displacement.py` (new) — registry + unit + disjoint-
  ness + real-signal + true end-to-end (pipeline renders the exact known test
  output for e/f via the two frozen primitives). `tests/test_place_object.py` —
  updated the one now-stale assertion (e/f are no longer identity; only g/i are).
  Suite 38/38 pass.

**R3-readiness note (for the next iter)**: the two fillings are asymmetric in
representation — fixed-target carries `args={}` (mode implicit), displacement
carries `args={target_mode:"displacement"}`. The render defaults absent mode to
"fixed", so this is correct, but when R3 lifts the two `place_object` rules it
should *normalize* `target_mode` onto both (the variable it abstracts). Left
asymmetric now to avoid churning the committed rule_002; flagged here, not
silently resolved.

**Probe before**: easy 1/3, easy_a 5/9; rules=2 (covers 6+3); P1=4.5, P5=3
**Probe after** : easy 1/3 (0002/0003 out of scope, no false fire), easy_a
**7/9** (a,b constant_output; c,d,h fixed place_object; **e,f displacement
place_object**; g/i correctly identity); rules=3 (covers 6+3+2); P5=4. R0 family
(easy0001/000a/000b) unregressed.

**Invariants**: forbidden=none (F8 companion present: new conditions/ file).
positives = **P5 +1 (3→4)** → verdict CLEAN. P1 4.5→3.67, P2 4.5→3.67, P6 −96:
the expected dip from adding a *genuinely new general filling* (a third rule,
more code), **not** overfit accumulation — rule_003 is value-agnostic and covers
2 tasks via a general predicate (§2.5-3 "material for R3", not a per-task
literal). P1/P2 recover when R3 merges the two place_object fillings. P3/P4 flat.

**Next gap (note for future iter)**: with **two** `place_object` fillings now
coexisting (fixed cell + constant Δ), differing only in `args.target_mode`, the
R3 prerequisite is met — `anti_unification.unify()` over rule_002+rule_003 should
lift them into one `place_object` rule whose target function is a variable,
driving P1/P2/P3 up *together* (the BACKLOG §2.5-4 litmus). That is now the
highest-value step (R3, the "★ 최우선 큰-틀 보상"). Alternatively, still within
R1, the relative-corner filling (g: target=(H−1,W−1)) is a third member of the
same skeleton; but adding a *third* literal filling before R3 lifts the first
two would be accretion-shaped — prefer wiring R3 next.

---
## Learning Loop -- 2026-06-12 12:20

- Split: None, Tasks: 3
- Correct: 1 / 3 (33.3%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 1s
- Log: logs/learn_20260612_122057.log

---
## Learning Loop -- 2026-06-12 12:21

- Split: None, Tasks: 9
- Correct: 7 / 9 (77.8%)
- Rules: 3 -> 3 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260612_122059.log

---
## Learning Loop -- 2026-06-12 12:37

- Split: None, Tasks: 9
- Correct: 7 / 9 (77.8%)
- Rules: 1 -> 2 (+1 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260612_123738.log

---
## Learning Loop -- 2026-06-12 12:38

- Split: None, Tasks: 9
- Correct: 7 / 9 (77.8%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260612_123759.log

---
## Learning Loop -- 2026-06-12 12:38

- Split: None, Tasks: 3
- Correct: 1 / 3 (33.3%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 1s
- Log: logs/learn_20260612_123832.log

---
## Iter 6 — 2026-06-12 — branch test31

**Diagnosis**: Iter 5 left **two coexisting `place_object` fillings** (rule_002
fixed-cell, rule_003 constant-Δ) and named R3 (anti-unification) as the highest-
value step. Reading `docs/ANTI_UNIFICATION.md` (pre-written for "iter 6") exposed
the *real* blocker: `unify()` did not exist at all — `program/` failed to import
(`program/__init__.py` imported a non-existent `anti_unify`), so AU had **never**
been wired (P3=0). And the two fillings could not be lifted even once `unify()`
existed, because the spec's skeleton = `condition.type` + `action.dsl` must be
*identical*, yet the fillings carried two *different* condition.types (their
dispatch matchers). The smallest defensible R3 step is therefore: implement
`unify()` to the doc contract, give the two fillings a **shared parent
condition.type** (`single_object_move`, an already-registered matcher — the
filling distinction lives only in `action.args.target_mode`), and wire the single
AU call site so the pair lifts into one `covers>1` abstraction.

**Change**:
- `program/anti_unification.py` — implemented the public API to
  `docs/ANTI_UNIFICATION.md` §1–§3: `unify(rules)`, `UnifyResult`
  (`is_more_general`), `NoCommonSkeleton`. Leaf-case field-wise anti-unification
  over `condition.params`/`action.args` (shared values pass through, disagreements
  lift to `?vN`; `min_evidence` takes the max, never lifts), order-preserving
  `covers` union, and an immutable audit trace written under
  `episodic_memory/<source_task>/anti_unification/au_NNN.json`. The original-intent
  term-tree stubs are retained as documented future work.
- `program/__init__.py` — exported the real API (`unify`/`UnifyResult`/
  `NoCommonSkeleton`); the package now imports (it didn't before — the dangling
  `anti_unify` import is *why* AU saw no traffic).
- `agent/active_operators.py` — the two `_build_place_object_*` methods now emit
  the **parent** `condition.type="single_object_move"` instead of their dispatch-
  time filling matchers, so the two fillings share a skeleton (differ *only* in
  `action.args.target_mode`). Dispatch in `effect()` still uses the specific
  matchers; the render path keys on `target_mode`, untouched. No new `_try_*`.
- `agent/memory.py:save_rule` — wired the single AU call site (CLAUDE.md §8):
  (a) **subsumption** — a concrete instance an existing abstraction's variables
  accept is folded into its `covers`, never re-lifted (repeated runs converge);
  (b) exact dedup (unchanged); (c) **AU lift** — concrete siblings sharing a
  skeleton but differing in a param/arg are `unify()`-ed into one abstraction that
  *replaces* them on disk; (d) new source rule. Helpers `_subsumes`/`_same_skeleton`/
  `_persist_abstract` added; `NoCommonSkeleton` is caught (not `RuleSchemaError`,
  so F7 is not engaged).
- `procedural_memory/rule_002.json` (now the abstraction) + `rule_003.json`
  (deleted) — the two fillings lifted into ONE `place_object` rule:
  `action.args.target_mode="?v1"`, `covers=[c,d,e,f,h]`, `anti_unification_trace`
  → `episodic_memory/easy000e/anti_unification/au_001.json`. Rule count 3→2.
- `tests/test_anti_unification.py` (new) — 9 tests: unify unit (lift, covers
  union, min_evidence max, trace shape, `is_more_general`/`NoCommonSkeleton`) +
  save_rule integration (two fillings → one abstraction) + convergence (a
  subsumed instance grows covers, spawns no rule, writes no second trace). Suite
  47→47 (was 38; +9 new), all green.

**Probe before**: easy 1/3, easy_a 7/9; rules=3 (covers 6+3+2); P1=3.67, P2=3.67, P3=0.0
**Probe after** : easy 1/3 (unchanged), easy_a **7/9** (unregressed — a,b
constant_output; c,d,e,f,h place_object; g,i correctly identity); rules=**2**
(covers 6+5); P1=**5.5**, P2=**5.5**, P3=**0.5**.

**Invariants**: forbidden=none (F8 companion present: memory.py +
anti_unification.py accompany the active_operators edit). positives = **P1 +1.83,
P2 +1.83, P3 +0.5 (all three together)** → verdict CLEAN. This is the §2.5-4
litmus: rule *count* fell (3→2) while coverage *rose* — generalization, not
accretion. P6 +9 (active_operators comments documenting the skeleton-share). P4/P5 flat.

### RUNG R3 CLEARED — anti-unification fires end-to-end

R3's done-when ("최소 한 쌍이 lift 되어 covers>1 + anti_unification_trace 기록")
is met, against the four observation criteria (§5):
1. **작동**: `unify()` runs error-free; the lift produces a schema-valid
   abstraction; convergence (subsumption) holds across repeated runs (verified:
   2nd run_learn stays 2→2, +0 learned, one trace).
2. **모듈 통일성**: the two `place_object` fillings — once overfit *material*
   (§2.5-3) — now resolve through **one** abstraction whose differing target
   function is a single variable `?v1`. No per-task rule accretion.
3. **정답 접근**: easy_a 7/9 maintained; the family solves the intended way.
4. **탐색 건전성**: deterministic, bounded; the trace is a forensic audit.
Signals moved exactly as the rung predicts: **P1·P2·P3 rose together**.

**Next gap (note for future iter)**: with the lift+subsumption machinery proven,
the remaining R1 members are now *cheap* — a relative-corner filling (g:
target=(H−1,W−1)) and a resized filling (i) each add a new `target_mode`, and
`save_rule`'s subsumption **auto-folds** them into the existing abstraction's
`covers` (no new rule, P1/P2 keep rising) instead of spawning literals. That
drives easy_a toward 100% — the graduation milestone — while *strengthening* the
abstraction. (Latent, unchanged: the fast path reads `entry["rule"]`, absent in
the new schema, so the abstraction is learned but not yet *reused* — that is R5.)

---
## Learning Loop -- 2026-06-12 12:41

- Split: None, Tasks: 3
- Correct: 1 / 3 (33.3%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 1s
- Log: logs/learn_20260612_124142.log

---
## Learning Loop -- 2026-06-12 12:41

- Split: None, Tasks: 9
- Correct: 7 / 9 (77.8%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260612_124144.log

---
## Learning Loop -- 2026-06-12 12:49

- Split: None, Tasks: 9
- Correct: 8 / 9 (88.9%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260612_124917.log

---
## Learning Loop -- 2026-06-12 12:49

- Split: None, Tasks: 3
- Correct: 1 / 3 (33.3%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 1s
- Log: logs/learn_20260612_124930.log

---
## Learning Loop -- 2026-06-12 12:50

- Split: None, Tasks: 9
- Correct: 8 / 9 (88.9%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260612_125015.log

---
## Iter 7 — 2026-06-12 — branch test31

**Diagnosis**: R0 cleared (iter 2), R3 cleared (iter 6); the lowest unproven work
is the R1 graduation gap — easy_a stuck at 7/9 with g and i remaining. Inspecting
the data: easy000g moves the single object onto the **bottom-right corner**
`(H-1,W-1)` with grid size preserved, across grids of *different* sizes (4×4 /
3×5 / 6×4) — so the landing *cell* varies (fixed-target declines) and the offset
Δ varies (displacement declines), leaving it as `identity`. easy000i also lands
on a corner (top-left) but **resizes** the grid (6×6→5×5), a distinct
grid-resize capability. The smallest defensible step is the **relative-corner
filling** for g (size-preserved); i's resize is a larger, separate gap left for
later. This is the third filling of the *same* `place_object` skeleton, so iter
6's subsumption auto-folds it into the existing abstraction (rule_002) — covers
grows, no new rule (the §2.5-4 litmus).

**Change**:
- `agent/dsl_expr/__init__.py` — grew the argument/relation vocabulary with
  `corners_at(pos, H, W)` (relation: which grid corners a position coincides
  with) and `corner_cell(id, H, W)` (its inverse). A corner is kept as an
  **anchor formula** ("min"/"max" over the bounds), not a concrete cell, so it is
  value-agnostic — the same `br` resolves to a different cell per grid size
  (§2.5-2b). Located under `agent/`, not `procedural_memory/DSL/` (F3-safe,
  §2.5-1).
- `agent/conditions/single_object_move_relative_corner.py` (new) — third
  *filling* matcher: fires when every pair lands the object on the same grid
  corner (the COMM/intersection of `corners_at` across pairs) with size
  preserved. Disjoint from constant-displacement; *overlaps* fixed-target only in
  the same-size case (a corner cell is then also a constant cell — easy000c), but
  GeneralizeOperator checks fixed-target first so that overlap routes to the
  fixed rule and only the size-varying case (g) reaches this filling. P5 4→5;
  also the F8 companion for the active_operators edit.
- `agent/active_operators.py` — (a) `_object_transition` now surfaces
  `corner_constant` / `corner` (the COMM corner id), via the new vocabulary;
  (b) `GeneralizeOperator` emits a `place_object` rule with
  `action.args.target_mode="corner"` when that matcher fires (after the two prior
  fillings; disjoint/overlap-safe by order); (c) `_derive_place_target` gains a
  `corner` branch that re-derives the corner from the example outputs and
  resolves it against the *test* grid's own bounds (P5: never the test G1), now
  receiving `grid_dims` from `_render_place_object`. The render skeleton (erase
  source via fresh `make_grid`, paint at `f(target)` via `coloring`) is unchanged
  and shared across all three fillings; only `f` differs — the R3 variable. No
  new `_try_*`/`_apply_*`.
- `procedural_memory/rule_002.json` — the place_object abstraction's `covers`
  grew `[c,d,e,f,h] → [c,d,e,f,h,g]` by **subsumption** (target_mode="corner"
  accepted by the `?v1` variable). Rule count stays 2; `target_mode` stays
  abstract; trace unchanged. Not a new file — the iter-6 machinery folded it.
- `tests/test_place_object_corner.py` (new) — registry + vocab round-trip + unit
  (fires only on constant corner + size preserved) + signal (real g) +
  same-size-overlap-routes-to-fixed (c) + end-to-end (renders exact g output) +
  subsumption (corner filling folds into the abstraction, no second rule). 14
  tests. `tests/test_place_object.py` — updated the one now-stale assertion (g is
  solved; only i is identity). Suite 60/60 pass.

**Probe before**: easy 1/3, easy_a 7/9; rules=2 (covers 6+5); P1=5.5, P2=5.5, P5=4
**Probe after** : easy 1/3 (unchanged — 0002/0003 out of scope, no false fire),
easy_a **8/9** (a,b constant_output; c,d,e,f,h,g place_object; only i — the
resize — remains identity); rules=**2** (covers 6+6); P1=**6.0**, P2=**6.0**, P5=5.

**Invariants**: forbidden=none (F8 companion present: new conditions/ file).
positives = **P1 +0.5, P2 +0.5, P5 +1** → verdict CLEAN. The §2.5-4 litmus holds:
covers (P1/P2) rose while rule *count* stayed 2 — generalization via subsumption,
not accretion. P6 −88 (active_operators grew by the corner signal + render
branch; allowed — F8 companion present, no `_try_*`). P3/P4 flat.

**Next gap (note for future iter)**: easy_a is one task from the graduation
milestone — only easy000i remains, and it is **not** another `place_object`
filling: its output grid is a *different size* from the input (6×6→5×5, object to
top-left). That needs a grid-**resize** capability — a `make_grid` whose
dimensions are derived from the examples (here H-1,W-1) rather than copied from
the input — which the current size-preserving render path cannot express. That is
the glaring hole: a resize-aware output-dimension derivation, still composed from
the two frozen primitives but parameterizing `make_grid`'s height/width. (Latent,
unchanged since iter 4/6: the fast path reads `entry["rule"]`, absent in the new
schema, so the abstraction is learned but not reused across runs — that is R5.)

---
## Learning Loop -- 2026-06-12 12:52

- Split: None, Tasks: 3
- Correct: 1 / 3 (33.3%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 1s
- Log: logs/learn_20260612_125159.log

---
## Learning Loop -- 2026-06-12 12:52

- Split: None, Tasks: 9
- Correct: 8 / 9 (88.9%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260612_125201.log

---
## Learning Loop -- 2026-06-12 12:59

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260612_125921.log

---
## Learning Loop -- 2026-06-12 12:59

- Split: training, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 9s
- Log: logs/learn_20260612_125930.log

---
## Learning Loop -- 2026-06-12 12:59

- Split: training, Tasks: 3
- Correct: 0 / 3 (0.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 6s
- Log: logs/learn_20260612_125949.log

---
## Learning Loop -- 2026-06-12 13:00

- Split: None, Tasks: 3
- Correct: 1 / 3 (33.3%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 1s
- Log: logs/learn_20260612_130004.log

---
## Learning Loop -- 2026-06-12 13:02

- Split: None, Tasks: 3
- Correct: 1 / 3 (33.3%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 1s
- Log: logs/learn_20260612_130202.log

---
## Learning Loop -- 2026-06-12 13:02

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 3s
- Log: logs/learn_20260612_130204.log

---
## Learning Loop -- 2026-06-12 13:08

- Split: None, Tasks: 16
- Correct: 6 / 16 (37.5%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 7s
- Log: logs/learn_20260612_130846.log

---
## Iter 9 — 2026-06-12 — branch test31

**Diagnosis**: easy_a is mastered (R1 cleared iter 8) and R0–R3 mechanisms work
(rule_001 constant_output covers 6; rule_002 place_object covers 7, AU-traced).
The easy probe (seed42 → easy0001/0002/0003) sits at 1/3 not from a capability
gap but because **easy0002/0003/0004 are ill-posed**: their two training pairs
have *identical inputs mapping to different outputs* (e.g. easy0002:
2@(1,1)→2@(5,5) and 2@(1,1)→1@(5,5)) — non-functional, so the agent correctly
abstains (identity) per P3 (reasons over values, no DIFF can justify a unique
answer). The graduation gate is therefore mis-calibrated against contradictory
probe tasks, not blocked by a missing capability. The *functional* failing
members (easy0007/0008/0010/0011/0015/0016) all need the target cell / output
colour derived as a **relation on the moving object's property** (easy0008:
target == (2·colour, 2·colour)) — variable-origin derivation, which is
arbor-open-questions **Q-B3/Q-B4** + the §2.5-2b "AU product is incomplete until
its variable is filled" gap. Per BACKLOG_LOOP §5 that rung is **held and
surfaced, not invented**.

The smallest defensible step that moves a positive signal *without* touching the
open question or hand-coding a detector: harvest the genuine generalization the
existing place_object abstraction already has over the easy slice, and lock the
intended behaviour with tests.

**Change**:
- `procedural_memory/rule_002.json` — running the full easy slice
  (`run_learn.py --task-dir data/ARC_easy`) grew `covers` from the 7 easy_a
  movers to **+easy0006, +easy0014** (the easy-slice members whose rule is
  "relocate single object onto a constant cell, colour preserved" — the same
  fixed-target filling). Rule count stays 2; one general rule absorbs more of
  the family by subsumption (§2.5-4 litmus: covers↑ with rule count flat =
  generalization, not accretion). No new rule file, no new detector.
- `tests/test_easy_slice_family.py` (new, 6 tests) — pins three facts:
  (1) place_object solves easy0006/0014 the intended way (generalization
  guard); (2) the agent abstains (identity, no fabricated rule) on the
  contradictory easy0002/0003/0004 (P3 guard — prevents a future iter from
  "solving" them by guessing); (3) the property-relation targets
  easy0007/0008 abstain pending the variable-origin open question (locks the
  held rung against a premature score-chasing fix).

**Probe before**: easy 1/3, easy_a 9/9; rules=2 (covers 6+7); P1=6.5, P2=6.5, P5=5
**Probe after** : easy 1/3 (unchanged — 0002/0003 ill-posed, correct abstain;
no regression), easy_a 9/9; rules=2 (covers 6+9); P1=**7.5**, P2=**7.5**, P5=5

**Invariants**: forbidden=none (active_operators.py untouched → F8 N/A; no new
`_try_*`/`_apply_*`; DSL unchanged; no frozen-file edit). positives = **P1 +1.0,
P2 +1.0**; P3/P4/P5/P6 flat → verdict CLEAN.

**Next gap (note for future iter)**: the wall is now explicit and singular —
**variable-origin derivation** (target/colour as a relation on an object
property). It is needed by every remaining functional easy task (0007/0008/0010/
0011/0015/0016) *and* is what would complete the AU product rule_002's `?v1`
into a self-applying abstraction (the R5 fast-path can't reuse rule_002 directly
because `target_mode="?v1"` is unresolved — §2.5-2b). But it is **open-question
territory (Q-B3/Q-B4)**: how to *invent/select* the derive-expression for a
variable is the user's explicit "(아직 모르겠어)". Per BACKLOG_LOOP §5 the next
iter should either (a) make a *design proposal* for variable-origin resolution
and surface it for the user, or (b) route to a different rung — R4 (2nd-order
edge-of-edge compare) via an authored `data/ARC_madeup/` task — rather than
inventing a 2-point relation fitter that would overfit.

---
## Learning Loop -- 2026-06-12 13:15

- Split: None, Tasks: 3
- Correct: 1 / 3 (33.3%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 1s
- Log: logs/learn_20260612_131547.log

---
## Learning Loop -- 2026-06-12 13:15

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 0
- Time: 4s
- Log: logs/learn_20260612_131549.log

---
## Learning Loop -- 2026-06-12 13:27

- Split: None, Tasks: 3
- Correct: 1 / 3 (33.3%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 1
- Time: 1s
- Log: logs/learn_20260612_132658.log

---
## Learning Loop -- 2026-06-12 13:27

- Split: None, Tasks: 9
- Correct: 9 / 9 (100.0%)
- Rules: 2 -> 2 (+0 learned)
- Stored rule hits: 2
- Time: 4s
- Log: logs/learn_20260612_132700.log

---
## Iter 10 — 2026-06-12T13:28:13 — branch test31

**Diagnosis**: R0–R3 are cleared and easy_a is mastered (9/9), but the probe's
`Reused: 0 times (stored rule hit)` exposes that the **Fast path is dead code** —
every solve re-runs the full Slow pipeline and no learned rule is ever reused,
which directly contradicts the single ultimate goal (knowledge that *grows and
gets reused*) and is the precondition for rung R5. Root cause (confirmed, three
stacked breakages): `active_agent.solve()` read `entry.get("rule", {})`, a key
from an **older wrapped schema**; the persisted schema is now flat
({condition, action}, RULE_FORMAT §3) with no "rule" wrapper, so every rule read
back as `{}`. Even read directly, the flat schema carries no top-level `type`
dispatch tag PredictOperator keys on, and the render helpers read the task off
the predictor — which the fast path never seeded. This is the smallest defensible
step: a confirmed correctness/architecture defect with a bounded fix, no
open-question entanglement, lower risk than starting R4's 2nd-order machinery.

**Change**:
- `agent/memory.py` — added `applicable_rule(entry)`: the schema bridge from the
  on-disk flat {condition, action} rule to a PredictOperator-applicable rule
  (stamps the dispatch `type` from `action.dsl` via `_DSL_TO_DISPATCH`). Returns
  None for unknown recipes AND for rules whose action still holds an unresolved
  anti-unification variable (`?v…`, e.g. rule_002's `target_mode="?v1"`) — so an
  *incomplete* abstract rule is never falsely replayed; it falls through to the
  Slow path. `_has_unresolved_var` helper. Also corrected the file's stale
  module docstring, which still documented the obsolete wrapped-"rule" schema
  (the very assumption that rotted the fast path).
- `agent/active_agent.py` — fast path now reconstructs via `applicable_rule`,
  seeds `self._predictor._task = task` before replay, and drops the dead
  `entry.get("rule")` read. No change to active_operators.py (so F8 N/A) and no
  new `_try_*`/`_apply_*` (F2 N/A).
- `tests/test_fast_path_reuse.py` (new, 6 tests) — `applicable_rule` unit cases
  (stamps type / skips unknown recipe / skips unresolved `?v`); end-to-end reuse
  of a concrete constant-output rule (method=stored_rule, times_reused persisted,
  correct grid); reuse output == Slow-path output (behaviour-preserving); and an
  abstract `?v1` rule falls through to the Slow path with no correctness loss.

**Probe before**: easy 1/3 (easy0001 via *pipeline*), easy_a 9/9; **Reused: 0**;
rules=2 (covers 6+9); P1=7.5 P2=7.5 P3=0.5 P4=247 P5=5
**Probe after** : easy 1/3 (easy0001 now via **stored(easy0001)**, "Discovered:
0 new" — no re-derive), easy_a 9/9 (**Reused: 2** — the concrete constant-output
members a/b reused; c–i correctly fall through to Slow path); **Reused: 1** on the
seed-42 probe; rules=2 (covers 6+9); P1–P5 unchanged. Suite 66→**72** pass.

**Invariants**: forbidden=**none** (active_operators.py untouched; no new
`_try_*`/`_apply_*`; DSL frozen; no frozen-file edit; rule files restored to
times_reused=0 so the commit carries no verification side-effects). positives =
all flat → verdict **NEUTRAL**. This is the INVARIANTS §3 case: the P1–P6 set has
**no signal that measures reuse rate**, so reviving the dead Fast path (an
architecture-fidelity fix, observable as Reused 0→≥1) scores neutral despite being
real, non-spinning work. Correctness is unchanged by construction (behaviour-
preserving reuse, guarded by `_rule_matches_examples`).

**Structural finding (surfaced for the user, not acted on)**: the easy→training
graduation gate is **unsatisfiable**. `run_loop.sh` requires the seed-42 easy
probe (easy0001/0002/0003) at 100%, but easy0002/0003 are *non-functional*
(identical training inputs → different outputs; verified directly this iter), so
the agent correctly abstains and EASY_CLEAN can never be 1 — the loop is pinned
in `easy` phase regardless of capability. This is not mine to fix (editing
run_loop.sh to skip ahead / editing frozen data/ is forbidden); flagging so the
user can re-seed the probe, exclude the ill-posed members, or gate graduation on
easy_a alone.

**Next gap (note for future iter)**: with the Fast path alive, R5's remaining
half is **variable resolution** — filling rule_002's `?v1` so the AU-lifted
*abstract* rule self-applies (currently it's correctly skipped, so c–i still need
the Slow path). The defensible, non-inventing route is Q-B4's *proposed
direction* (a): enumerate the **already-known** fillings {fixed, displacement,
corner} and accept the one that reproduces all example outputs — selection
grounded in comparison, over a *bounded* domain (NOT the open Q-B3 "invent a new
concept" case). Alternatively route to R4 (2nd-order edge-of-edge compare) via an
authored `data/ARC_madeup/` task, which would also move P5.
