"""
claude_solver.py -- Claude Code CLI as last-resort solver.

When the SOAR pipeline fails to find a matching concept, this module
calls Claude Code (via `claude -p`) to analyze the task and generate
a concept JSON. The concept is saved and validated against examples.

Flow:
  1. Build a prompt with task grids + available primitives + concept format
  2. Call `claude -p --permission-mode bypassPermissions` via subprocess
  3. Parse the response for a JSON concept (or detect concepts Claude wrote to disk)
  4. Reload concept engine and validate against examples
"""

import json
import os
import re
import subprocess
import sys
import glob


def try_claude_solve(task, patterns, comparisons, procedural_root="procedural_memory"):
    """
    Last-resort solver: asks Claude Code to generate a concept JSON.

    Returns:
        rule dict ({"type": "concept:...", ...}) if Claude succeeds, else None
    """
    concepts_dir = os.path.join(procedural_root, "concepts")
    os.makedirs(concepts_dir, exist_ok=True)

    # Snapshot existing concepts before calling Claude
    before = set(glob.glob(os.path.join(concepts_dir, "*.json")))

    prompt = _build_prompt(task, patterns, comparisons, procedural_root)

    print(f"[CLAUDE] Calling Claude for task {task.task_hex}...")

    try:
        response = _call_claude(prompt)
    except subprocess.TimeoutExpired:
        print(f"[CLAUDE] Timeout (task {task.task_hex})", file=sys.stderr)
        response = ""
    except Exception as e:
        print(f"[CLAUDE] CLI call failed: {e}", file=sys.stderr)
        response = ""

    # Check for new concepts Claude wrote directly to disk
    after = set(glob.glob(os.path.join(concepts_dir, "*.json")))
    new_files = after - before

    # Also try to parse concept from stdout response
    if response:
        concept = _parse_concept_json(response)
        if concept and concept.get("concept_id"):
            concept_id = concept["concept_id"]
            concept_path = os.path.join(concepts_dir, f"{concept_id}.json")
            if concept_path not in new_files:
                with open(concept_path, "w") as f:
                    json.dump(concept, f, indent=2)
                new_files.add(concept_path)
                print(f"[CLAUDE] Parsed concept from response: {concept_id}")

    if not new_files:
        print(f"[CLAUDE] No concepts generated for {task.task_hex}")
        return None

    print(f"[CLAUDE] {len(new_files)} new concept(s) found")

    # Reload concept engine and try matching
    rule = _reload_and_match(patterns, task)
    if rule:
        print(f"[CLAUDE] Matched concept: {rule.get('concept_id', rule.get('type', '?'))}")
        return rule

    print(f"[CLAUDE] No concept matched task {task.task_hex} after generation")
    return None


def _build_prompt(task, patterns, comparisons, procedural_root):
    """Build a focused prompt for Claude with task data and available tools."""
    # Format example grids
    examples_text = ""
    for idx, pair in enumerate(task.example_pairs):
        inp = pair.input_grid.raw if pair.input_grid else []
        out = pair.output_grid.raw if pair.output_grid else []
        examples_text += f"\nExample {idx + 1}:\n"
        examples_text += f"  Input  ({len(inp)}x{len(inp[0]) if inp else 0}):\n"
        for row in inp:
            examples_text += f"    {row}\n"
        examples_text += f"  Output ({len(out)}x{len(out[0]) if out else 0}):\n"
        for row in out:
            examples_text += f"    {row}\n"

    # Format test inputs
    tests_text = ""
    for idx, pair in enumerate(task.test_pairs):
        inp = pair.input_grid.raw if pair.input_grid else []
        tests_text += f"\nTest {idx + 1} Input ({len(inp)}x{len(inp[0]) if inp else 0}):\n"
        for row in inp:
            tests_text += f"    {row}\n"

    # Pattern summary
    pattern_text = ""
    if patterns:
        pattern_text = f"Grid size preserved: {patterns.get('grid_size_preserved', '?')}\n"
        for idx, pa in enumerate(patterns.get("pair_analyses", [])):
            pattern_text += f"  Pair {idx}: {pa.get('total_changes', 0)} changed cells, {pa.get('num_groups', 0)} groups\n"

    # List existing concepts so Claude doesn't duplicate
    existing = []
    concepts_dir = os.path.join(procedural_root, "concepts")
    if os.path.isdir(concepts_dir):
        existing = [f.replace(".json", "") for f in os.listdir(concepts_dir) if f.endswith(".json")]

    existing_text = ", ".join(existing[:30]) if existing else "none"

    prompt = f"""You are solving ARC task {task.task_hex}. Analyze the input→output transformation and create a concept JSON file.

TASK DATA:
{examples_text}
{tests_text}

EXTRACTED PATTERNS:
{pattern_text}

ALREADY EXISTING CONCEPTS (do not duplicate): {existing_text}

Create a concept JSON file at procedural_memory/concepts/<name>.json.

The concept JSON format:
{{
  "concept_id": "<descriptive_name>",
  "version": 1,
  "description": "One-line description",
  "signature": {{
    "grid_size_preserved": true/false
  }},
  "parameters": {{
    "param_name": {{"type": "int|color|color_map", "infer": "method_name"}}
  }},
  "steps": [
    {{"id": "s1", "primitive": "fn_name", "args": {{"grid": "$input", ...}}, "output": "result"}}
  ],
  "result": "$result"
}}

Available primitives: Read procedural_memory/base_rules/_primitives.py for the full list.
Available inference methods: bg_color, ratio_hw, color_map_from_arckg, non_bg_single, from_examples, separator_color, color_added_in_output, source_color_from_arckg, start_color_from_arckg

Rules:
- "$input" = input grid, "$param_name" = inferred parameter
- Do NOT hardcode colors or positions — use parameter inference
- If no existing primitive fits, add a new one to _primitives.py
- The concept must work for ALL examples, not just one
- Create exactly ONE concept file that solves this task"""

    return prompt


def _call_claude(prompt, timeout=300):
    """Call Claude Code CLI and return response text."""
    result = subprocess.run(
        [
            "claude", "-p", prompt,
            "--permission-mode", "bypassPermissions",
            "--output-format", "text",
        ],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=os.getcwd(),
        shell=(sys.platform == "win32"),
    )
    if result.returncode != 0:
        stderr = result.stderr.strip()
        if stderr:
            print(f"[CLAUDE] stderr: {stderr[:200]}", file=sys.stderr)
    return result.stdout.strip()


def _parse_concept_json(response):
    """Extract a concept JSON from Claude's response."""
    # Try ```json ... ``` block
    match = re.search(r'```json\s*\n(.*?)\n```', response, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try any ``` block containing concept_id
    match = re.search(r'```\s*\n(\{.*?"concept_id".*?\})\n```', response, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try whole response as JSON
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    return None


def _reload_and_match(patterns, task):
    """Force-reload concept engine and try matching against the task."""
    try:
        from procedural_memory.base_rules import _concept_engine
        _concept_engine._loaded = False
        _concept_engine._concepts = []
    except Exception:
        pass

    try:
        from agent.rule_engine import try_all
        rule = try_all(patterns, task)
        if rule and rule.get("type", "identity") != "identity":
            return rule
    except Exception as e:
        print(f"[CLAUDE] Validation error: {e}", file=sys.stderr)

    return None
