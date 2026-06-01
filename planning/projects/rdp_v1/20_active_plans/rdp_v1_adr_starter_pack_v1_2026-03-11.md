# RDP v1 ADR starter pack
## lightweight starter list

_Date: 2026-03-11_

Use lightweight ADRs. Each should include:
- ID
- title
- date
- status
- decision owner
- context
- decision
- alternatives considered
- consequences
- linked rules/tests/files

## Suggested active ADR set

### ADR-0001 — Core is strict, boundary is forgiving
Decision:
Core types and runtime contracts stay strict. Friendly input belongs at the boundary and must be normalised before entering core.

### ADR-0002 — Core uses enums, not magic strings
Decision:
Core runtime logic should use enums or similarly strict typed values rather than raw string policy tokens.

### ADR-0003 — Campaigns become first-class top-level surface
Decision:
Campaign architecture moves toward a first-class governed surface rather than remaining effectively owned by benchmark tooling.

### ADR-0004 — Introduce first-class RunSpec / config runner
Decision:
RDP should converge on one serialisable public run contract and one canonical run entrypoint.

### ADR-0005 — One artifact/output/privacy owner
Decision:
Portable output, path redaction, identity redaction, trace placement, JSON/JSONL rules, and artefact refs should have one shared owner.

### ADR-0006 — No-WLI stays first-class under common outer run/job model
Decision:
No-WLI remains a first-class parity source and must fit the same serious outer run/job model rather than being treated as a disposable exception.

### ADR-0007 — Keep ScorerReport, add narrow SolverReport
Decision:
ScorerReport remains a stable core concept. A narrow stable SolverReport is added rather than allowing summary/report sprawl.

### ADR-0008 — Split data into assets/problem_sources/fixtures clearly
Decision:
Repo data concerns are split clearly so assets, problem sources, and fixtures are not muddled together.

### ADR-0009 — Support matrix is binding for planning and tests
Decision:
The support matrix is a real planning-and-test contract, not a vague aspiration note.

### ADR-0010 — Preserve flagship LP capability during v1 convergence
Decision:
V1 convergence work must preserve the effective capability of the intended flagship LP attack and must not simplify by quietly trimming it.
