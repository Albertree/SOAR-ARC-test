"""
Test Case 1: Solve each training pair independently -> Claude finds common structure.
Baseline. Expected failure: when pair solutions are structurally dissimilar.
"""
import json


def solve_single_pair_prompt(pair_input, pair_output, other_pairs_context):
    return f"""Describe the transformation mapping this ARC input to its output.

Context (other training pairs):
{json.dumps(other_pairs_context, indent=2)}

Target:
Input: {json.dumps(pair_input)}
Output: {json.dumps(pair_output)}

Be specific (what changed, where, pattern) and abstract
(use "non-background color" not specific color values like "3" or "blue")."""


def antiunify_prompt(rule_0, rule_1):
    return f"""Two rule descriptions each solve one training pair.

Rule for Pair 0:
{rule_0}

Rule for Pair 1:
{rule_1}

Write ONE general rule that works for BOTH pairs. Replace any task-specific
values with abstract descriptions. The rule must be unambiguously applicable
to a new input grid."""


def apply_rule_prompt(general_rule, test_input, training_examples):
    return f"""Apply this rule to the test input.

Rule: {general_rule}

Training examples:
{json.dumps(training_examples, indent=2)}

Test input: {json.dumps(test_input)}

Output ONLY the result grid as a JSON array of arrays. Example: [[0,1],[2,3]]"""
