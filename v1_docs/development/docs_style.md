# Documentation Style

Status: staged V1 draft

V1 docs should make RDP easier to understand without sanding off the important
details.

## Reader First

Write for a technically capable reader who is new to RDP, then give deeper
links for specialists and integrators.

Prefer:

- short pages
- direct commands
- concrete file names
- small tables
- plain explanations of contract terms
- links to deeper pages

Avoid opening with architecture walls, release history, or long lists of every
module in the repo.

## Beginner Command Policy

Beginner pages should use the simple path:

```text
python install.py
python tutorials/v1/run_tutorials.py
```

Do not make beginner docs depend on special shell setup, separate tutorial
config files, editor-specific setup, or command-heavy tutorial control.

Contributor pages may use normal development commands such as focused pytest
runs, but those should not leak into the first-run path.

## Be Honest

If a page describes evidence, say what kind of evidence it is.

Examples:

- a tutorial pass proves that tutorial passed
- a partial recovery threshold is not exact recovery
- truth/oracle data must be visible
- report-only diagnostics must not affect ranking
- a display summary is not a solver-state persistence format

Do not turn uncertainty into marketing language.

## Paths

Use repo-relative paths in committed docs.

Good:

```text
tutorials/v1/run_tutorials.py
output/tutorial_logs/
artifacts/solver_report.json
```

Avoid absolute local paths in docs unless the page is explicitly recording a
local staging decision outside the public repo.

## Old Docs And Planning Notes

The old `docs/` tree and archived planning folder are source material.

Do not copy planning text directly into V1 docs. Read it, check it against the
current clean release tree, then rewrite it in the new voice.

When old docs and current code disagree, document the current code and record
the mismatch as an open cleanup item.

## Tutorial Docs

Tutorial docs should name:

- the runner
- the selected tutorial list owner
- the match threshold owner
- whether full printout review is needed
- where logs are written
- what success looks like

Do not document tutorial behavior that the current runner cannot execute.

## Report Docs

Report docs should preserve the boundary between:

- `RunSpec`
- `RunResult`
- `SolverReport`
- `ScorerReport`
- display summary
- artifacts

Those objects have different jobs. Keeping the jobs separate is part of the V1
design.
