"""
Claude-assisted program solving and concept generation.

Used when brute-force solver fails or AU templates need concept JSONs.
All Claude calls use the Anthropic API via urllib (no SDK dependency).
"""
import json
import os
import inspect


def _call_claude(prompt, max_tokens=2000):
    """Call Claude API. Returns response text or raises."""
    import urllib.request

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    payload = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}]
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST"
    )

    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())

    return "".join(
        block["text"] for block in data.get("content", [])
        if block.get("type") == "text"
    )


def _render_grid(raw):
    return "\n".join(" ".join(str(c) for c in row) for row in raw)


def _available_primitives():
    from procedural_memory.base_rules import _primitives as P
    prims = {}
    for name, fn in inspect.getmembers(P, inspect.isfunction):
        if name.startswith("_"):
            continue
        prims[name] = str(inspect.signature(fn))
    return prims


def solve_pair_with_claude(input_raw, output_raw, task_hex, pair_idx):
    """Ask Claude to find a program for one pair. Returns program dict or None."""
    prims = _available_primitives()
    prim_list = "\n".join(f"  {n}{s}" for n, s in sorted(prims.items()))

    prompt = f"""You are solving one training pair of ARC task {task_hex}, pair {pair_idx}.

Input grid:
{_render_grid(input_raw)}

Output grid:
{_render_grid(output_raw)}

Available primitives:
{prim_list}

Express the transformation as primitive calls. Use "$input" for the input grid.
Respond with ONLY valid JSON:
{{"steps": [{{"primitive": "name", "args": {{"grid": "$input"}}, "output": "result"}}]}}

If you cannot express it, respond: {{"error": "cannot express"}}"""

    try:
        response = _call_claude(prompt)
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            response = response.split("```")[1].split("```")[0]

        data = json.loads(response.strip())
        if "error" in data or "steps" not in data:
            return None

        # Validate by execution
        from procedural_memory.base_rules import _primitives as P
        env = {"input": input_raw}
        for step in data["steps"]:
            fn = getattr(P, step["primitive"], None)
            if fn is None:
                return None
            resolved = {}
            for k, v in step["args"].items():
                if isinstance(v, str) and v.startswith("$"):
                    resolved[k] = env.get(v[1:], v)
                else:
                    resolved[k] = v
            result = fn(**resolved)
            env[step["output"]] = result

        if env.get("result") != output_raw:
            return None

        return {
            "concept_id": "claude_generated",
            "params": {},
            "steps": data["steps"],
            "source": "claude",
        }
    except Exception:
        return None


def template_to_concept_json(template, task_hex, all_pair_programs):
    """Convert an AU template into a concept JSON via Claude."""
    # Build variable value table
    var_values = {}
    for prog in all_pair_programs:
        if prog is None:
            continue
        for step in prog["steps"]:
            for k, v in step["args"].items():
                for t_step in template["steps"]:
                    if t_step["primitive"] == step["primitive"]:
                        t_val = t_step["args"].get(k)
                        if isinstance(t_val, str) and t_val.startswith("?var_"):
                            var_values.setdefault(t_val, []).append(v)

    prims_used = list({s["primitive"] for s in template["steps"]})
    from procedural_memory.base_rules import _primitives as P
    prim_sigs = {n: str(inspect.signature(getattr(P, n))) for n in prims_used if hasattr(P, n)}

    # Add grid examples
    grid_examples = ""
    try:
        from managers.arc_manager import ARCManager
        t = ARCManager().load_task(task_hex)
        for i, pair in enumerate(t.example_pairs[:2]):
            grid_examples += f"\nPair {i} input:\n{_render_grid(pair.input_grid.raw)}\n"
            grid_examples += f"Pair {i} output:\n{_render_grid(pair.output_grid.raw)}\n"
    except Exception:
        pass

    infer_methods = [
        "bg_color - most frequent color",
        "non_bg_single - single non-background color",
        "color_map_from_arckg - consistent {old:new} mapping",
        "from_examples - brute force values 0-9",
    ]

    prompt = f"""Convert this AU template into a concept JSON.

Task: {task_hex}
{grid_examples}
AU template steps:
{json.dumps(template["steps"], indent=2)}

Variables (values across pairs):
{json.dumps(var_values, indent=2, default=str)}

Primitive signatures: {json.dumps(prim_sigs)}

Inference methods: {chr(10).join(f"  {m}" for m in infer_methods)}

Write a concept JSON with proper signature and parameter inference.
Respond with ONLY the JSON."""

    try:
        response = _call_claude(prompt, max_tokens=1500)
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            response = response.split("```")[1].split("```")[0]
        concept = json.loads(response.strip())
        if not all(k in concept for k in ["concept_id", "steps", "result"]):
            return None
        return concept
    except Exception:
        return None


def au_merge_with_claude(template_a, template_b, task_hexes):
    """Merge two similar AU templates into one general concept via Claude."""
    prompt = f"""Two ARC tasks solved by similar programs. Produce ONE concept JSON covering both.

Tasks: {task_hexes}

Template A: {json.dumps(template_a["steps"], indent=2)}
Template B: {json.dumps(template_b["steps"], indent=2)}
A variables: {template_a["variables"]}
B variables: {template_b["variables"]}

Write a concept JSON parameterizing anything that differs.
Respond with ONLY the JSON."""

    try:
        response = _call_claude(prompt, max_tokens=1500)
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            response = response.split("```")[1].split("```")[0]
        return json.loads(response.strip())
    except Exception:
        return None
