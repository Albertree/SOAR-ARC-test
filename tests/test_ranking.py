"""
Unit tests for agent/dsl_expr/ranking.py — the answered Q-C3 ranking-util set
(argmax, argmin, nth_by_desc, sort_by, count, filter_by, unique) registered as the
growing LHS selection vocabulary (BACKLOG_LOOP §2.5-1). The shared contract with
selection.py is decline-on-tie: a ranked pick is returned only when it names
exactly one item.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.dsl_expr import ranking


def _sz(x):
    return x["s"]


ABC = [{"s": 4, "n": "a"}, {"s": 3, "n": "b"}, {"s": 1, "n": "c"}]


def test_argmax_argmin_unique_extreme():
    assert ranking.argmax(ABC, _sz)["n"] == "a"
    assert ranking.argmin(ABC, _sz)["n"] == "c"


def test_argmax_declines_on_tie():
    tied = [{"s": 4, "n": "a"}, {"s": 4, "n": "b"}, {"s": 1, "n": "c"}]
    assert ranking.argmax(tied, _sz) is None
    # ...but argmin is still unambiguous here
    assert ranking.argmin(tied, _sz)["n"] == "c"


def test_argmax_declines_on_empty():
    assert ranking.argmax([], _sz) is None
    assert ranking.argmin([], _sz) is None


def test_nth_by_desc_ranks_distinct_values():
    assert ranking.nth_by_desc(ABC, _sz, 1)["n"] == "a"   # == argmax
    assert ranking.nth_by_desc(ABC, _sz, 2)["n"] == "b"   # second largest
    assert ranking.nth_by_desc(ABC, _sz, 3)["n"] == "c"


def test_nth_by_asc_is_the_ascending_mirror():
    assert ranking.nth_by_asc(ABC, _sz, 1)["n"] == "c"    # == argmin
    assert ranking.nth_by_asc(ABC, _sz, 2)["n"] == "b"    # second smallest


def test_nth_declines_when_rank_absent_or_tied():
    # only two distinct values -> no 3rd rank
    two = [{"s": 5, "n": "a"}, {"s": 5, "n": "b"}, {"s": 1, "n": "c"}]
    assert ranking.nth_by_desc(two, _sz, 3) is None
    # rank-2 value (1) here is unique, so it resolves...
    assert ranking.nth_by_desc(two, _sz, 2)["n"] == "c"
    # ...but a rank whose value is shared declines (rank-1 value 5 is tied)
    assert ranking.nth_by_desc(two, _sz, 1) is None
    # n below 1 is not a valid rank
    assert ranking.nth_by_desc(ABC, _sz, 0) is None


def test_sort_by_is_pure_and_ordered():
    src = [{"s": 1}, {"s": 3}, {"s": 2}]
    asc = ranking.sort_by(src, _sz)
    desc = ranking.sort_by(src, _sz, descending=True)
    assert [o["s"] for o in asc] == [1, 2, 3]
    assert [o["s"] for o in desc] == [3, 2, 1]
    assert [o["s"] for o in src] == [1, 3, 2]   # input unchanged


def test_count_and_filter_and_unique():
    assert ranking.count(ABC) == 3
    assert ranking.count(ABC, lambda o: o["s"] > 1) == 2
    assert [o["n"] for o in ranking.filter_by(ABC, lambda o: o["s"] > 1)] == ["a", "b"]
    assert ranking.unique([ABC[0]])["n"] == "a"
    assert ranking.unique(ABC) is None       # several -> no sole item
    assert ranking.unique([]) is None
