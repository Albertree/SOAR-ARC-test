# LOOP COMPLETE — honest termination

**Date**: 2026-06-15 (iter 66, branch test33)
**Author**: iter 66 of the ARBOR infinite loop
**Trigger**: PROMPT.md §2.2 / §5 / docs/BACKLOG_LOOP.md §7 — genuine convergence
of the *general-mechanism* frontier, with the residual fenced behind an explicit
open question.

> `run_loop.sh` stops at the next iter when this file is present. The user resumes
> by **deleting it** (e.g. after lifting the bar — see "Remaining limitations").
> Written only because it is *true*: a premature completion file is itself a
> meaningless artifact (PROMPT.md §2.2).

---

## 1. Why I judge development has converged (the bar: §7, all three)

The bar is **not** ARC score (score is a microscope, PROMPT.md §1). The bar is:
*no nameable gap a future iter can close without inventing a per-task concept, and
no defensible `data/ARC_madeup/` task that would expose one, with the remainder
waiting on a human design decision in `arbor-open-questions.md`.* All three hold.

### 1a. The capability ladder (R0–R6) is built and proven the intended way

- **R0** GRID-level COMM-copy — cleared (constant-output, value-agnostic).
- **R1** Object-level analysis + selection-lift — cleared; the seed
  property/relation/util/selection vocabulary lives under `agent/` (not in the
  frozen DSL), and selection arguments lift (`size`/`position`/`colour-identity`/
  `rank`).
- **R2** Episodic writer — confirmed (P4 = 932 attempt folders on disk).
- **R3** Anti-unification wiring — cleared and *repeatedly* exercised: `unify()`
  fires at the single `save_rule()` call site and lifts divergent task-specific
  programs into `covers>1` rules with traces (rule_011 covers=22, rule_012
  covers=6, rule_016 covers=5, rule_019 covers=5, …).
- **R4** 2nd-order/ranking relation — cleared (dense size-rank / ordinal property
  transfers to unseen size keys).
- **R5** Fast-path reuse — fired (stored-rule hits generalize across structurally
  distinct tasks; e.g. dedup-family 3/4 via `stored()`).
- **R6** Training escalation — this is the rung the loop has been climbing for
  ~40 iters by **growing the Slow-path synthesizer** (`program/synthesis.py`):
  ~19 frozen-primitive composition schemas, each lifting to `covers>1`, plus the
  2-step **compose** lever (crop/dihedral/dedup stage-1 → single-step stage-2).
  **This rung's general lever is now exhausted — see §2.**

### 1b. The general-mechanism frontier is probed-exhausted

Every non-open-question lever a future iter could pull has been tested by
**read-only, full-1000-task, held-out-verified** probes and folds **< 2** tasks
(the §2.5-3/4 bar for "advance, not accretion"). The decisive recent probes:

| Lever | Result | Probe |
|-------|--------|-------|
| Single-step clean families (ray/cross, recolor-by-new-property, dihedral overlay, keep/erase, bbox fill) | all 0 ≥2-fold under full-grid reproduction | iter59 |
| Compose stage-1 widenings (block_reduce, trim_border, panel-split, panel-select, odd_block, common_block, tile_unit) | all refuted, 0 held-out | iter61–64 |
| Add-only fill — 6 fresh families (reflect-union ×3, diag/ortho ray, frame) | 0 or 1 fold (diag_ray singleton) over 223 add-only tasks | iter65/66 `probe_addonly_families.py` |
| **3-step compose** (reduction→reduction→step) | 0 / 1 fold (b9b7f026), **0 held-out** | iter66 `probe_compose3_fast.py` |
| **Expand-then-transform compose** (scale/fractal stage-1 → step) | **0 folds** over all 50 larger-output failing tasks | iter66 `probe_compose_expand.py` |

The 2×/3× larger-output cluster *looked* like mass (11 tasks at exactly 2×, 8 at
3×) but on inspection (`/tmp` probes, iter66) each is a **per-task** arrangement
(tile-then-recolour, content-keyed macro tiling, object enlarge-and-reposition) —
heterogeneous, no shared liftable skeleton; the clean dihedral-tiling / scale /
fractal sub-families are *already* schemas.

### 1c. The residual is the explicit open question Q-B3 — must not invent

The remaining failing mass decomposes (iter64 `probe_fail_profile.py`, 871 tasks)
into:
- **184 pure-recolour** (footprint-fixed) = the object-correspondence corpus;
- **39 output-is-a-subgrid** named per-task heterogeneously;
- most of the 183 smaller / 50 larger / 8 varies = multi-step or correspondence;
- **223 add-only fill** whose residual *selector* (WHERE to add) is per-task.

In every case the unfilled piece is **which input element corresponds to which
output element / which region the rule acts on** — i.e. the per-task *matching-key
/ concept invention* that `arbor-open-questions.md` lists as **Q-B3** ("self-
introduced primitive — 새 property 발명"), the single ❌ "본질적 미해결" in that
doc's progress table. iter63 confirmed fixed correspondence predicates
(col/row-overlap, nearest, contains, nearest-anchor) fold ≤1 with held-out
(`scripts/probe_legend.py`). BACKLOG_LOOP.md §5 is explicit: when a rung touches
an open question, **surface and defer — do not invent the answer**. So this is not
"no small slice"; it is *architecturally fenced* pending a user design decision.

### 1d. No defensible new `madeup` task exposes a *new* general gap

The authored beginner curriculum is mastered (`data/ARC_madeup/` 27/27) and covers
the whole §2.1 concept list (object size≠1, count≠1, multi-object selection, grid
resize, unequal in/out sizes, size↔object-property, pairs≠2). Any *new* madeup
task that would fail would necessarily isolate object-correspondence/concept-
invention = Q-B3 — which I must not invent an answer to. Authoring it would be
NEUTRAL infra, not a closed gap (the spinning §2.2 forbids).

---

## 2. Standings (figures)

- **Rules**: 24 (all canonical `{condition, action}`; no schema-invalid rules).
- **Rule coverage P1 = sum-covers / rules = 147 / 24 = 6.125**; P2 mean covers
  6.125; **P3 au_traced_frac 0.833**; P4 episodic entries 932; P5 condition
  matchers 4; P6 active_operators 1433 lines.
- **Synthesizer (Slow path)**: **129 / 1000** training tasks solved by a general,
  value-agnostic program; **114** of those also reproduce the held-out test pair
  (≈88% transfer — the solved programs are general, not overfit literals).
- **Regression guards (the intended-way bar, not score)**: `data/ARC_easy_a` 9/9
  (100%), `data/ARC_madeup` 27/27 (100%) — green every iter.
- **Forbidden signals**: none tripped this lineage (F1 frozen files intact; F2 no
  new `_try_*`; F3 transformation DSL still exactly `coloring`/`make_grid`).

---

## 3. Honest remaining limitations (for the user to decide whether to lift the bar)

ARBOR is **not** a high-scoring ARC solver and was never meant to be judged as one
at this stage. It solves the easy_a + madeup curricula the intended way and ~13%
of ARC-AGI-2 training via a growing, anti-unification-lifted, frozen-primitive
synthesizer. Autonomous progress is now blocked on **one** thing:

> **Object-correspondence / concept invention (Q-B3).** To climb further the
> system must learn, per task and *value-agnostically*, which input object/region
> corresponds to which output object/region — and, when no existing property
> names the relevant feature, *invent* the property (e.g. "this coordinate is the
> grid's bottom-right", "this object is the odd-one-out by shape"). The design doc
> sketches a direction (hypothesis-enumerate-and-test, like the synthesizer
> already does) but flags the *enumeration efficiency / candidate-selection
> weighting* as essentially unresolved (Q-B3, Q-B4) — a **human design decision**,
> not something the loop may silently fabricate.

**To resume the loop**, the user can:
1. Make a design decision on Q-B3/Q-B4 (the matching-key / property-invention
   enumeration + ranking policy) and record it in `arbor-open-questions.md`, then
   delete this file — the next iter can then build the object-correspondence rung
   (the single largest remaining capability, ~184+ tasks) without "inventing".
2. Or lift the bar in another direction (e.g. a new sanctioned mechanism) and
   delete this file.

Until then, continuing would only emit near-duplicate NEUTRAL probe commits over
an already-mapped frontier — the spinning PROMPT.md §2.2 most wants gone.

---

## 4. Standing artifacts left for a resumed loop (so it need not re-scan)

Read-only diagnostics under `scripts/` (all write nothing; together they record
the refuted hypotheses so a resumed loop does not waste iters re-probing):
`probe_fail_profile.py`, `probe_panel_select.py`, `probe_window_select.py`,
`probe_addonly_families.py`, `probe_addonly_profile.py`, `probe_compose3.py`,
`probe_compose3_fast.py`, `probe_compose_expand.py`, `probe_legend.py`.
