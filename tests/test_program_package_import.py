"""
Regression test for the `program` package's public interface.

`program/__init__.py` previously re-exported a name (`anti_unify`) that does
NOT exist in `program/anti_unification.py` (the real functions are
`anti_unify_pair_programs` / `anti_unify_terms` / `program_lines_to_terms` /
`terms_to_program_lines`). Because Python runs a package's `__init__.py` before
importing any submodule, that broken re-export made *both* `import program` and
`from program.anti_unification import <anything>` raise `ImportError` — i.e. the
entire anti-unification package (CLAUDE.md §8, module H) was unreachable. This
locks the fix: the package imports and its `__all__` names resolve to real
callables.

pytest is not installed in this environment, so the file is also runnable
directly:  python tests/test_program_package_import.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_passed = 0
_failed = 0


def check(name, cond):
    global _passed, _failed
    if cond:
        _passed += 1
    else:
        _failed += 1
        print(f"  FAIL: {name}")


# --- the package itself imports (the regression) --------------------------

import program  # noqa: E402  — must not raise ImportError

check("import program succeeds", program is not None)

# Importing a submodule also runs program/__init__.py first, so this is the
# second symptom of the same bug.
from program import anti_unification  # noqa: E402

check("submodule import succeeds", anti_unification is not None)

# --- __all__ is accurate: every advertised name resolves to a callable ----

expected = {
    "anti_unify_pair_programs",
    "anti_unify_terms",
    "program_lines_to_terms",
    "terms_to_program_lines",
}

check("__all__ matches the real public functions", set(program.__all__) == expected)

for name in expected:
    check(f"program.{name} is callable", callable(getattr(program, name, None)))

# The non-existent name must NOT be advertised again.
check("anti_unify (non-existent) not re-exported", not hasattr(program, "anti_unify"))

# Each advertised name is the same object as the submodule's, i.e. a genuine
# re-export, not a shadowing stub.
for name in expected:
    check(
        f"program.{name} is anti_unification.{name}",
        getattr(program, name) is getattr(anti_unification, name),
    )


print(f"\ntest_program_package_import: {_passed} passed, {_failed} failed")
sys.exit(1 if _failed else 0)
