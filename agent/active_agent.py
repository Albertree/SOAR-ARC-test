"""
ActiveSoarAgent — Main SOAR agent with memory-based learning.

Solve flow:
  1. Load stored rules from procedural_memory
  2. Try each stored rule against example pairs (fast path)
  3. If a stored rule works → apply to test input, return
  4. If none work → run full SOAR pipeline (slow path)
  5. If pipeline discovers a new rule → save to procedural_memory
"""

from types import SimpleNamespace

from agent.wm import WorkingMemory
from agent.cycle import run_cycle
from agent.elaboration_rules import build_elaborator
from agent.rules import build_proposer
from agent.io import inject_arc_task
from agent.active_operators import (
    PredictOperator,
    SIZE_GRID_DSL,
    SELF_FRACTAL_DSL,
    CANVAS_FILL_DSL,
    RECOLOR_DSL,
    OBJECT_SELECT_RECOLOR_DSL,
    GEOMETRIC_TRANSFORM_DSL,
    SCALE_TRANSFORM_DSL,
    SYMMETRY_REPAIR_DSL,
    OBJECT_EXTRACT_DSL,
)
from agent.conditions import match as match_condition
from agent.dsl_expr.selection import (
    analyze_object_size_grid,
    analyze_object_move,
    analyze_self_fractal,
    analyze_canvas_fill,
    analyze_color_remap,
    analyze_object_select_recolor,
    analyze_geometric_transform,
    analyze_scale_transform,
    analyze_symmetry_repair,
    analyze_object_extract,
)
from agent.memory import load_all_rules, save_rule_to_ltm, increment_reuse_count
from agent.wm_logger import reset_wm_snapshot

# The abstract (AU-lifted) ``action.dsl`` name carried by the place_object family
# rule (rule_002). Distinct from the *concrete* per-reading DSL names
# (``place_object_constant`` …) the Slow-path predictor dispatches on: this is the
# lifted umbrella whose ``args.target.reading == "?v0"`` hole is resolved at reuse
# time (BACKLOG_LOOP §2.5-2b).
PLACE_OBJECT_ABSTRACT_DSL = "place_object"

# Sentinel render target for the place_object family: its ``?v0`` reading-hole
# (constant_target / constant_offset / constant_corner / constant_resize /
# constant_select) is not a single self-resolving renderer but a *multi-reading
# resolver* on the agent (``_place_object_render``), which tries each reading and
# keeps the first that reproduces the examples. Every other family's renderer
# self-resolves its argument off the task's own examples, so it is named directly
# by its PredictOperator method. Distinct object so it can never collide with a
# real predictor attribute name.
_PLACE_OBJECT_RESOLVER = object()

# ── Fast-path abstract-rule reuse registry (R5 / module E) ────────────────────
# Each tuple is (action.dsl, condition.type, analyze_fn, render_target) where
# render_target either names a self-resolving ``PredictOperator`` method — it
# recomputes the family's lifted argument expression off the task's *own* example
# COMM and renders the test pairs (§2.5-2b "fill the hole from COMM, then verify")
# — or is the ``_PLACE_OBJECT_RESOLVER`` sentinel for the one family that needs
# the multi-reading resolver on the agent.
#
# This is a *data table*, not a hand-spelled dict (iter 45's named next gap):
# every born-general family that owns a lifted ``covers>1`` rule now participates
# in Fast-path reuse by appearing in this list, instead of requiring a bespoke
# constructor edit per family. That is the §2.5 generalisation — extend the reuse
# *mechanism* once, not once per family. The reuse safety gate
# (``_reproduces_examples``) still guards every entry, so wiring a family can only
# turn a Slow-path re-derivation into a Fast-path reuse, never a wrong answer.
# (``copy_common_output`` is intentionally absent — it has no self-resolving
# ``_*_grids`` renderer yet; wiring it is a separate later step.)
_ABSTRACT_REUSE_REGISTRY = [
    (SIZE_GRID_DSL,             "object_size_grid",      analyze_object_size_grid,      "_place_size_grid_grids"),
    (PLACE_OBJECT_ABSTRACT_DSL, "object_move",           analyze_object_move,           _PLACE_OBJECT_RESOLVER),
    (SELF_FRACTAL_DSL,          "self_fractal",          analyze_self_fractal,          "_self_fractal_grids"),
    (CANVAS_FILL_DSL,           "canvas_fill",           analyze_canvas_fill,           "_canvas_fill_grids"),
    (RECOLOR_DSL,               "color_remap",           analyze_color_remap,           "_recolor_grids"),
    (OBJECT_SELECT_RECOLOR_DSL, "object_select_recolor", analyze_object_select_recolor, "_object_select_recolor_grids"),
    (GEOMETRIC_TRANSFORM_DSL,   "geometric_transform",   analyze_geometric_transform,   "_geometric_transform_grids"),
    (SCALE_TRANSFORM_DSL,       "scale_transform",       analyze_scale_transform,       "_scale_transform_grids"),
    (SYMMETRY_REPAIR_DSL,       "symmetry_repair",       analyze_symmetry_repair,       "_symmetry_repair_grids"),
    (OBJECT_EXTRACT_DSL,        "object_extract",        analyze_object_extract,        "_object_extract_grids"),
]


class ActiveSoarAgent:
    """
    SOAR agent that accumulates knowledge across tasks.
    Each solve() call checks stored rules first, then falls back to the pipeline.
    New rules are saved after successful pipeline discoveries.
    """

    def __init__(self, semantic_memory_root: str = "semantic_memory",
                 procedural_memory_root: str = "procedural_memory",
                 max_steps: int = 50):
        self.semantic_memory_root = semantic_memory_root
        self.procedural_memory_root = procedural_memory_root
        self.max_steps = max_steps
        self._submission_count: int = 0
        self._current_task_hex: str = None
        self._predictor = PredictOperator()

        # --- Fast-path activation table for *abstract* (covers>1) rules (R5) ---
        # A lifted anti-unification rule is an *incomplete* program: its action
        # carries a ``?vN`` variable whose filler must be chosen from the new
        # task's own COMM before it can run (BACKLOG_LOOP §2.5-2b — "AU 결과는
        # 미완성; 변수를 채우는 선택이 선행돼야"). The legacy ``_apply_rule``
        # dispatcher only knows the three concrete legacy types, so the stored
        # abstractions never fired and every task re-derived through the Slow path
        # (`Reused: 0`). Each entry maps an abstract ``action.dsl`` to
        #   (condition.type, patterns_fn, render_fn)
        # where the condition matcher is the *activation* test (module E) and the
        # render_fn recomputes the variable from the task's examples and renders —
        # i.e. the stored rule is *reused* rather than rediscovered.
        #
        # The table is built from the module-level ``_ABSTRACT_REUSE_REGISTRY``
        # data list (iter 46): every born-general family that owns a lifted rule
        # participates by appearing there, so the reuse *mechanism* (module E) is
        # extended once rather than re-hand-spelled per family. Most renderers
        # self-resolve their lifted argument off the task's own examples; the one
        # exception is ``place_object``, whose ``?v0`` reading-hole needs the
        # multi-reading resolver ``_place_object_render`` on the agent (the
        # ``_PLACE_OBJECT_RESOLVER`` sentinel selects it). The reuse safety gate
        # (``_reproduces_examples``) guards every entry — wiring a family can only
        # convert a Slow-path re-derivation into a Fast-path reuse, never a wrong
        # answer (it declines unless the resolved program reproduces *every*
        # example output exactly).
        self._abstract_reuse = {
            dsl: (
                cond_type,
                self._make_reuse_patterns_fn(cond_type, analyze_fn),
                (self._place_object_render
                 if render_target is _PLACE_OBJECT_RESOLVER
                 else getattr(self._predictor, render_target)),
            )
            for dsl, cond_type, analyze_fn, render_target in _ABSTRACT_REUSE_REGISTRY
        }

        # Stats for logging
        self.last_solve_info = {}

    def solve(self, task) -> list:
        """
        Solve one task. Returns list of predicted grids (one per test pair).
        Tries stored rules first, then full pipeline.
        """
        if self._current_task_hex != task.task_hex:
            self._current_task_hex = task.task_hex
            self._submission_count = 0

        self.last_solve_info = {
            "task_hex": task.task_hex,
            "method": "none",
            "rule_type": "none",
            "steps": 0,
            "rule_source": None,
        }

        # --- Fast path: try stored rules ---
        stored_rules = load_all_rules(self.procedural_memory_root)
        for entry in stored_rules:
            # Abstract (covers>1) rule reuse: activate the stored rule via its
            # condition matcher and resolve+render it on this task (R5, §2.5-2b).
            predicted = self._reuse_abstract_rule(entry, task)
            if predicted:
                increment_reuse_count(entry)
                self.last_solve_info.update({
                    "method": "stored_rule",
                    "rule_type": entry.get("concept")
                    or entry.get("action", {}).get("dsl", "abstract"),
                    "rule_source": entry.get("source_task"),
                })
                self._submission_count += 1
                return predicted

            rule = entry.get("rule", {})
            if rule.get("type") == "identity":
                continue  # skip identity fallback rules
            if self._rule_matches_examples(rule, task):
                predicted = self._apply_rule_to_tests(rule, task)
                if predicted:
                    increment_reuse_count(entry)
                    self.last_solve_info.update({
                        "method": "stored_rule",
                        "rule_type": rule.get("type", "unknown"),
                        "rule_source": entry.get("source_task"),
                    })
                    self._submission_count += 1
                    return predicted

        # --- Slow path: full SOAR pipeline ---
        wm = WorkingMemory()
        reset_wm_snapshot(wm)
        inject_arc_task(task, wm)

        elaborator = build_elaborator()
        proposer = build_proposer()

        result = run_cycle(
            wm, elaborator, proposer,
            max_steps=self.max_steps,
            stop_on_goal=True,
            log_wm=False,
        )

        predicted = self._extract_prediction(wm)

        active_rules = wm.s1.get("active-rules")
        rule_type = "none"
        if active_rules and isinstance(active_rules, list):
            rule_type = active_rules[0].get("type", "none")

        self.last_solve_info.update({
            "method": "pipeline",
            "rule_type": rule_type,
            "steps": result["steps_taken"],
        })

        # --- Learn: save new rule only if the discovered program reproduces
        #     the train examples it was derived from. An overfit pair-specific
        #     program is legitimate anti-unification *material* (BACKLOG §2.5-3)
        #     only when it actually reproduces its own train pairs; a non-identity
        #     guess that fits neither train nor test is noise. Persisting it spawns
        #     a condition-less, covers=1 rule that can never be lifted — the
        #     168-rule accretion failure mode (§2.5-4, F2 spirit). The check uses
        #     *train* reproduction (available at solve time), never test
        #     correctness, so it is honest, not score-gaming.
        if (active_rules and rule_type != "identity"
                and self._rule_matches_examples(active_rules[0], task)):
            save_rule_to_ltm(
                active_rules[0], task.task_hex,
                self.procedural_memory_root,
            )

        self._submission_count += 1
        return predicted

    # ---- abstract (covers>1) rule reuse — R5 / §2.5-2b -------------------

    @staticmethod
    def _make_reuse_patterns_fn(cond_type, analyze_fn):
        """Build the ``patterns_fn`` for one registry family: it runs the family's
        ``analyze_fn`` on the task's own example pairs and keys the result under the
        family's ``condition.type`` — the exact shape the Slow path's ExtractPattern
        produces, so the stored rule's condition matcher activates identically on a
        fresh task (module E). A factory (not an inline lambda in the registry) so
        each family closes over *its own* ``cond_type``/``analyze_fn`` with no
        late-binding capture bug."""
        return lambda task: {cond_type: analyze_fn(task.example_pairs)}

    def _reuse_abstract_rule(self, entry, task):
        """Activate a stored *abstract* rule on ``task`` and return its test
        predictions, or None when it does not apply.

        The reuse loop the legacy applier could not express (BACKLOG_LOOP §2.5-2b,
        R5): a lifted ``covers>1`` rule is a program with a *hole* (its ``?vN``
        variable). To run it on a fresh task its filler must be chosen from *this*
        task's comparison evidence, not the source task's. Steps:

        1. **Activation** — the stored rule's own ``condition`` matcher must fire on
           the task's patterns (module E: a learned rule recognises a new task).
        2. **Resolution + render** — the family's render_fn recomputes the variable
           from the task's example COMM and renders (the §2.5-2b "fill the hole from
           COMM" step). This is reuse of the *abstraction*, not Slow-path rediscovery.
        3. **Safety gate** — the resolved program must reproduce *every* example
           output exactly; otherwise we decline and the Slow path runs unchanged, so
           reuse can never turn a solved task into a wrong answer (only skip a reuse).
        """
        action = entry.get("action") or {}
        condition = entry.get("condition") or {}
        spec = self._abstract_reuse.get(action.get("dsl"))
        if spec is None:
            return None
        cond_type, patterns_fn, render_fn = spec
        if condition.get("type") != cond_type:
            return None

        # 1. Activation: the stored rule's condition matcher fires on this task.
        try:
            if not match_condition(cond_type, patterns_fn(task),
                                   condition.get("params") or {}):
                return None
        except KeyError:
            return None

        # 3. Safety gate: the resolved abstraction reproduces every example output.
        if not self._reproduces_examples(render_fn, task):
            return None

        # 2. Render the test predictions from the (now resolved) abstraction.
        grids = render_fn(task)
        predicted = []
        for i in range(len(task.test_pairs)):
            if grids.get(i) is None:
                return None
            predicted.append(grids[i])
        return predicted or None

    @staticmethod
    def _reproduces_examples(render_fn, task) -> bool:
        """True iff the abstraction renders *every* example input back to its known
        output. The render_fn learns from ``example_pairs`` and renders
        ``test_pairs``; pointing both at the example pairs makes it predict the
        examples, which we check against their actual outputs (the §2.5-2b verify
        step that keeps reuse honest)."""
        examples = list(task.example_pairs)
        if not examples:
            return False
        shim = SimpleNamespace(example_pairs=examples, test_pairs=examples)
        rendered = render_fn(shim)
        for i, pair in enumerate(examples):
            if pair.output_grid is None or rendered.get(i) != pair.output_grid.raw:
                return False
        return True

    # ---- place_object reuse: resolve the ?v0 reading-hole from COMM ------

    def _place_object_render(self, task):
        """Render the place_object family abstraction by first *resolving* its
        ``?v0`` reading-hole from the task's own comparison evidence (BACKLOG_LOOP
        §2.5-2b, R5).

        The lifted ``place_object`` rule is incomplete: its target is one of five
        readings (constant_target / constant_offset / constant_corner /
        constant_resize / constant_select) and *which* one grounds a given task is
        not stored — it must be chosen from the task's COMM/DIFF (P3/P4: reason,
        not value). We try each reading's renderer in turn and keep the first that
        reproduces *every* example output; that reproduction check is the COMM-
        grounded choice of filler. The chosen renderer then renders the test pairs.
        Returns {} when no reading reproduces the examples (reuse then declines and
        the Slow path runs unchanged — reuse can only skip, never break).

        The renderers are the *same* ones the Slow path uses, so a resolved reuse
        renders identically to a fresh derivation — it just skips the rediscovery.
        """
        readings = [
            self._predictor._place_object_grids,          # constant_target
            self._predictor._place_object_offset_grids,   # constant_offset
            self._predictor._place_object_corner_grids,   # constant_corner
            self._predictor._place_object_resize_grids,   # constant_resize
            self._predictor._place_object_select_grids,   # constant_select
        ]
        for render in readings:
            if self._reproduces_examples(render, task):
                return render(task)
        return {}

    # ---- helpers --------------------------------------------------------

    def _rule_matches_examples(self, rule, task) -> bool:
        """Check if a rule reproduces output for ALL example pairs.

        Dispatches by rule shape. A *canonical* ``{condition, action}`` rule is
        reproduced through the predict pipeline (``_canonical_rule_reproduces``);
        the legacy ``_apply_rule`` only knows the three legacy typed rules and
        returns ``None`` for every canonical one, which silently barred every
        canonical family from the learn-save gate — and so from R3 lift and R5
        reuse (memory ``canonical_rules_never_persist``). Legacy ``{type, ...}``
        rules keep the original ``_apply_rule`` path unchanged."""
        action = rule.get("action") if isinstance(rule, dict) else None
        if action and action.get("dsl"):
            return self._canonical_rule_reproduces(rule, task)
        for pair in task.example_pairs:
            if pair.input_grid is None or pair.output_grid is None:
                continue
            predicted = self._predictor._apply_rule(rule, pair.input_grid)
            if predicted is None or predicted != pair.output_grid.raw:
                return False
        return True

    def _canonical_rule_reproduces(self, rule, task) -> bool:
        """Reproduce a *canonical* ``{condition, action}`` rule against the task's
        own example pairs **via the predict pipeline** (PredictOperator's
        per-family renderers), not the legacy ``_apply_rule``.

        Why this exists (BACKLOG_LOOP R3/R5; iter20 Next-gap; memory
        ``canonical_rules_never_persist``): the learn-save gate validated a
        discovered rule with ``_apply_rule``, which only knows the three legacy
        typed rules and returns ``None`` for every canonical rule. So a canonical
        family rule silently failed the gate and was *never saved* — therefore
        never lifted by anti-unification (R3) nor reused by the Fast path (R5).
        Routing the gate through the same renderer the predictor uses lets a
        canonical rule that genuinely reproduces its train pairs persist (then be
        absorbed into / lifted with its siblings) the intended way, with no new
        liftless accretion: a discovered concrete reading is absorbed by the
        family abstraction it already ranges over (memory.py ``_abstract_absorbs``).

        The render shim points ``test_pairs`` at the example pairs (the §2.5-2b
        verify trick already used by ``_reproduces_examples``): the renderer learns
        its parameters from the examples and renders them back, which we check
        against the known example outputs. Reuses the canonical predict dispatch
        wholesale (PredictOperator.effect) rather than duplicating it."""
        action = rule.get("action") if isinstance(rule, dict) else None
        if not action or not action.get("dsl"):
            return False
        examples = [
            p for p in task.example_pairs
            if p.input_grid is not None and p.output_grid is not None
        ]
        if not examples:
            return False
        shim = SimpleNamespace(
            task_hex=getattr(task, "task_hex", None),
            example_pairs=examples,
            test_pairs=examples,
        )
        wm = SimpleNamespace(task=shim, s1={"active-rules": [rule]})
        self._predictor.effect(wm)
        predictions = wm.s1.get("predictions") or {}
        for i, pair in enumerate(examples):
            if predictions.get(f"test_{i}") != pair.output_grid.raw:
                return False
        return True

    def _apply_rule_to_tests(self, rule, task) -> list:
        """Apply a rule to all test inputs. Returns list of predicted grids."""
        grids = []
        for test_pair in task.test_pairs:
            if test_pair.input_grid is None:
                return None
            predicted = self._predictor._apply_rule(rule, test_pair.input_grid)
            if predicted is None:
                return None
            grids.append(predicted)
        return grids

    @staticmethod
    def _extract_prediction(wm) -> list:
        """Extract predicted grids from WM output-link."""
        try:
            s1 = wm.s1.get("S1")
            if not s1:
                return None
            output_link_id = s1.get("output-link")
            if not output_link_id:
                return None
            output_node = wm.s1.get(output_link_id)
            if not output_node:
                return None
            return output_node.get("predicted-grid")
        except Exception:
            return None

    @property
    def can_retry(self) -> bool:
        return self._submission_count < 3
