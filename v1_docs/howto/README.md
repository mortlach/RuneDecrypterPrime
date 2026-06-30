# How-To Guides

Status: staged V1 draft

These pages are for contributors making focused changes to the RDP core.

## Guides

| Guide | Use when |
| --- | --- |
| [Add A Cipher](add_cipher.md) | You need a new cipher implementation or public cipher wrapper. |
| [Add A Solver](add_solver.md) | You need a new search strategy. |
| [Add A Scorer Lane](add_scorer_lane.md) | You need a new scoring signal, capability lane, or report-only scorer diagnostic. |
| [Add A Tutorial](../development/adding_a_tutorial.md) | You need a new runnable V1 tutorial. |

## Working Rule

Keep changes small and contract-backed. A new extension should include:

- source implementation
- config or registry wiring
- focused tests
- report/telemetry evidence when relevant
- docs updates

Do not add generated outputs, local logs, caches, or benchmark results to the
repo.
