"""
ranking — the *ranking / selection util* vocabulary (the growing LHS, §2.5-1).

This registers the minimal ranking-util set that `arbor-open-questions.md` Q-C3
("Ranking util DSL 의 적정 set") records as **answered and awaiting registration**
(status: "답 있음, 등록 대기" — module D): the seven utils

    (argmax, argmin, nth_by_desc, sort_by, count, filter_by, unique)

said to be "08ed6ac7 충분". They are *selection / util* expressions (the LHS
argument vocabulary), **not** transformations, so per §2.5-1 they live here under
`agent/` rather than the frozen `procedural_memory/DSL/` transformation directory
(adding a `def`/`@register` there trips F3).

Why this is distinct from the existing selectors (and not a duplicate). Every
selector in `selection.py` so far names the *extreme* (`largest` / `smallest` —
rank 1 by size) or the *odd one out* (`odd_color` / `odd_shape` — the unique-count
member). None can name a **ranked** member that is neither the extreme nor unique
— "the second largest", "the k-th by ...". That is exactly the ranking capability
Q-C3 answers (`nth_by_desc` / `sort_by`), and it is the substrate the §2.2 "가장
~한 / k-번째" ranking properties rest on. `argmax`/`argmin` here are the rank-1
special case, so the size selectors can delegate to one backing vocabulary instead
of each re-implementing the tie-aware extreme.

Decline-on-tie is the shared contract with `selection.py`: a ranked pick is only
returned when it names *exactly one* item (the n-th **distinct** key value is held
by a single item). A tie at the chosen rank makes the criterion ambiguous, so it
declines (returns ``None``) rather than guessing — keeping every ranked selection
value-agnostic and computable from G0 alone (P5).

Open-question note (surfaced per BACKLOG_LOOP §5): Q-C3 (the util *set*) is
answered and is what this module registers. The *separate*, still-open item is
`arbor-modules §2`("2차 relation 미지원 — edge-of-edge 비교") / Q "가장 긴 derived
속성 표현" — ranking over *comparison receipts* (2nd-order). These utils rank over
a *per-object property* (1st-order), not over comparison edges, so they do not
answer that open question; that 2nd-order representation is deliberately left for a
later rung. Deterministic and side-effect-free.
"""


def sort_by(items, key, *, descending=False) -> list:
    """The items sorted by ``key`` (ascending by default, descending when asked).

    A stable sort, so callers that need a deterministic order among equal keys get
    input order preserved. Pure — returns a new list, never mutates ``items``.
    """
    return sorted(items, key=key, reverse=descending)


def count(items, pred=None) -> int:
    """How many items satisfy ``pred`` (all of them when ``pred`` is ``None``)."""
    if pred is None:
        return len(items)
    return sum(1 for x in items if pred(x))


def filter_by(items, pred) -> list:
    """The items satisfying ``pred`` (a *scope predicate*, §2.5-2b), order kept."""
    return [x for x in items if pred(x)]


def unique(items):
    """The sole item when there is exactly one, else ``None`` — the degenerate
    selection (commits to "the one" without a literal index)."""
    if isinstance(items, list) and len(items) == 1:
        return items[0]
    return None


def _nth_ranked(items, key, n: int, descending: bool):
    """The unique item whose ``key`` equals the n-th (1-based) **distinct** value
    in the chosen order, or ``None`` when there are fewer than ``n`` distinct
    values or that value is shared by more than one item.

    Ranking over *distinct* values (not raw positions) is what makes the pick
    unambiguous: "second largest" means the second-largest *value*, declining when
    that value is tied, exactly like the extreme selectors decline on a tie.
    """
    if not items or n is None or n < 1:
        return None
    values = sorted({key(x) for x in items}, reverse=descending)
    if len(values) < n:
        return None
    target = values[n - 1]
    matches = [x for x in items if key(x) == target]
    return matches[0] if len(matches) == 1 else None


def nth_by_desc(items, key, n: int):
    """The unique item at the n-th rank counting from the *largest* key (1-based).
    ``nth_by_desc(_, key, 1)`` is `argmax`. Declines on a tie at that rank."""
    return _nth_ranked(items, key, n, descending=True)


def nth_by_asc(items, key, n: int):
    """The ascending mirror of `nth_by_desc` — n-th rank from the *smallest* key.
    ``nth_by_asc(_, key, 1)`` is `argmin`. (The answer set names ``nth_by_desc``;
    this is its ascending companion so "second smallest" needs no key negation.)"""
    return _nth_ranked(items, key, n, descending=False)


def argmax(items, key):
    """The unique key-maximal item, or ``None`` on a tie / empty — rank 1 desc."""
    return _nth_ranked(items, key, 1, descending=True)


def argmin(items, key):
    """The unique key-minimal item, or ``None`` on a tie / empty — rank 1 asc."""
    return _nth_ranked(items, key, 1, descending=False)
