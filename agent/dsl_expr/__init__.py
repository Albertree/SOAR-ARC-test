"""
agent.dsl_expr — the *argument / composition* expression vocabulary.

BACKLOG_LOOP §2.5-1 splits the world in two: the *transformation* category is
frozen at two primitives (`make_grid`/`coloring`, in `procedural_memory/DSL/`),
while the vocabulary that builds their *arguments* and *compositions* is meant
to grow — and must live under `agent/`, not in the frozen DSL directory (putting
it there would trip F3). This package is that home.

Today it holds `render`: expressing a concrete target grid as a `make_grid` +
`coloring` composition (R0's COMM-copy action reduces to exactly this). As later
rungs add selection expressions (`unique`, `argmax`, `position-of`, …) they join
here too.
"""
