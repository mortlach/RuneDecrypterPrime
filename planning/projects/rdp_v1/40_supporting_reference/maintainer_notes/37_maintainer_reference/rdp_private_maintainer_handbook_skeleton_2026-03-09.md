# RDP Private Maintainer Handbook Skeleton

## Status
Draft skeleton for internal use. This is intended for the private gitignored planning area, not the public-facing repo.

---

# 1. Purpose

This handbook exists to stop RDP drifting as it grows.

RDP is no longer mainly in an alpha feature-invention phase. It is now in a convergence, hardening, tuning, and proof phase. That changes how work should be done.

The purpose of this handbook is to make the following things explicit and durable:
- the engineering rules of engagement
- the intended architecture boundaries
- the workflow for maintainers and agents
- the anti-drift rules that should guide refactors and new features
- where to record decisions and why they were made
- how to keep private planning, public docs, and real code behaviour aligned

This handbook is private because it may include:
- internal engineering judgement
- work-in-progress decisions
- design trade-offs not ready for public docs
- maintainer workflow notes
- agent instructions and review habits

But the important public-safe parts of the architecture should still be reflected in:
- public docs
- tests
- schema contracts
- code structure

Private notes must not become the only place where the truth lives.

---

# 2. Core aim

Build and maintain a world-class rune decrypter that is:
- powerful enough for advanced research and hard problems
- usable enough for beginners and intermediate solvers
- reproducible enough for scientific-style experimentation
- structured enough to support tutorials, campaigns, APIs, and future GUIs
- stable enough that contracts do not drift every few months

That means RDP should gradually become:
- smaller in trusted core surface
- clearer in ownership
- stricter in internal contracts
- better documented in behaviour
- easier to extend without accidental breakage

---

# 3. Rules of engagement

These are the default engineering rules for work on RDP.

## ROE-001: Core is strict, boundary is forgiving
- Core types, configs, and runtime contracts should be strict.
- Boundary layers may accept friendlier inputs and normalise them.
- Do not let boundary forgiveness leak into core internals.

## ROE-002: Enums in core, not magic strings
- Core runtime logic should use enums or similarly strict typed values.
- Strings may appear at API/config boundaries, then must be normalised.
- New raw string policy tokens in core need strong justification.

## ROE-003: Tests lock behaviour before structural refactor
- If a behaviour is intended and non-trivial, write or tighten tests first.
- Do not rely on memory or chat history to preserve behaviour.

## ROE-004: No silent drift in persisted outputs
- Persisted files must follow one clear artifact/output/privacy policy.
- No absolute paths in persisted outputs unless explicitly permitted.
- No hidden output destinations.

## ROE-005: One owner per policy
Examples:
- one owner for output/privacy policy
- one owner for telemetry emission contract
- one owner for artifact hashing/canonical JSON rules
- one owner for top-level run spec

If multiple modules own the same policy, drift is likely.

## ROE-006: No new module-global orchestration in core flows
- Prefer explicit state objects/config objects over `globals()` choreography.
- Temporary bridge code is acceptable only with an exit plan.

## ROE-007: No benchmark-local policy leaking into core without review
- Core should support reusable solving capability.
- Campaign- or benchmark-specific policy should live above core unless truly general.

## ROE-008: Compatibility shims need an explicit removal plan
- If a shim is introduced or retained, document:
  - why it exists
  - who still depends on it
  - when it can be removed

## ROE-009: Public docs, private notes, and real behaviour must be kept aligned
- Private notes may be richer.
- Public docs may be simpler.
- Tests and code must reflect the actual truth.

## ROE-010: Small, measured refactor slices
- Prefer controlled, test-backed phases.
- Avoid giant rewrites unless there is no safer path.

---

# 4. Architectural intent

This section is the short maintainers' map of what each layer is for.

## 4.1 Core library
Owns:
- ciphers
- key-op families and registries
- solver engine and solver interfaces
- strict runtime configs
- strict core types and enums
- telemetry model
- typed reports such as ScorerReport and likely SolverReport
- canonical top-level RunSpec once introduced

Should not own:
- community campaign bookkeeping
- ad hoc experiment wrappers
- install scripts
- private planning logic
- personal helper scripts

## 4.2 API / boundary layer
Owns:
- friendly entrypoints
- config parsing and validation
- boundary normalisation from JSON/YAML/UI input into strict core types
- tutorial-facing and GUI-facing solve front door

Should not own:
- hidden policy defaults that bypass core contracts
- large amounts of benchmark-specific wiring

## 4.3 Problem sources
Owns:
- LP page/locator-backed sources
- solved-page fixtures
- reusable machine-readable problem definitions
- source metadata and labels

This should be clearly separated from general assets and from test-only fixtures.

## 4.4 Assets / resources
Owns:
- packaged asset-location policy
- default paths for smaller installable resources
- manifests and lightweight metadata

Should not blur together:
- large external datasets
- test baselines
- LP source definitions

## 4.5 Campaigns
Owns:
- distributed experiment workflows
- job specs and aggregation
- shard/bundle/import/export flow
- result collation
- tuning and sweep infrastructure
- community experiment contracts

Campaigns are broader than benchmarks. The name should reflect that.

## 4.6 Tutorials
Owns:
- human-facing examples
- learning material
- worked solves
- small demonstration configs

Should not become the hidden source of truth for runtime behaviour.

## 4.7 Tools
Owns only:
- genuinely auxiliary scripts
- private helper utilities
- temporary conversion or maintenance scripts

If tests, schemas, docs, outputs, and workflows depend on something as a stable surface, it is probably not really a tool anymore.

---

# 5. Proposed long-term repo shape

This is a working target, not yet a frozen plan.

```text
repo-root/
  src/rune_decrypter_prime/
    core/
    api/
    telemetry/
    reports/
    problem_sources/
    assets/               # or resources/
    ...

  campaigns/
    community/
    periodic_sub_trans/
    ...

  tutorials/
    v1/
    solved_pages/
    examples/

  tools/
    helper_scripts_only/

  tests/
    unit/
    integration/
    guardrails/
    campaigns/
    tutorials/

  planning/               # gitignored private maintainer space
    working/
    decisions/
    review/
    release/
    agents/
```

Notes:
- `campaigns/` is preferred over `benchmarks/` if the system is broader than scorekeeping.
- `problem_sources/` should be distinct from tutorials and distinct from giant external data.
- `tools/` should shrink back to honestly auxiliary scripts.

---

# 6. Key active design directions

These are the main design directions currently supported by the review.

## 6.1 First-class core config runner
RDP should have one serialisable top-level run contract.

Likely shape:
- `RunSpec` in core/API boundary
- can be loaded from JSON or YAML
- can be used by:
  - tutorials
  - LP solved pages
  - API callers
  - future GUI/web front ends
  - campaign jobs

Campaign layer should extend or wrap this, not replace it with an unrelated solve-description model.

## 6.2 One outer run/job model, different internal policies
No-WLI should stay first-class, but ideally under the same outer run/job model.
Different problem classes may differ in:
- runner policy
- scorer roles
- search strategy
- fixture metadata

That is better than maintaining separate worlds forever.

## 6.3 Typed report objects
- keep `ScorerReport`
- likely add `SolverReport`
- reports should be compact typed summaries
- telemetry remains the detailed event stream
- reports do not replace telemetry

## 6.4 One artifact/output/privacy owner
Need one shared owner for:
- JSON writing
- JSONL writing
- canonical JSON for hashing
- path redaction
- identity redaction
- trace location policy
- telemetry dump placement

## 6.5 Stronger internal anti-drift guardrails
Important rules should not just be preferences. They need enforcement.

---

# 7. Private planning folder workflow

This section assumes the repo already has a gitignored planning area.

## 7.1 Why keep a private planning area
Useful for:
- working TODO lists
- review notes
- maintainer rules
- draft architecture plans
- agent instructions
- decision records not yet ready for public docs
- implementation phase checklists

## 7.2 Problems with the current typical setup
Common failure modes:
- TODO list becomes the only source of truth
- architectural rules live only in chat or memory
- agents tick off tasks without checking contracts
- decisions are not recorded, so later work reopens the same argument
- work items do not say what tests protect them
- public docs and private plans drift apart

## 7.3 Recommended private planning layout

```text
planning/
  working/
    ACTIVE_TODO.md
    CURRENT_PHASE.md
    CURRENT_RISKS.md
    INBOX.md

  review/
    v1_review/
    findings_register.csv
    collated_programme.md

  decisions/
    ADR-0001-*.md
    ADR-0002-*.md

  architecture/
    target_architecture.md
    boundaries.md
    anti_drift_policies.md

  agents/
    maintainer_handbook.md
    change_workflow.md
    task_template.md
    review_template.md

  release/
    v1_release_gate.md
    packaging_checklist.md
    docs_alignment_checklist.md
```

## 7.4 Recommended meaning of each file

### ACTIVE_TODO.md
Current ordered work queue only.
Each item should link to:
- rationale
- owner
- affected rules
- required tests
- status

### CURRENT_PHASE.md
Explains what phase the repo is in.
Examples:
- convergence and hardening
- config runner design freeze
- output/privacy policy unification

### CURRENT_RISKS.md
Short list of active risks.
Examples:
- path privacy drift
- scoring role ambiguity
- module-global runner state

### INBOX.md
Low-commitment capture area.
Not yet approved work.

This prevents the TODO list becoming a junk drawer.

---

# 8. Decision register

Use lightweight ADRs.

Each decision record should include:
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

## Suggested first ADRs
- ADR-0001: Core is strict, boundary is forgiving
- ADR-0002: Core uses enums, not magic strings
- ADR-0003: Campaigns become first-class top-level surface
- ADR-0004: Introduce first-class RunSpec / config runner
- ADR-0005: One artifact/output/privacy owner
- ADR-0006: No-WLI stays first-class under common outer run/job model
- ADR-0007: Keep ScorerReport, add narrow SolverReport
- ADR-0008: Split current data package into assets/problem_sources/fixtures

---

# 9. Change workflow for humans and agents

## 9.1 Before starting work
Read in this order:
1. `CURRENT_PHASE.md`
2. this handbook
3. relevant ADRs
4. `ACTIVE_TODO.md`
5. relevant tests
6. relevant code

## 9.2 Before proposing a change
Answer these questions:
- what contract is affected?
- is this core, boundary, campaign, tutorial, or tool?
- which rules of engagement apply?
- is there already a decision record about this?
- what tests lock current intended behaviour?
- is this must-fix, should-fix, or later?

## 9.3 Change classes
Every task should be labelled as one of:
- correctness bug
- contract hardening
- convergence cleanup
- architectural change
- new feature
- experiment
- documentation alignment
- release hygiene

## 9.4 Required task fields
Every real task should include:
- title
- purpose
- category
- owner
- files likely touched
- rules affected
- tests to add or update
- success criteria
- non-goals
- rollback or safety notes

## 9.5 During implementation
- prefer small slices
- update task status as you go
- do not create hidden side contracts
- do not widen public contract casually
- note any architecture decision that changed

## 9.6 After implementation
- check relevant tests
- update ADR if needed
- update public-safe docs if behaviour changed
- update private planning note if next phase changed
- mark TODO item done only when the actual acceptance criteria are met

---

# 10. Anti-drift policies to make explicit

These are examples of the sort of internal policies that should be documented and enforced.

## Policy family A: Type and contract discipline
- core uses enums and strict types
- boundary may parse strings
- no raw string policy tokens added to core without review
- no `Enum | str` in core storage unless there is an explicit reason

## Policy family B: Output and privacy discipline
- no absolute paths in persisted outputs
- no raw identity leakage in persisted logs
- all output writers go through one owner
- telemetry mirrors must obey run-root policy

## Policy family C: Repo structure discipline
- first-class product surfaces do not live under `tools`
- old snapshots are moved out of active package space
- temporary shims must be marked and tracked

## Policy family D: Runtime discipline
- no new module-global runner orchestration
- stop reasons should come from one canonical contract
- solver/scorer summary reports should be typed

## Policy family E: Review discipline
- tests first for behaviour-preserving refactor
- ADR for non-trivial architecture changes
- TODO items must link to rules and tests

---

# 11. Enforcement map

Every important rule should have at least one enforcement mechanism.

| Rule | Enforcement type | Current status | Notes |
|---|---|---|---|
| Core strict, boundary forgiving | guardrail tests + review checklist | partial | needs stronger config cleanup |
| Enums in core | guardrail tests + type review | partial | some core config still accepts strings |
| No absolute persisted paths | tests + shared writer policy | partial | JSONL path privacy still weak |
| One artifact/output owner | code structure | missing | major convergence target |
| No module-global orchestration | architecture review + refactor plan | partial | campaign runners still use globals choreography |
| Tests before structural cleanup | workflow + PR checklist | partial | should become standard |
| Shim removal plans | ADR/task template | weak | many shims lack explicit exit plan |

---

# 12. Public vs private documentation split

## Keep private
- working TODO queue
- maintainer workflow details
- internal engineering rules with sensitive detail
- draft architecture moves
- unfinished decision records
- agent-specific guidance

## Safe to make public later
- high-level architecture boundaries
- stable top-level run model
- public API contract
- tutorial structure
- campaign/job schema contracts
- public-safe coding conventions

Private material should support public truth, not replace it.

---

# 13. Templates

## 13.1 Task template

```md
# Task: <title>

## Purpose

## Category
- correctness bug / convergence cleanup / architectural change / new feature / etc.

## Why now

## Rules affected
- ROE-...

## Likely files

## Tests to add or update

## Success criteria

## Non-goals

## Risks

## Status
- planned / in progress / review / done
```

## 13.2 ADR template

```md
# ADR-XXXX: <title>

## Status

## Context

## Decision

## Alternatives considered

## Consequences

## Linked rules/tests/files
```

## 13.3 Review template

```md
# Review note: <topic>

## Scope

## Evidence

## Findings

## Contract risks

## Determinism/privacy risks

## Recommended action

## Priority
- must-fix / should-fix / later
```

---

# 14. Suggested first follow-up documents

These are the next private docs worth writing after this skeleton.

1. `anti_drift_policies.md`
2. `target_architecture.md`
3. `ADR-0001-core-strict-boundary-forgiving.md`
4. `ADR-0002-enums-in-core.md`
5. `ADR-0003-campaigns-first-class.md`
6. `v1_hardening_implementation_brief.md`
7. `output_privacy_contract.md`
8. `config_runner_design_draft.md`

---

# 15. Immediate practical recommendations

1. Keep using the gitignored planning folder, but make it more structured.
2. Split current planning truth into:
   - active queue
   - decisions
   - architecture rules
   - reviews
   - release gates
3. Add a short private maintainer handbook like this and require agents to read it first.
4. Start a lightweight ADR log now.
5. Link every major TODO item to rules, tests, and affected contracts.
6. Do not let private workflow notes become the only place where the architecture truth lives.
7. Mirror the stable public-safe subset into the public repo as the architecture converges.

---

# 16. Final note

This handbook is not meant to add bureaucracy.
It is meant to protect coherence while RDP grows into a long-term serious project.

The more RDP becomes:
- usable by many kinds of solvers
- suitable for difficult research problems
- able to support campaigns and APIs and GUIs

...the more important it becomes that the project has explicit internal rules, clear boundaries, and a workflow that prevents contract drift.

