# RDP v1 implementation task register
## phase-by-phase task register for review

_Date: 2026-03-11_

## Effort bands
- S: 1–2 days
- M: 3–5 days
- L: 1–2 weeks
- XL: 2–4 weeks
- XXL: 1–2 months

## Overall scale
Rough guide for one careful maintainer:
- planning/control pack + mapping: 2–3 weeks
- contract hardening before campaign lift: 4–7 weeks
- campaign façade + ownership lift: 8–14 weeks
- proof pass + release alignment: 2–4 weeks

This is broadly 4–6 months of stop-start convergence work for one careful maintainer.

---

# Phase 0 — planning/control pack and mapping

## P0.1 Create the private planning/control pack
Goal:
Create the files that make the handbook real instead of aspirational.

Current promoted equivalents:
- `planning/projects/rdp_v1/20_active_plans/CURRENT_PHASE_v1_2026-03-11.md`
- `planning/projects/rdp_v1/20_active_plans/ACTIVE_TODO_v0_2.md`
- `planning/projects/rdp_v1/20_active_plans/CURRENT_RISKS_v1_2026-03-11.md`
- `planning/projects/project_workflow/10_schema_and_rules/AGENT_UPDATE_AND_LOGGING_RULES_V1.md`
- `planning/projects/project_workflow/20_templates/RESULT_NOTE_TEMPLATE_V1.md`
- `planning/projects/project_workflow/20_templates/STATUS_LEDGER_TEMPLATE_V1.md`

Effort: M

Main risks:
- becoming too vague
- duplicating architecture truth that should live in public-safe docs
- turning into a junk drawer

Acceptance checks:
- each file exists and is populated
- `CURRENT_PHASE.md` says plainly what must not be weakened
- `ACTIVE_TODO.md` links each item to rationale, owner, rules, tests, status, and non-goals
- handbook read-first order is copied into the workflow pack

## P0.2 Create the ADR starter set
Goal:
Stop the same architecture arguments being reopened in every slice.

Likely files:
- `planning/decisions/ADR-0001-core-strict-boundary-forgiving.md`
- `ADR-0002-enums-in-core.md`
- `ADR-0003-first-class-campaign-surface.md`
- `ADR-0004-runspec-front-door.md`
- `ADR-0005-one-output-owner.md`
- `ADR-0006-no-wli-first-class.md`
- `ADR-0007-scorerreport-and-solverreport.md`
- `ADR-0008-assets-problem-sources-fixtures-split.md`
- `ADR-0009-support-matrix-binding.md`
- `ADR-0010-preserve-flagship-lp-capability.md`

Effort: M

Acceptance checks:
- all 10 ADRs exist in lightweight form
- each links to rules, tests, and affected files
- no ADR contradicts charter/spec/handbook order of truth

## P0.3 Write the current-code mapping note
Goal:
Meet Gate 3 before major refactor work.

Likely files:
- `planning/architecture/current_code_mapping_note.md`

Must include:
- current run/front-door area
- current scoring/report area
- current outer campaign area
- current inner stage-engine area
- current output/privacy area
- current LP/assets area

Effort: M

Main risks:
- guessing ownership
- collapsing outer and inner campaign surfaces into one vague blob

Acceptance checks:
- each workstream has current owner/de facto owner, target owner, risk note, and required test gates
- outer community campaign config and inner `StageSpec`/`AdaptivePolicySpec`/`StageEngine` surfaces are explicitly distinguished
- note is good enough that an agent could pick files without guessing

## P0.4 Build the first findings register and workstream index
Goal:
Give agents a structured list of known issues, not scattered chat memory.

Current promoted equivalents:
- `planning/projects/rdp_v1/40_supporting_reference/support_matrices/31_support_matrices/findings_register.csv`
- `planning/projects/rdp_v1/01_WORKSTREAM_INDEX.md`

Effort: S

Acceptance checks:
- every finding has area, priority, risk, linked rules, linked tests, likely files
- campaign/report/output/privacy findings are not buried under “cleanup”

---

# Phase 1 — support matrix lock-down and guardrail scaffolding

## P1.1 Freeze matrix wording and cell meaning
Goal:
Turn the matrix from “aspiration sheet” into a reviewable contract.

Likely files:
- support matrix workbook / CSV
- `planning/architecture/support_matrix_cell_meanings.md`

Effort: M

Main risks:
- wording that sounds universal when it really means “where relevant”
- unclear unsupported-combination behaviour

Acceptance checks:
- each cell meaning is defined
- “Yes”, “Where relevant”, “Limited”, and “Not supported” have explicit review meaning
- unsupported combinations are expected to fail clearly and consistently

## P1.2 Map support cells to tests
Goal:
Create the first proof scaffold.

Current promoted equivalents:
- `planning/projects/rdp_v1/40_supporting_reference/support_matrices/31_support_matrices/support-to-test_map_7.txt`
- updates to `planning/projects/rdp_v1/20_active_plans/ACTIVE_TODO_v0_2.md`

Likely source areas:
- `tests/api/`
- `tests/api_contract/`
- `tests/ui_normalize/`
- `tests/scoring/`
- `tests/community/`
- `tests/tools/`
- `tests/guardrails/`

Effort: M

Acceptance checks:
- each important matrix row has at least one positive proof and, where relevant, one negative/failure proof
- gaps are named rather than hand-waved

## P1.3 Add missing anti-drift guardrails
Goal:
Before architecture work, add tests that stop common wrong moves.

Likely files:
- new tests under:
  - `tests/guardrails/`
  - `tests/api_contract/`
  - `tests/community/`
  - `tests/tools/`

Guardrail themes:
- no second config surface
- no absolute-path leakage
- no campaign-local scorer contract
- no hidden benchmark-local policy in core
- no silent default drift

Effort: L

Acceptance checks:
- handbook enforcement-map gaps become smaller, especially output owner, LP capability, and second-surface drift

---

# Phase 2 — output/privacy and report contract stabilisation

## P2.1 Inventory current output/privacy owners
Goal:
Make the current fragmentation explicit before changing anything.

Likely files:
- `src/rune_decrypter_prime/io/run_logger.py`
- `src/rune_decrypter_prime/core/config/logging_config.py`
- `tools/benchmarks/periodic_sub_trans/common/io_reports.py`
- `tools/benchmarks/periodic_sub_trans/common/trace_writer.py`
- `tools/benchmarks/periodic_sub_trans/common/paths.py`
- `tools/benchmarks/community/_campaign_common.py`
- `tools/benchmarks/community/run_shard.py`

Effort: S

Acceptance checks:
- one short inventory note exists
- every writer/policy owner has current role and target owner

## P2.2 Define the shared output/privacy contract
Goal:
Write the minimum stable contract before code movement.

Likely files:
- `planning/architecture/output_privacy_contract.md`
- `ADR-0005`

Contract topics:
- JSON/JSONL rules
- canonical JSON for hashing
- path redaction
- identity redaction
- trace placement
- telemetry placement
- logical artefact refs only in portable outputs

Effort: M

Acceptance checks:
- contract is small and clear
- tests can be written against it

## P2.3 Stabilise ScorerReport minimum contract
Goal:
Stop report drift between core and campaign projections.

Likely files:
- `src/rune_decrypter_prime/scoring/scorer_report.py`
- `src/rune_decrypter_prime/scoring/scorer_report_builder.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/word_ngram_report.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_finalize.py`
- related tests in `tests/scoring/` and `tests/tools/`

Effort: L

Acceptance checks:
- minimum ScorerReport fields are written down
- report creation is centralised or clearly owned
- no-WLI projections use the shared report truth rather than ad hoc copied subsets where avoidable

## P2.4 Land minimum SolverReport
Goal:
Make SolverReport real rather than only governed in docs.

Likely files:
- new or updated files under `src/rune_decrypter_prime/scoring/` or adjacent reporting package
- tests under `tests/scoring/`, `tests/api_contract/`, `tests/community/`

Effort: L

Acceptance checks:
- SolverReport minimum contract exists in code and docs
- campaign summary can link/build from it without inventing a detached truth store

## P2.5 Formal rescoring retained-state contract
Goal:
Make later rescoring/reconstruction reliable and explicit.

Likely files:
- report/rescoring design note
- relevant scoring/campaign code once identified in mapping note
- tests under `tests/scoring/`, `tests/community/`, `tests/tools/`

Effort: M to L

Acceptance checks:
- minimum retained state is documented
- rerun/rescore path is testable
- campaign summaries surface big-ticket results without monopolising truth

---

# Phase 3 — RunSpec / front-door convergence

## P3.1 Inventory current front-door surfaces
Goal:
Be explicit about what currently acts as the public run boundary.

Likely files:
- `src/rune_decrypter_prime/api/run.py`
- `src/rune_decrypter_prime/api/specs.py`
- `src/rune_decrypter_prime/api/normalize.py`
- `src/rune_decrypter_prime/core/config/run.py`
- related tests under `tests/api/`, `tests/api_contract/`, `tests/ui_normalize/`

Effort: S

Acceptance checks:
- one inventory note names current surfaces, target surface, and known overlap

## P3.2 Define the minimum RunSpec
Goal:
Lock the first-release public run contract before wide code edits.

Likely files:
- `ADR-0004`
- `planning/architecture/runspec_minimum_contract.md`
- eventual source implementation files above

Effort: M

Acceptance checks:
- contract is serialisable
- supported combinations and clear failures are defined
- tutorials, API use, LP helpers, and campaigns are all named as consumers

## P3.3 Introduce RunSpec behind an adapter bridge
Goal:
Land the real contract without breaking everything at once.

Likely files:
- same front-door files as above
- possibly light bridging/adaptation helpers
- tests in `tests/api*`

Effort: L

Acceptance checks:
- one canonical entrypoint exists
- temporary bridge has written exit plan and tests
- unsupported combinations fail clearly

## P3.4 Route tutorials, direct runs, and campaign-generated runs through the same front door
Goal:
Make the architecture honest.

Likely files:
- tutorials/examples
- API callers
- campaign-generated run creation points
- regression tests

Effort: L

Acceptance checks:
- tutorials remain regression consumers of the real system
- campaign-generated runs produce real RunSpec instances or equivalent deterministic reconstruction data

---

# Phase 4 — first governed campaign façade

## P4.1 Define the minimum outer CampaignSpec
Goal:
Turn today’s community config shape into the formal outer campaign boundary.

Likely files:
- `tools/benchmarks/community/examples/campaign_config_v1_1.json`
- `planning/architecture/campaignspec_minimum_contract.md`
- later real source package files

Effort: M

Acceptance checks:
- minimum campaign fields are written down
- variable dimensions, fixed context, stage plan/policy, outputs, and reconstruction are explicit

## P4.2 Widen StageSpec without losing current substance
Goal:
Keep today’s strong inner stage core while making outer stage concepts explicit.

Likely files:
- `tools/benchmarks/periodic_sub_trans/common/stage_spec.py`
- stage-related tests
- design note for widened stage contract

Effort: L

Acceptance checks:
- current useful fields such as search/decision/aux objectives, pool/promotion behaviour, and params are preserved or deliberately re-homed
- formal stage contract includes stage purpose, input source, run-spec generation/search slice, selection, and output policy

## P4.3 Wrap AdaptivePolicySpec inside a broader PolicySpec
Goal:
Preserve real adaptive selection behaviour but stop pretending it is the whole campaign policy model.

Likely files:
- `tools/benchmarks/periodic_sub_trans/common/policy_spec.py`
- selection/policy tests
- design note / ADR link

Effort: L

Acceptance checks:
- outer policy areas are explicit: progression, selection, retry, budget/stop, survivor/diversity, batching where relevant, rescore, resume
- current adaptive selection slice survives inside the wider model

## P4.4 Define minimum CampaignSummary and StageSummary
Goal:
Stabilise the minimum campaign-level projected views without over-designing the long-term analysis layer.

Likely files:
- campaign summary types / notes
- `StageSummary` / `CampaignSummary` tests
- maybe shared summary builder helpers later

Effort: M

Acceptance checks:
- campaign summary is explicitly built from telemetry, ScorerReport, SolverReport, and stage outputs
- stage summary minimum fields exist
- summary remains projected/interpreted rather than monopolising truth

## P4.5 Build a governed façade over the current stage engine
Goal:
Preserve behaviour while changing ownership and public shape.

Likely files:
- `tools/benchmarks/periodic_sub_trans/common/stage_engine.py`
- community campaign runner files
- new façade package files
- campaign progression tests

Effort: XL

Acceptance checks:
- façade can express current serious LP stage flow
- retries, survivor flow, bounded loops, and rescoring remain first-class
- bridge is documented with exit path if temporary

## P4.6 Make no-WLI the first serious façade consumer
Goal:
Use the hardest real flow as the proving ground.

Likely files:
- `tools/benchmarks/periodic_sub_trans/no_wli/*`
- associated tests in `tests/tools/` and `tests/community/`

Effort: XL

Acceptance checks:
- no-WLI can run through the governed façade without capability loss
- current tuning changes remain behaviour corrections, not architectural side roads
- parity notes are kept honest

---

# Phase 5 — campaign ownership lift and de-localisation

## P5.1 Create the first-class campaigns package surface
Goal:
Move campaign architecture toward its intended home.

Likely files:
- new `src/rune_decrypter_prime/campaigns/` package
- import bridges
- docs/tests touching campaign package paths

Effort: L

Acceptance checks:
- real first-class campaign surface exists
- important campaign architecture is no longer only benchmark folklore

## P5.2 Move generic pieces before runner-local pieces
Goal:
Separate genuinely generic campaign machinery from no-WLI/sub-then-col/col-then-sub local plumbing.

Likely files:
- generic stage/policy/summary components
- runner-specific wrappers remain temporarily local

Effort: L

Acceptance checks:
- moved pieces are truly reusable
- runner-local assumptions are still visible and test-backed

## P5.3 Reduce override and switch sprawl into named policy blocks
Goal:
Simplify expression of current behaviour without weakening it.

Likely files:
- no-WLI and common campaign policy/config files
- maybe shared policy block modules
- tests for selection, retry, survivor/diversity, batching, budgets, resume, telemetry options

Effort: XL

Acceptance checks:
- named policy blocks exist
- same real behaviour is expressible with less local sprawl
- tests prove preserved outcomes on flagship paths

## P5.4 Remove duplicate helpers and shim debt
Goal:
Clean up only after convergence surfaces are stable.

Likely files:
- duplicated config helpers
- runner-local writers
- old path helpers
- obsolete bridges

Effort: M to L

Acceptance checks:
- every removed shim has a written replacement
- no hidden side contract survives

---

# Phase 6 — LP/assets alignment

## P6.1 Finalise asset manifest rules
Goal:
Move from “some manifest support exists” to a governed v1 asset story.

Likely files:
- `assets_manifest_v1.json`
- `src/rune_decrypter_prime/data/asset_paths.py`
- asset governance note / ADR
- guardrail tests

Effort: M

Acceptance checks:
- logical asset ids and versions are clear
- portable refs are used in reports/campaign state where relevant

## P6.2 Align LP problem sources with the shared contracts
Goal:
Ensure LP domain helpers are real consumers of the shared run/campaign model, not a side door.

Likely files:
- `src/rune_decrypter_prime/data/liber_primus/*`
- related tests in `tests/data/` and `tests/guardrails/`

Effort: L

Acceptance checks:
- LP problem sources fit the agreed boundary model
- tutorials and campaign flows can use LP support honestly through shared contracts

## P6.3 Re-check tutorial parity against LP-first truth
Goal:
Keep tutorials useful and honest.

Likely files:
- tutorial/example sources and tests

Effort: M

Acceptance checks:
- tutorials still exercise the real system
- presence of tutorial-only ciphers is not confused with first-release public support promise

---

# Phase 7 — proof pass and release proof

## P7.1 Support proof pack
Goal:
Show the support matrix is proved, not merely asserted.

Likely files:
- `planning/release/v1_release_gate.md`
- `planning/release/docs_alignment_checklist.md`
- support proof summary

Effort: M

Acceptance checks:
- support-matrix cells map to actual tests and real pass/fail evidence

## P7.2 Campaign progression and reconstruction proof
Goal:
Prove the flagship campaign story survives convergence.

Likely files:
- campaign proof note
- tests in `tests/community/` and `tests/tools/`

Effort: M to L

Acceptance checks:
- stage progression, survivor flow, retries, rescoring, and reconstruction are test-proven on the flagship path

## P7.3 Output/privacy proof
Goal:
Prove portability and privacy, not just assume them.

Likely files:
- output/privacy tests
- release checklist

Effort: M

Acceptance checks:
- no absolute paths in portable outputs
- shared writer rules are actually enforced

## P7.4 Docs alignment proof
Goal:
Ensure public-safe docs, private notes, tests, and code say the same thing.

Likely files:
- charter/spec/plan final pack
- handbook
- ADRs
- release checklist

Effort: S to M

Acceptance checks:
- stable truths are mirrored into public-safe docs and tests, as the handbook requires

---

# Suggested first ticket stack

1. P0.1 planning/control pack
2. P0.3 current-code mapping note
3. P1.1 matrix wording + cell meanings
4. P1.2 support-to-test mapping
5. P2.1 output/privacy owner inventory
6. P2.3 ScorerReport minimum contract
7. P3.1 front-door surface inventory

# What should stay out of scope for now

Do not do these early:
- broad tree moves
- rename-driven cleanup
- campaign package relocation before façade/gates exist
- speculative new feature families
- over-designed long-term campaign analysis layer
- “temporary” second front doors that are likely to stick
