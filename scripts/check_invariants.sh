#!/bin/bash
# scripts/check_invariants.sh
#
# Enforces docs/INVARIANTS.md.
#
# Usage:
#   ./scripts/check_invariants.sh --snapshot <path>     # capture baseline
#   ./scripts/check_invariants.sh --check    <path>     # diff against baseline
#
# Exit codes (check mode):
#   0 — clean: no forbidden signal hit; ≥1 positive delta ≥ 0
#   1 — forbidden signal tripped (caller should `git revert HEAD`)
#   2 — neutral: no forbidden, no positive improvement either

set -u
MODE="${1:-}"
SNAPSHOT_PATH="${2:-logs/_invariant_snapshot.json}"

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT" || exit 99

# ─── interpreter detection ───────────────────────────────────────────
# On Windows hosts, `python3` is typically the Microsoft Store stub: it
# exits with rc=49 without executing any script (prints only "Python"),
# which would silently zero every metric below. Prefer an interpreter
# that actually runs a one-liner. Honour $PYTHON_BIN if the caller pinned
# one explicitly.
if [ -n "${PYTHON_BIN:-}" ]; then
    :
else
    PYTHON_BIN=""
    for candidate in python3 python; do
        if command -v "$candidate" >/dev/null 2>&1 \
            && "$candidate" -c "import sys; sys.exit(0)" >/dev/null 2>&1; then
            PYTHON_BIN="$candidate"
            break
        fi
    done
fi
if [ -z "${PYTHON_BIN:-}" ]; then
    echo "[invariants] no working python interpreter found (tried python3, python)" >&2
    exit 99
fi

# ─── metric computation (pure python, no external deps) ──────────────
compute_metrics() {
    "$PYTHON_BIN" - <<'PYEOF'
import json, os, glob, re, sys
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

metrics = {}

# P1, P2, P3 — rule-coverage family
rule_files = sorted(glob.glob("procedural_memory/rule_*.json"))
solved_tasks = set()
covers_lens = []
au_traced = 0
total = 0
for path in rule_files:
    try:
        with open(path, encoding="utf-8") as f:
            r = json.load(f)
    except (OSError, json.JSONDecodeError):
        continue
    total += 1
    covers = r.get("covers", [])
    if isinstance(covers, list):
        covers_lens.append(len(covers))
        for t in covers:
            solved_tasks.add(t)
    if r.get("anti_unification_trace"):
        au_traced += 1

metrics["P1_rule_coverage"] = (len(solved_tasks) / total) if total else 0.0
metrics["P2_mean_covers"]   = (sum(covers_lens) / total) if total else 0.0
metrics["P3_au_traced_frac"]= (au_traced / total) if total else 0.0
metrics["_rule_count"]      = total
metrics["_solved_count"]    = len(solved_tasks)

# P4 — episodic memory entries
ep_count = 0
if os.path.isdir("episodic_memory"):
    for root, dirs, files in os.walk("episodic_memory"):
        # count attempt_NNN folders
        for d in dirs:
            if re.match(r"^attempt_\d+$", d):
                ep_count += 1
metrics["P4_episodic_entries"] = ep_count

# P5 — registered condition matchers
cond_count = 0
init_path = "agent/conditions/__init__.py"
if os.path.isfile(init_path):
    try:
        # parse-by-import would import side effects; just scan text
        with open(init_path, encoding="utf-8") as f:
            src = f.read()
        cond_count = len(re.findall(r'@register\(', src))
        # also count modules registered via decorator in agent/conditions/*.py
        for p in glob.glob("agent/conditions/*.py"):
            if p.endswith("__init__.py"):
                continue
            with open(p, encoding="utf-8") as f:
                cond_count += len(re.findall(r'@register\(', f.read()))
    except OSError:
        pass
metrics["P5_condition_matchers"] = cond_count

# P6 — active_operators.py line count (lower is better)
ao_lines = 0
if os.path.isfile("agent/active_operators.py"):
    with open("agent/active_operators.py", encoding="utf-8") as f:
        ao_lines = sum(1 for _ in f)
metrics["P6_active_operators_lines"] = ao_lines

# Bookkeeping
import subprocess
try:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
except subprocess.CalledProcessError:
    head = ""
metrics["_head"] = head

json.dump(metrics, sys.stdout, indent=2, sort_keys=True)
PYEOF
}

# ─── snapshot mode ───────────────────────────────────────────────────
if [ "$MODE" = "--snapshot" ]; then
    mkdir -p "$(dirname "$SNAPSHOT_PATH")"
    if ! compute_metrics > "$SNAPSHOT_PATH"; then
        rc=$?
        echo "[invariants] snapshot failed (rc=$rc); removing partial $SNAPSHOT_PATH" >&2
        rm -f "$SNAPSHOT_PATH"
        exit "$rc"
    fi
    if [ ! -s "$SNAPSHOT_PATH" ]; then
        echo "[invariants] snapshot produced empty output — refusing to write 0-byte file" >&2
        rm -f "$SNAPSHOT_PATH"
        exit 99
    fi
    echo "[invariants] snapshot saved to $SNAPSHOT_PATH"
    exit 0
fi

# ─── check mode ──────────────────────────────────────────────────────
if [ "$MODE" != "--check" ]; then
    echo "Usage: $0 --snapshot <path>   |   $0 --check <path>" >&2
    exit 99
fi

if [ ! -f "$SNAPSHOT_PATH" ]; then
    echo "[invariants] no snapshot at $SNAPSHOT_PATH — cannot check" >&2
    exit 99
fi

BASE_HEAD=$("$PYTHON_BIN" -c "import json; print(json.load(open('$SNAPSHOT_PATH'))['_head'])")
if [ -z "$BASE_HEAD" ]; then
    BASE_HEAD="HEAD~1"
fi

violations=()

# F1 — Frozen files
F1_OUT=$(git diff "$BASE_HEAD" -- \
    data/ \
    agent/cycle.py \
    agent/wm.py \
    ARCKG/task.py ARCKG/pair.py ARCKG/grid.py ARCKG/object.py ARCKG/pixel.py \
    2>/dev/null)
if [ -n "$F1_OUT" ]; then
    violations+=("F1: frozen file modified")
fi

# F2 — new _try_* / _apply_*
F2_OUT=$(git diff "$BASE_HEAD" -- agent/active_operators.py 2>/dev/null \
    | grep -E "^\+\s*def _(try|apply)_" || true)
if [ -n "$F2_OUT" ]; then
    violations+=("F2: new _try_*/_apply_* method")
fi

# F3 — hand-coded DSL primitive added (anything other than coloring/make_grid)
F3_OUT=$(git diff "$BASE_HEAD" -- 'procedural_memory/DSL/*.py' 2>/dev/null \
    | grep -E "^\+.*@.*register\(" \
    | grep -vE 'register\("(coloring|make_grid)"\)' \
    | grep -vE "register\('(coloring|make_grid)'\)" || true)
# also catch new def in DSL/*.py that aren't coloring/make_grid
F3_DEF_OUT=$(git diff "$BASE_HEAD" -- 'procedural_memory/DSL/*.py' 2>/dev/null \
    | grep -E "^\+\s*def " \
    | grep -vE "def (coloring|make_grid|apply_DSL|register|_)" || true)
if [ -n "$F3_OUT" ] || [ -n "$F3_DEF_OUT" ]; then
    violations+=("F3: hand-coded DSL primitive added")
fi

# F4 — rule without condition key
F4_BAD=""
for f in procedural_memory/rule_*.json; do
    [ -e "$f" ] || continue
    if ! "$PYTHON_BIN" -c "
import json, sys
try:
    with open('$f', encoding='utf-8') as _fp:
        r = json.load(_fp)
except Exception as e:
    print('parse error: $f:', e); sys.exit(1)
if 'condition' not in r or 'action' not in r:
    print('$f'); sys.exit(1)
" >/dev/null 2>&1; then
        F4_BAD="$F4_BAD $f"
    fi
done
if [ -n "$F4_BAD" ]; then
    violations+=("F4: rule(s) missing condition/action key:$F4_BAD")
fi

# F5 — TF_GRID under semantic_memory (check git diff for new TF_ paths only;
#       full filesystem walk is too slow once semantic_memory holds 1k+ tasks)
F5_OUT=$(git diff "$BASE_HEAD" --name-only --diff-filter=A 2>/dev/null \
    | grep -E "^semantic_memory/.*[Tt][Ff]_" || true)
if [ -n "$F5_OUT" ]; then
    violations+=("F5: TF_GRID artifact added under semantic_memory/ ($F5_OUT)")
fi

# F6 — auto-grown --limit
F6_OUT=$(git diff "$BASE_HEAD" -- run_loop.sh run_pipeline.sh run_learn.py run_1ktasks.py 2>/dev/null \
    | grep -E "^\+.*(TASKS_PER_SESSION\s*=\s*\(?TASKS_PER_SESSION|limit\s*\*=|limit\s*=\s*limit\s*\*)" || true)
if [ -n "$F6_OUT" ]; then
    violations+=("F6: auto-grow of task budget reintroduced")
fi

# F7 — RuleSchemaError swallowed
F7_OUT=$(git diff "$BASE_HEAD" -- agent/ scripts/ procedural_memory/ 2>/dev/null \
    | grep -B1 -A3 "except.*RuleSchemaError" \
    | grep -E "^\+.*\b(pass|continue)\b" || true)
if [ -n "$F7_OUT" ]; then
    # only fail if not followed by raise in same block (heuristic: look for raise nearby)
    if ! git diff "$BASE_HEAD" -- agent/ scripts/ procedural_memory/ 2>/dev/null \
        | grep -A5 "except.*RuleSchemaError" | grep -q "raise"; then
        violations+=("F7: RuleSchemaError swallowed without re-raise")
    fi
fi

# F8 — active_operators grew without anti-unification-side companion
AO_NUMSTAT=$(git diff "$BASE_HEAD" --numstat -- agent/active_operators.py 2>/dev/null)
if [ -n "$AO_NUMSTAT" ]; then
    added=$(echo "$AO_NUMSTAT" | awk '{print $1}')
    deleted=$(echo "$AO_NUMSTAT" | awk '{print $2}')
    net=$(( ${added:-0} - ${deleted:-0} ))
    if [ "$net" -gt 0 ]; then
        # must also touch one of: memory.py, anti_unification.py, conditions/
        companion=$(git diff "$BASE_HEAD" --name-only 2>/dev/null \
            | grep -E "^(agent/memory\.py|program/anti_unification\.py|agent/conditions/)" || true)
        if [ -z "$companion" ]; then
            violations+=("F8: active_operators.py grew (+$net) without anti-unification-side companion edit")
        fi
    fi
fi

# ─── report ──────────────────────────────────────────────────────────
echo
echo "════ invariant check ════"
echo "base HEAD: $BASE_HEAD"

if [ ${#violations[@]} -gt 0 ]; then
    echo
    echo "FORBIDDEN signals tripped:"
    for v in "${violations[@]}"; do
        echo "  ✗ $v"
    done
    echo
    echo "verdict: VIOLATION (caller should revert)"
    exit 1
fi

# Positive-signal deltas
echo
echo "Positive signals (after − before):"
"$PYTHON_BIN" - "$SNAPSHOT_PATH" <<'PYEOF'
import json, sys, subprocess
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

with open(sys.argv[1], encoding="utf-8") as _f:
    before = json.load(_f)
# recompute now
result = subprocess.run([sys.executable, "-c", """
import json, os, glob, re, sys
metrics={}
rule_files = sorted(glob.glob('procedural_memory/rule_*.json'))
solved=set(); covers=[]; au=0; total=0
for p in rule_files:
    try:
        with open(p, encoding='utf-8') as _f: r=json.load(_f)
    except: continue
    total+=1
    cv=r.get('covers',[])
    if isinstance(cv,list):
        covers.append(len(cv))
        for t in cv: solved.add(t)
    if r.get('anti_unification_trace'): au+=1
metrics['P1_rule_coverage']=(len(solved)/total) if total else 0.0
metrics['P2_mean_covers']=(sum(covers)/total) if total else 0.0
metrics['P3_au_traced_frac']=(au/total) if total else 0.0
ep=0
if os.path.isdir('episodic_memory'):
    for _,dirs,_ in os.walk('episodic_memory'):
        ep+=sum(1 for d in dirs if re.match(r'^attempt_\\d+$',d))
metrics['P4_episodic_entries']=ep
cc=0
ip='agent/conditions/__init__.py'
if os.path.isfile(ip):
    with open(ip, encoding='utf-8') as _f: cc+=len(re.findall(r'@register\\(',_f.read()))
for p in glob.glob('agent/conditions/*.py'):
    if p.endswith('__init__.py'): continue
    with open(p, encoding='utf-8') as _f: cc+=len(re.findall(r'@register\\(',_f.read()))
metrics['P5_condition_matchers']=cc
al=0
if os.path.isfile('agent/active_operators.py'):
    with open('agent/active_operators.py', encoding='utf-8') as _f:
        al=sum(1 for _ in _f)
metrics['P6_active_operators_lines']=al
print(json.dumps(metrics))
"""], capture_output=True, text=True)
if result.returncode != 0 or not result.stdout.strip():
    sys.stderr.write("[invariants] post-check recompute failed:\\n")
    sys.stderr.write(result.stderr or "(no stderr)\\n")
    sys.exit(99)
after = json.loads(result.stdout)

keys = ["P1_rule_coverage", "P2_mean_covers", "P3_au_traced_frac",
        "P4_episodic_entries", "P5_condition_matchers", "P6_active_operators_lines"]

# P6 improvement direction is inverted (lower = better)
inverted = {"P6_active_operators_lines"}

improved = 0
deltas = []
for k in keys:
    b = before.get(k, 0)
    a = after.get(k, 0)
    d = a - b
    if k in inverted:
        d = -d  # show as "lines removed"
    deltas.append((k, b, a, d))
    if d > 0:
        improved += 1

for k, b, a, d in deltas:
    arrow = "↑" if d > 0 else ("↓" if d < 0 else "·")
    suffix = " (lines removed)" if k == "P6_active_operators_lines" else ""
    print(f"  {arrow} {k:30s} {b!r:>10} → {a!r:<10}  Δ={d:+}{suffix}")

print()
if improved > 0:
    print(f"verdict: CLEAN ({improved} positive delta(s))")
    sys.exit(0)
else:
    print("verdict: NEUTRAL (no positive improvement)")
    sys.exit(2)
PYEOF
exit $?
