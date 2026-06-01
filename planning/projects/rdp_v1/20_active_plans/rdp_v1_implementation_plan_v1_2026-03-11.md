# RDP v1 convergence implementation plan
## owner-aligned draft for controlled refactor execution

_Date: 2026-03-11_

## 1. Purpose

This document turns the now mostly-settled v1 governance into a practical implementation programme.

It is not a fresh architecture exploration round.

It exists to make the refactor:
- controlled
- file-aware
- test-aware
- proof-based
- and resistant to shortcut behaviour by humans or agents

RDP is now in a capability-preserving convergence refactor. The job is to converge contracts, reports, outputs, campaign ownership, and repo shape onto the owner-reviewed target state without weakening the intended flagship LP attack capability and without silently dropping serious supported behaviour.

A shorter implementation plan does not mean the work got smaller in substance. It is shorter because the governing truth is now split across:
- the governance charter
- the campaign spec
- the support matrix
- this implementation plan
- the maintainer handbook

## 2. Source-of-truth order

When there is tension between documents or between docs and code, use this order:

1. governance charter
2. campaign spec
3. support matrix and capability notes
4. implementation plan
5. maintainer handbook
6. existing code and benchmark behaviour as parity evidence where docs are abstract
7. old notes and temporary scraps

Existing code is evidence, not the final governor.

Existing LP benchmark behaviour is the temporary parity source where the new docs are still abstract, unless that behaviour conflicts with the charter or support matrix.

No one is allowed to narrow a support promise by arguing that the current code is messy.

## 3. What is already settled

The following should now be treated as settled enough to build from and not re-argued during implementation unless a very specific detail forces review:

- API/boundary owns forgiving input shape and normalisation
- core owns the fixed typed solving interface
- RunSpec is the one true public run entrypoint
- campaigns sit above core runs and must not become a rival solving architecture
- ScorerReport remains a stable core concept
- a narrow stable SolverReport must be added
- formal rescoring is part of v1
- output/privacy rules are shared and portable
- LP support is first-class
- tutorials must use the real supported system
- tools should become auxiliary again
- strict in core and forgiving at boundary is non-negotiable
- the support matrix is binding for planning and tests

## 4. What this implementation plan is and is not

This plan is for:
- landing order
- workstream ownership
- file touchpoints
- tests and proof gates
- anti-drift behaviour rules
- controlled transition from current repo state to the v1 target state

This plan is not for:
- shrinking the support promise
- replacing serious campaign behaviour with toy wrappers
- allowing benchmark-local policy to leak into core
- inventing a second run language
- treating no-WLI or LP campaign complexity as optional awkward baggage
- making large structural tree moves before parity and guardrails are protected

## 5. Repo reality this plan is based on

The source tree confirms that the repo already contains substantial real machinery, but that this machinery is still split across parallel ownership shapes.

In plain English:

- the run/config front door is present in pieces rather than as one true RunSpec
- ScorerReport exists, but report convergence is not complete
- SolverReport appears to be a target-state concept, not a landed current type
- campaign machinery exists in at least two real surfaces:
  - an outer community campaign/config/sharding surface
  - an inner staged engine/policy surface in periodic-sub/trans tooling
- output/privacy behaviour is still spread across multiple owners
- LP domain and asset groundwork already exist and are important parity sources
- the repo test stack is already large enough that the refactor must be test-first and slice-based

So the refactor is mainly a convergence and ownership job, not a capability-invention job.

## 6. Mandatory pre-implementation gates

Implementation execution should not begin until these are treated as met:

### Gate 1 — document freeze
The owner-reviewed governance charter, campaign spec, and refactor plan must be accepted as the governing set.

### Gate 2 — support wording freeze
The first-release support matrix wording must be stable enough to drive contract tests.

### Gate 3 — current-code mapping note
There must be an explicit mapping from the present code into the formal target surfaces, so the implementation plan preserves what matters and only cleans what is accidental.

### Gate 4 — anti-drift guardrails
The anti-drift rules must already be reflected in the implementation sequencing and planned tests.

## 7. Current-code mapping that must exist before major edits

The implementation work should recognise these present-day source areas.

### 7.1 Current run/front-door area
Current main touchpoints:
- `src/rune_decrypter_prime/api/run.py`
- `src/rune_decrypter_prime/api/specs.py`
- `src/rune_decrypter_prime/api/normalize.py`
- `src/rune_decrypter_prime/core/config/run.py`
- related tests under:
  - `tests/api/`
  - `tests/api_contract/`
  - `tests/ui_normalize/`

Interpretation:
this is the present front-door surface that will need to converge toward one real RunSpec path.

### 7.2 Current scoring/report area
Current main touchpoints:
- `src/rune_decrypter_prime/scoring/scorer_report.py`
- `src/rune_decrypter_prime/scoring/scorer_report_builder.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/word_ngram_report.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_finalize.py`
- related tests under:
  - `tests/scoring/`
  - `tests/tools/`
  - `tests/telemetry/`

Interpretation:
ScorerReport is real, but report usage and projection still need convergence. SolverReport still needs to become a real stable type.

### 7.3 Current outer campaign area
Current main touchpoints:
- `tools/benchmarks/community/examples/campaign_config_v1_1.json`
- `tools/benchmarks/community/generate_manifest.py`
- `tools/benchmarks/community/run_shard.py`
- `tools/benchmarks/community/_run_single_job.py`
- `tools/benchmarks/community/_campaign_common.py`
- related tests under `tests/community/`

Interpretation:
this is already part of the real outer CampaignSpec story and should be generalised, not discarded.

### 7.4 Current inner campaign/stage engine area
Current main touchpoints:
- `tools/benchmarks/periodic_sub_trans/common/stage_spec.py`
- `tools/benchmarks/periodic_sub_trans/common/policy_spec.py`
- `tools/benchmarks/periodic_sub_trans/common/stage_engine.py`
- runner-specific areas under:
  - `tools/benchmarks/periodic_sub_trans/no_wli/`
  - `tools/benchmarks/periodic_sub_trans/sub_then_col/`
  - `tools/benchmarks/periodic_sub_trans/col_then_sub/`

Interpretation:
this is already a real strong inner campaign core. It should be widened and wrapped, not flattened away.

### 7.5 Current output/privacy area
Current main touchpoints:
- `src/rune_decrypter_prime/core/config/logging_config.py`
- `src/rune_decrypter_prime/io/run_logger.py`
- `tools/benchmarks/periodic_sub_trans/common/io_reports.py`
- `tools/benchmarks/periodic_sub_trans/common/trace_writer.py`
- `tools/benchmarks/periodic_sub_trans/common/paths.py`
- output-related helpers inside campaign tooling
- related tests including:
  - `tests/test_logging_paths.py`
  - privacy/path tests under `tests/tools/`

Interpretation:
portable output and privacy behaviour are still spread across multiple owners and must be converged.

### 7.6 Current LP/assets area
Current main touchpoints:
- `assets_manifest_v1.json`
- `src/rune_decrypter_prime/data/asset_paths.py`
- `src/rune_decrypter_prime/data/liber_primus/lp_master.py`
- `src/rune_decrypter_prime/data/liber_primus/lp_adapter.py`
- related tests under:
  - `tests/data/`
  - `tests/guardrails/`

Interpretation:
LP domain and asset handling are already real and should be treated as parity sources, not optional polish.

## 8. Main workstreams

### Workstream 0 — planning and control pack

Goal:
Make the refactor operationally safe by turning the handbook into a real working control system.

Required outputs:
- `planning/projects/rdp_v1/20_active_plans/CURRENT_PHASE_v1_2026-03-11.md`
- `planning/projects/rdp_v1/20_active_plans/ACTIVE_TODO_v0_2.md`
- `planning/projects/rdp_v1/20_active_plans/CURRENT_RISKS_v1_2026-03-11.md`
- `planning/projects/rdp_v1/30_architecture_specs/rdp_v1_current_code_crosscheck_note.md`
- `planning/projects/project_workflow/10_schema_and_rules/AGENT_UPDATE_AND_LOGGING_RULES_V1.md`
- `planning/projects/project_workflow/20_templates/RESULT_NOTE_TEMPLATE_V1.md`
- `planning/projects/project_workflow/20_templates/STATUS_LEDGER_TEMPLATE_V1.md`
- `planning/projects/rdp_v1/20_active_plans/rdp_v1_adr_starter_pack_v1_2026-03-11.md`

Why this is first:
The handbook already defines the read-first order, slice done criteria, anti-drift rules, and suggested planning layout. Those rules now need to exist as actual maintained files rather than only as handbook prose.

Effort: Medium.
Risk: Low technical risk, very high leverage.

### Workstream 1 — support matrix lock-down and test meaning

Goal:
Turn the support matrix into a binding planning-and-test contract rather than a promise sheet.

Required outputs:
- final wording of matrix cells
- one short note explaining cell meanings
- mapping from matrix cells to test families
- explicit unsupported-combination failure rules

Key rule:
The matrix describes the v1 target support promise. It should not be read as a claim that every promised combination is already uniformly converged in today’s repo.

Effort: Medium.
Risk: Medium.

### Workstream 2 — one public run contract and front door

Goal:
Make RunSpec the real serialisable public run contract and one true public entrypoint.

Includes:
- run/config normalisation boundary
- typed run contract
- canonical entrypoint
- honest shared relationship between direct runs, tutorials, API use, LP helpers, and campaign-generated runs

Important clarification:
This workstream is a convergence of the current run/config surfaces into one public contract. It is not a blank-slate invention.

Effort: Large.
Risk: High.

### Workstream 3 — scoring, reports, and formal rescoring

Goal:
Stabilise the v1 scoring and report contract.

Includes:
- keep ScorerReport
- add narrow stable SolverReport
- define formal rescoring retained-state contract
- preserve reconstruction guarantees
- remove report drift between core and campaign projections

Important clarification:
No-WLI remains a first-class parity source under the common outer run/job model, not a disposable special case.

Effort: Large.
Risk: High.

### Workstream 4 — one output/privacy/artefact owner

Goal:
Create one shared owner for portable output behaviour.

Includes:
- JSON and JSONL writing
- canonical JSON rules
- path redaction
- identity redaction
- trace placement
- telemetry placement
- logical artefact reference policy

Effort: Medium.
Risk: High because this is cross-cutting.

### Workstream 5 — first-class campaign surface

Goal:
Lift campaign architecture into governed first-class ownership while preserving the real LP attack workflows.

Includes:
- CampaignSpec
- widened StageSpec
- broader PolicySpec
- campaign summaries
- stage summaries
- survivor carry-forward
- retries
- bounded control loops
- optional rescoring
- honest output and reconstruction

Important clarification:
The campaign framework is not:
- a second solving architecture
- a campaign-local scoring contract
- a campaign-local output-writing system
- a place for magical opaque adaptive logic

Effort: Very large.
Risk: Very high.

### Workstream 6 — LP domain and asset governance

Goal:
Finalise honest first-class LP and asset governance.

Includes:
- logical asset IDs and versions
- source/runtime asset split
- clearer manifests
- stable LP problem-source surface
- portable asset references in runs and campaigns

Effort: Medium.
Risk: Medium.

### Workstream 7 — repo ownership convergence and de-shimming

Goal:
Move stable product surfaces into their intended long-term ownership areas and reduce shim debt.

Includes:
- first-class `campaigns/` ownership
- clearer strict solving area
- LP domain module in its intended governed place
- tools returning to genuinely auxiliary status
- removal of duplicate helpers once replacements are stable

Effort: Medium to large.
Risk: High if attempted too early.

### Workstream 8 — proof pass and release proof

Goal:
Prove both solve capability and contract honesty.

Includes:
- support-matrix proof
- campaign progression and reconstruction proof
- ScorerReport and SolverReport proof
- formal rescoring proof
- output/privacy proof
- flagship LP workflow proof

Effort: Medium.
Risk: Essential, not optional.

## 9. Landing order

### Phase A — control pack and mapping
Do this first.

Outputs:
- working planning pack
- ADR starter set
- current-code mapping note
- touchpoint tables by workstream
- risk register

### Phase B — support wording freeze and guardrail scaffolding
Do this before architectural edits.

Outputs:
- frozen support matrix wording
- matrix cell interpretation note
- initial contract-test mapping
- missing anti-drift tests identified and queued

### Phase C — output/privacy and report contract stabilisation
Do this before broad campaign lifting.

Outputs:
- one output/privacy owner design
- ScorerReport usage tightening
- minimum SolverReport contract
- retained-state rule for formal rescoring
- report/reconstruction test additions

### Phase D — RunSpec/front-door convergence
Do this before campaign extraction becomes broad.

Outputs:
- real RunSpec contract
- one canonical run entrypoint
- adaptation of direct runs, tutorials, LP helpers, and campaign-generated runs onto that path

### Phase E — first governed campaign façade
Do this before major repo shape changes.

Outputs:
- first governed CampaignSpec
- widened StageSpec
- wrapped/expanded PolicySpec
- campaign façade that preserves current serious LP behaviour
- no broad file moves yet

### Phase F — campaign ownership lift and de-localisation
Only after the façade and guardrails are working.

Outputs:
- campaign architecture moved toward first-class ownership
- runner-local duplication reduced
- long-term product surfaces no longer hiding in `tools/`

### Phase G — LP/assets alignment and proof pass
Final convergence and release-proof phase.

Outputs:
- LP/assets governance complete enough for release
- proof pass completed
- support matrix, docs, and tests aligned
- release gate checklist

## 10. Agent and maintainer workflow

This should become mandatory during the refactor phase.

### 10.1 Read-first order
Before any real task, read in this order:
1. `CURRENT_PHASE.md`
2. maintainer handbook
3. relevant ADRs
4. `ACTIVE_TODO.md` or current phase brief
5. support matrix and capability notes
6. relevant tests
7. relevant code

### 10.2 Questions that must be answered before proposing a change
- What contract is affected?
- Is this core, boundary, campaign, tutorial, or tool?
- What tests currently protect intended behaviour?
- Is the current code the parity source here?
- Does this create a second surface or duplicate policy owner?
- Does this weaken LP capability, even slightly?
- Is this a true simplification, or just short-term wiring?
- Does an ADR already exist?

### 10.3 Things agents must not do
- quietly drop support promises because the code is messy
- create a second config surface beside the real run contract
- add benchmark-local policy to core for convenience
- add a local output writer or local path policy
- widen or change defaults silently
- hide behaviour inside tutorials or tools
- replace real parity with guessed parity
- collapse serious campaign behaviour into toy wrappers
- keep shim layers indefinitely

### 10.4 Temporary bridge rule
A temporary bridge is allowed only if all of these are written down:
- why it exists
- what parity it protects
- which tests cover it
- what removes it later
- what makes it dangerous if it lives too long

## 11. Required task template

Every non-trivial implementation task should include:
- title
- purpose
- category
- owner
- files likely touched
- rules affected
- parity source
- tests to add or update
- success criteria
- non-goals
- rollback or safety notes
- bridge note if temporary bridging is involved

Recommended category values:
- correctness bug
- contract hardening
- convergence cleanup
- architectural change
- new feature
- experiment
- documentation alignment
- release hygiene

## 12. Slice definition of done

No implementation slice is done until these are checked where relevant:
- intended behaviour preserved or explicitly changed with approval
- support-matrix cells protected by tests
- no new absolute-path leakage
- shared writer/output rules used
- no second config surface introduced
- no campaign-local scorer contract introduced
- reconstruction or rescoring path preserved where relevant
- reports still emitted on the agreed contract
- tutorials still run if they depend on the changed surface
- temporary shims have an exit note
- parity note updated if the source of truth moved

## 13. ADR starter set

- ADR-0001: Core is strict, boundary is forgiving
- ADR-0002: Core uses enums, not magic strings
- ADR-0003: Campaigns become first-class top-level surface
- ADR-0004: Introduce first-class RunSpec / config runner
- ADR-0005: One artifact/output/privacy owner
- ADR-0006: No-WLI stays first-class under common outer run/job model
- ADR-0007: Keep ScorerReport, add narrow SolverReport
- ADR-0008: Split data into assets/problem_sources/fixtures clearly
- ADR-0009: Support matrix is binding for planning and tests
- ADR-0010: Preserve flagship LP capability during v1 convergence

## 14. Immediate next actions

1. create the planning/control pack files named in Workstream 0
2. write the current-code mapping note from the source areas listed above
3. freeze support-matrix wording and add a short cell-meaning note
4. define the initial test mapping from support cells to existing tests
5. write task cards for:
   - output/privacy convergence
   - report/rescoring convergence
   - RunSpec/front-door convergence
   - first governed campaign façade
6. start Phase C only after those cards and gates exist

## 15. Final implementation judgement

RDP does not currently look blocked by missing raw capability.

It looks blocked by incomplete convergence of:
- ownership
- contract shape
- reporting
- reconstruction
- output/privacy policy
- campaign formalisation
- and repo-level execution discipline

That means the path to v1 is mainly:
- hardening
- convergence
- anti-drift cleanup
- and proof

But it also means the refactor must be run carefully, because the code already contains serious LP-first campaign behaviour and substantial prototype capability that would be easy to damage with neat-looking simplifications.
