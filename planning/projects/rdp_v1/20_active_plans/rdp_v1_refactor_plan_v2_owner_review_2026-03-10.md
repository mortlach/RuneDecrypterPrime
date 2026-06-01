# RDP v1 refactor and convergence plan — owner review draft 2
_Date: 2026-03-10_

## 1. Purpose

This plan turns the completed review and the now clearer owner governance into a controlled convergence programme.

The goal is not to redesign RDP from scratch.

The goal is to:
- freeze the owner-level governing documents
- formalise the campaign layer from the real code and real design intent
- lock the support and reporting contracts that v1 depends on
- simplify fragmented wiring without reducing attack capability
- and then move into phased implementation planning

This is therefore the **last governance-level pass before implementation planning**, not a fresh architecture exploration round.

---

## 2. Overall judgement

RDP now looks like a finishing-phase project.

The repo does not mainly look blocked by missing capabilities. It looks blocked by incomplete convergence of ownership, contracts, report surfaces, output policy, and campaign formalisation.

That is good news.

It means the path to v1 is mostly:
- hardening
- simplification
- anti-drift cleanup
- proving support honestly
- and giving first-class architecture first-class ownership

The campaign layer is now clearly part of that main convergence work, not a side note.

---

## 3. What is already settled enough

The following should be treated as settled enough to build from:
- owner design intent is the source of truth
- API and boundary own forgiving input shape and normalisation
- core owns the fixed typed solving interface
- RunSpec is the one true public run entrypoint
- campaigns sit above core runs and must not become a rival solving architecture
- scoring is core
- ScorerReport is a stable core concept
- SolverReport is a stable core concept
- formal rescoring is part of v1
- output/privacy rules are shared and portable
- LP support is first-class
- tutorials use the real supported system
- tools should become auxiliary again
- strict-in-core and forgiving-at-boundary is non-negotiable

Do not re-argue these points during implementation planning except where a specific detail truly forces review.

---

## 4. What still needs to be frozen before implementation planning

Only a small number of things still need final wording before implementation planning begins.

### 4.1 Governance charter v3

Tighten and freeze the owner governance charter.

This should be a controlled tightening pass, not a conceptual rewrite.

### 4.2 Campaign spec v1

Write and freeze the formal campaign spec.

This is now the main missing contract document. It should be extracted from the present code shape and the owner campaign philosophy rather than invented afresh.

### 4.3 Support-matrix wording

Freeze the wording of the first-release support matrix and the intended test meaning of its cells.

### 4.4 Refactor plan v2

Rewrite the refactor plan in light of the frozen charter and campaign spec so it becomes a practical convergence programme rather than a partly speculative review document.

---

## 5. Main convergence workstreams

The refactor should now be organised into the following workstreams.

### Workstream A — core run contract and front door

Goal:
- make RunSpec the real public run entrypoint
- define the strict serialisable run contract clearly
- keep the boundary forgiving but keep core strict

Includes:
- run/config normalisation boundary
- typed run contract
- canonical run entrypoint
- shared relationship between tutorials, direct runs, API use, and campaign-generated runs

Done when:
- one true public run path exists
- tutorials and campaigns can both use it honestly
- unsupported combinations fail clearly

### Workstream B — scoring, reports, and formal rescoring

Goal:
- keep scoring as a core capability
- stabilise ScorerReport and SolverReport as real shared contracts
- make formal rescoring reconstruction reliable and explicit

Includes:
- generic scorer interface
- search score versus report score roles
- report embedding and linking rules
- retained state for reliable later rescoring

Done when:
- ScorerReport and SolverReport have explicit minimum contracts
- campaign-level reporting can build on them without inventing rival report objects
- reconstruction is testable

### Workstream C — campaign formalisation and first-class ownership

Goal:
- turn the existing benchmark-local campaign machinery into a governed first-class campaign surface
- preserve full LP-attack capability while simplifying the public shape

Includes:
- CampaignSpec
- StageSpec
- PolicySpec
- variable tuning dimensions
- stage defaults
- stage progression
- bounded control loops
- deterministic resume and reconstruction
- campaign summaries and stage summaries

Done when:
- the campaign model is formally documented
- the model maps cleanly to the real code that already exists
- campaign architecture no longer depends on quiet benchmark-local folklore

### Workstream D — output, artefact, and privacy convergence

Goal:
- ensure one shared portable output and privacy contract across runs and campaigns

Includes:
- shared writer ownership
- path redaction
- identity redaction
- JSON and JSONL policy
- trace policy
- logical artefact refs only in portable outputs

Done when:
- run and campaign outputs obey one shared set of rules
- privacy and portability are test-backed

### Workstream E — repo-shape convergence

Goal:
- move important architecture toward its intended first-class ownership

Includes:
- first-class `campaigns/` surface
- strict solving area
- first-class LP domain surface
- first-class tutorials/examples surface
- tools reduced to auxiliary wrappers and helpers

Done when:
- important architecture is no longer quietly owned by `tools/`
- repo boundaries better match real architectural ownership

### Workstream F — support proof and contract tests

Goal:
- prove the v1 support story rather than merely asserting it

Includes:
- support-matrix contract tests
- RunSpec validation tests
- scoring/report contract tests
- campaign progression tests
- output/privacy tests
- reconstruction tests

Done when:
- the main first-class support promises are testable and tested
- both solve-proof and contract-proof exist for the supported v1 path

---

## 6. Campaign workstream in more detail

Because campaign is now clearly central, it deserves a more explicit statement in the plan.

### 6.1 Core principle

Do not reduce campaign ambition.

Do not treat campaign as a convenience wrapper around a tiny menu of neat workflows.

Campaign is the orchestrated optimiser over a chosen problem space and chosen variable run dimensions. For v1 it must support the strongest credible narrow LP attack the system can currently mount.

### 6.2 What stays

Keep the real useful substance already present in the code, including:
- community campaign config shape
- stage structure
- auxiliary objective bindings
- adaptive selection policy slices
- ordered stage engine behaviour
- stage events and pool-shaping behaviour

### 6.3 What changes

Change the **public shape and ownership**, not the seriousness of the attack.

The main cleanup tasks are:
- extract the outer campaign contract explicitly
- separate outer campaign definition from stage-execution detail
- replace switch-on-switch sprawl with named policy blocks
- preserve full LP attack patterns while making them more readable and governed
- move important campaign architecture toward first-class ownership

### 6.4 Knob-sprawl simplification

The current system has too many local overrides, copied patterns, and layered switches.

The refactor should preserve the actual behaviour but regroup it into a smaller number of named policy structures such as:
- variable-dimension definitions
- selection rules
- retry rules
- survivor or diversity rules
- batching rules
- budget rules
- resume rules
- telemetry options

### 6.5 Defaults

There should be a small set of standard stage and policy defaults sufficient for the full LP campaign, while remaining extensible.

### 6.6 Reconstruction minimum

At minimum, campaign outputs must preserve enough information to reconstruct the solve path later, even if more data needs to be recollected by rerun.

Campaign-level summaries should also surface the main big-ticket outcomes for fast review.

### 6.7 Campaign summaries

Treat campaign summary as a campaign-level summary object built from telemetry, ScorerReport, SolverReport, and related stage outputs.

Do not over-design the final analysis space now. Keep the contract minimal and extensible.

---

## 7. Pre-implementation gates

Implementation planning should not begin until these are in place:

### Gate 1 — document freeze

The following review drafts must exist and be owner-reviewed:
- governance charter v3
- campaign spec v1
- refactor plan v2

### Gate 2 — support wording freeze

The first-release support matrix wording must be stable enough to drive contract tests.

### Gate 3 — current-code mapping note

There must be an explicit mapping from existing campaign code into the formal campaign surface, so the implementation plan can preserve what matters and only clean what is accidental.

### Gate 4 — anti-drift guardrails

The main anti-drift rules must be reflected in the planned tests and implementation sequencing.

---

## 8. Implementation-planning sequence

Once the document freeze is complete, implementation planning should follow in this order.

### Phase 1 — touchpoint and ownership map

For each workstream, list:
- files or areas touched
- current owner or de facto owner
- target owner after convergence
- known risks
- required test gates

### Phase 2 — landing order

Choose a landing order that protects behaviour.

Recommended broad order:
1. tighten or add tests and guardrails
2. fix clear correctness or privacy defects
3. stabilise shared output and report contracts
4. introduce or tighten the RunSpec front door
5. formalise and lift the campaign surface
6. regroup repo ownership and package shape
7. remove duplicate helpers and shim debt

### Phase 3 — phase-by-phase implementation slices

For each implementation slice, define:
- goal
- exact files touched
- prerequisites
- tests to add or update
- done criteria
- parity expectations

### Phase 4 — proof pass

After the main slices land, do one explicit proof pass covering:
- first-class support matrix
- campaign progression and reconstruction
- report contracts
- output/privacy rules
- main LP-oriented campaign path

---

## 9. What not to do now

Do not:
- start with large structural moves before contracts are frozen
- quietly reduce campaign scope
- invent new major features during convergence unless they are directly required to complete the supported v1 path
- let important architecture remain permanently hidden inside `tools/`
- over-design the long-term campaign analysis layer before the minimum campaign summary contract is settled

---

## 10. Deliverables for the next step

The next immediate deliverables should therefore be:
- reviewed governance charter v3
- reviewed campaign spec v1
- reviewed refactor plan v2
- support-matrix draft aligned to the charter

After that, move straight into a concrete implementation plan.

That implementation plan should be practical, file-aware, test-aware, and phase-based rather than philosophical.

---

## 11. End state this plan is aiming at

When this convergence programme is complete, RDP v1 should present as:
- one honest public run front door
- one strict typed core
- one first-class campaign surface capable of serious LP attack work
- one shared scoring and reporting story
- one shared output/privacy story
- one clearer repo ownership model
- one support story that is test-proven rather than folklore-driven

That is the target state this plan should now drive.
