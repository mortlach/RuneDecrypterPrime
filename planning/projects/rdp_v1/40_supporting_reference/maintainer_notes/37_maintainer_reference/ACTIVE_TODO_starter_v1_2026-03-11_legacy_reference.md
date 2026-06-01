# ACTIVE_TODO.md
## starter set for RDP v1 convergence phase

_Date: 2026-03-11_
_Status: starter draft_

## How to use this file

Each active item should stay small, owned, and reviewable.

Each item should link to:
- rationale
- owner
- affected rules
- required tests
- status
- non-goals

Do not let this file become a junk drawer.

---

## Item 001 — create planning/control pack
- **Change class:** documentation alignment
- **Purpose:** make the handbook workflow real in the repo planning area
- **Owner:** TBD
- **Affected rules:** ROE-003, ROE-009, ROE-010; support-matrix proof workflow
- **Files likely touched:**
  - `planning/working/CURRENT_PHASE.md`
  - `planning/working/ACTIVE_TODO.md`
  - `planning/working/CURRENT_RISKS.md`
  - `planning/agents/change_workflow.md`
  - `planning/agents/task_template.md`
  - `planning/agents/implementation_slice_gates.md`
- **Required tests:** none directly; review against handbook required
- **Status:** open
- **Success criteria:** required planning/control files exist and mirror handbook workflow
- **Non-goals:** no architecture rewrites

## Item 002 — write current-code mapping note
- **Change class:** documentation alignment
- **Purpose:** satisfy pre-implementation Gate 3 and stop file guessing
- **Owner:** TBD
- **Affected rules:** parity before tidiness; no guessed parity
- **Files likely touched:**
  - `planning/architecture/current_code_mapping_note.md`
- **Required tests:** none directly; mapping must point to current test areas
- **Status:** open
- **Success criteria:** run/front-door, scoring/report, outer campaign, inner stage engine, output/privacy, and LP/assets are all mapped
- **Non-goals:** no code movement yet

## Item 003 — freeze support-matrix cell meanings
- **Change class:** contract hardening
- **Purpose:** make matrix wording reviewable and testable
- **Owner:** TBD
- **Affected rules:** support matrix binding; no silent narrowing of support
- **Files likely touched:**
  - support matrix workbook / CSV
  - `planning/architecture/support_matrix_cell_meanings.md`
- **Required tests:** test-map follow-on item
- **Status:** open
- **Success criteria:** “Yes”, “Where relevant”, “Limited”, and “Not supported” have explicit meanings
- **Non-goals:** no new support promises

## Item 004 — map support matrix to tests
- **Change class:** contract hardening
- **Purpose:** turn support promises into proof scaffolding
- **Owner:** TBD
- **Affected rules:** support matrix binding; tests and contracts first
- **Files likely touched:**
  - `planning/review/support_matrix_test_map.md`
  - `planning/working/ACTIVE_TODO.md`
- **Required tests:** identify existing and missing tests only
- **Status:** open
- **Success criteria:** each important support promise has positive proof and clear-failure proof or an explicit gap note
- **Non-goals:** not yet filling every missing test gap

## Item 005 — inventory current output/privacy owners
- **Change class:** convergence cleanup
- **Purpose:** expose fragmented writer/policy ownership before convergence work
- **Owner:** TBD
- **Affected rules:** one owner per policy; no new absolute-path leakage
- **Files likely touched:**
  - `planning/architecture/output_owner_inventory.md`
  - current writer/path helper files
- **Required tests:** identify relevant output/privacy tests
- **Status:** open
- **Success criteria:** every current writer/policy owner is listed with current role and target owner
- **Non-goals:** no writer replacement yet

## Item 006 — define output/privacy minimum contract
- **Change class:** contract hardening
- **Purpose:** freeze the shared portable output contract before code movement
- **Owner:** TBD
- **Affected rules:** ROE-004, ROE-005, ROE-012
- **Files likely touched:**
  - `planning/architecture/output_privacy_contract.md`
  - `planning/decisions/ADR-0005-one-output-owner.md`
- **Required tests:** existing path/privacy tests identified; missing tests queued
- **Status:** open
- **Success criteria:** JSON/JSONL, path redaction, identity redaction, artefact refs, and trace placement rules are explicit
- **Non-goals:** no broad logging redesign

## Item 007 — define ScorerReport minimum contract
- **Change class:** contract hardening
- **Purpose:** stop report drift between core and campaign projections
- **Owner:** TBD
- **Affected rules:** keep ScorerReport; no rival report objects
- **Files likely touched:**
  - `src/rune_decrypter_prime/scoring/scorer_report.py`
  - `src/rune_decrypter_prime/scoring/scorer_report_builder.py`
  - `planning/architecture/scorerreport_minimum_contract.md`
- **Required tests:** existing scoring/report tests reviewed; new contract tests likely needed
- **Status:** open
- **Success criteria:** minimum fields and projection rules are explicit
- **Non-goals:** no scorer redesign

## Item 008 — land SolverReport minimum contract
- **Change class:** architectural change
- **Purpose:** make SolverReport a real shared contract rather than doc-only intent
- **Owner:** TBD
- **Affected rules:** typed reports; reconstruction minimum
- **Files likely touched:**
  - new or updated report files under `src/rune_decrypter_prime/`
  - `planning/architecture/solverreport_minimum_contract.md`
- **Required tests:** report contract tests; campaign-summary linkage tests later
- **Status:** open
- **Success criteria:** minimum SolverReport contract exists in code and docs
- **Non-goals:** no heavy telemetry system redesign

## Item 009 — define formal rescoring retained-state minimum
- **Change class:** contract hardening
- **Purpose:** make reliable later rescoring/reconstruction explicit
- **Owner:** TBD
- **Affected rules:** formal rescoring is part of v1; reconstruction preserved
- **Files likely touched:**
  - `planning/architecture/formal_rescoring_retained_state.md`
  - later related report/campaign code
- **Required tests:** rescoring / reconstruction tests identified or added
- **Status:** open
- **Success criteria:** minimum retained state is written down and testable
- **Non-goals:** no long-term analysis over-design

## Item 010 — inventory current front-door surfaces
- **Change class:** documentation alignment
- **Purpose:** make current public-ish run entrypoints explicit before RunSpec work
- **Owner:** TBD
- **Affected rules:** one true public run path; no duplicate public surfaces
- **Files likely touched:**
  - `planning/architecture/front_door_inventory.md`
  - front-door API/config files
- **Required tests:** existing API/ui normalisation tests identified
- **Status:** open
- **Success criteria:** all current entrypoints and overlaps are listed
- **Non-goals:** no RunSpec implementation yet

## Item 011 — define minimum RunSpec
- **Change class:** architectural change
- **Purpose:** freeze the first-release public run contract
- **Owner:** TBD
- **Affected rules:** core strict, boundary forgiving; no rival solve-description language
- **Files likely touched:**
  - `planning/architecture/runspec_minimum_contract.md`
  - `planning/decisions/ADR-0004-runspec-front-door.md`
- **Required tests:** RunSpec validation tests to be identified or added
- **Status:** open
- **Success criteria:** serialisable minimum RunSpec contract is clear enough to implement
- **Non-goals:** no tree reorganisation yet

## Item 012 — define minimum CampaignSpec
- **Change class:** architectural change
- **Purpose:** freeze the outer campaign boundary from the real current code shape
- **Owner:** TBD
- **Affected rules:** campaigns are first-class and wrap core runs; campaigns remain serious
- **Files likely touched:**
  - `planning/architecture/campaignspec_minimum_contract.md`
  - current community campaign config example and related notes
- **Required tests:** campaign boundary tests to be identified
- **Status:** open
- **Success criteria:** problem definition, fixed context, variable dimensions, stages, policy, budget, outputs, and reconstruction are explicit
- **Non-goals:** no full campaign package move yet

## Item 013 — widen StageSpec and PolicySpec on paper first
- **Change class:** contract hardening
- **Purpose:** preserve inner stage-engine substance while giving it a governed outer shape
- **Owner:** TBD
- **Affected rules:** campaigns remain serious; no toy wrappers
- **Files likely touched:**
  - `planning/architecture/stagespec_target_shape.md`
  - `planning/architecture/policyspec_target_shape.md`
- **Required tests:** stage progression tests identified
- **Status:** open
- **Success criteria:** current serious stage/policy behaviour is preserved in the target model
- **Non-goals:** no broad code edits yet

## Item 014 — define campaign and stage summary minimums
- **Change class:** contract hardening
- **Purpose:** make campaign-level projected views explicit without over-designing the analysis layer
- **Owner:** TBD
- **Affected rules:** campaign summary built from telemetry, ScorerReport, SolverReport, and stage outputs
- **Files likely touched:**
  - `planning/architecture/campaign_summary_minimum.md`
  - `planning/architecture/stage_summary_minimum.md`
- **Required tests:** campaign summary tests later
- **Status:** open
- **Success criteria:** summary minimum fields and non-goals are clear
- **Non-goals:** not building a rich dashboard layer

## Item 015 — queue first guardrail test additions
- **Change class:** contract hardening
- **Purpose:** lock behaviour before structural refactor
- **Owner:** TBD
- **Affected rules:** tests lock behaviour before structural refactor; parity before tidiness
- **Files likely touched:**
  - `tests/guardrails/`
  - `tests/api_contract/`
  - `tests/community/`
  - `tests/tools/`
- **Required tests:** new guardrails for second-surface drift, path leakage, campaign-local scorer contract, and silent default drift
- **Status:** open
- **Success criteria:** first missing anti-drift tests are written and passing or deliberately staged
- **Non-goals:** no broad refactor in the same slice
