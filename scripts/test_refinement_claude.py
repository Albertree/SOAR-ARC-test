"""
Test Case 3: Solve Pair 0 -> refine via Claude failure feedback until all pairs pass.
Expected failure: when Pair 0 solution is structurally incompatible with Pair 1.
"""
import json


def _diff_summary(predicted, expected, max_cells=10):
    diffs = []
    for r, (pr, er) in enumerate(zip(predicted, expected)):
        for c, (pv, ev) in enumerate(zip(pr, er)):
            if pv != ev:
                diffs.append(f"  row {r}, col {c}: got {pv}, expected {ev}")
    if len(diffs) > max_cells:
        diffs = diffs[:max_cells] + [f"  ...and {len(diffs) - max_cells} more"]
    return "\n".join(diffs) if diffs else "  (all cells match)"


def initial_solve_prompt(pair_input, pair_output):
    return f"""Describe the transformation rule for this ARC pair.

Input: {json.dumps(pair_input)}
Output: {json.dumps(pair_output)}

Be specific and abstract. Avoid naming specific color numbers."""


def refinement_prompt(current_rule, failing_pair_input, failing_pair_output,
                      predicted_output, passing_summaries):
    return f"""This rule works for some pairs but fails on another.

Current rule:
{current_rule}

Passing pairs: {passing_summaries}

Failing pair:
Input:    {json.dumps(failing_pair_input)}
Expected: {json.dumps(failing_pair_output)}
Got:      {json.dumps(predicted_output)}

Wrong cells:
{_diff_summary(predicted_output, failing_pair_output)}

Rewrite the rule to work for BOTH the passing pairs AND this failing pair.
If the failure suggests the rule was too specific, generalize.
If it was structurally wrong, correct the structure."""


def apply_rule_prompt(rule, test_input, examples):
    return f"""Apply this rule to the test input.

Rule: {rule}
Training examples: {json.dumps(examples, indent=2)}
Test input: {json.dumps(test_input)}

Output ONLY the result grid as a JSON array of arrays."""
