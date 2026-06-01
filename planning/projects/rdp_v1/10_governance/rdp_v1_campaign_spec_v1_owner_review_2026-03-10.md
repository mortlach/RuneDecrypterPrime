# RDP v1 campaign spec — owner review draft 1
_Date: 2026-03-10_

## 1. Purpose

This document formalises the campaign layer for RDP v1.

It is written to match the owner-led governance direction and the campaign machinery that already exists in the codebase. It is not a greenfield redesign.

The goal is to turn the present campaign shape into a governed, readable, extensible first-class surface that can support the real LP attack work the project needs.

---

## 2. Campaign philosophy

In RDP, a **campaign** is the framework for **optimising the optimiser** against a specific problem and a specific range of input assumptions.

A campaign is not just a single run, and not merely a loose batch of runs. It is an orchestrated, data-integrated way to explore and compare meaningful variations in run configuration for a narrowly defined attack problem.

For v1, the real use of campaigns is LP-first. The present purpose is to support the strongest credible narrowly defined LP attacks the project can mount using the best understanding already gained from months of practical and community work.

Campaigns are general enough to support serious RDP attacks beyond LP, but their abstraction should be shaped by real attack practice rather than by a toy workflow taxonomy.

---

## 3. Non-goals

The campaign framework is **not**:
- a second solving architecture unrelated to RunSpec
- a campaign-local scoring contract
- a campaign-local output-writing system
- a place for magical opaque adaptive logic
- a licence for benchmark-local policy to leak into core silently

Campaigns wrap, organise, and analyse real runs. They do not replace the shared run world.

---

## 4. Boundary and ownership

### 4.1 Core owns

Core owns:
- RunSpec and the public run contract
- typed solving contracts
- scoring runtime
- ScorerReport and SolverReport
- formal rescoring support
- shared output and privacy rules
- shared asset logic

### 4.2 Campaign owns

Campaign owns:
- problem-space definition at campaign level
- chosen variable tuning dimensions
- stage structure
- stage progression policy
- survivor carry-forward and concentration logic
- retry, rescore, and bounded control-loop decisions
- campaign-level summaries and comparison views

### 4.3 Tools do not own campaign architecture

Benchmark and helper scripts may still exist during convergence, but the first-class campaign architecture belongs in a first-class `campaigns/` surface rather than quietly living in `tools/`.

---

## 5. Core concepts

### 5.1 Campaign

A campaign is a governed orchestration of runs over a defined problem space, where selected real run-config dimensions are exposed as variable tuning knobs and the campaign coordinates execution, comparison, and data integration across that space.

### 5.2 Engagement

An engagement is one concrete run instance inside a campaign. In practice this is a run created from a concrete RunSpec.

### 5.3 Stage

A stage is an ordered campaign step with a clear purpose, such as broad exploration, candidate filtering, survivor promotion, deeper concentration, or rescoring.

### 5.4 Campaign summary

A campaign summary is a campaign-level summary object built from telemetry, ScorerReport, SolverReport, and related stage outputs.

It is not the only representation of the underlying data. It is a projected or interpreted representation of campaign results in one or more useful spaces.

In the most abstract sense it is a campaign-level data analysis layer, not the sole truth store.

### 5.5 Reconstruction

Campaign outputs must preserve enough information to reconstruct what was run and what came out. If more detail is needed later, it must still be possible to rerun or rescore from preserved state and logical references.

---

## 6. Campaign problem model

A campaign should normally define five top-level things:

1. **Problem definition**  
   What narrow attack problem is being targeted.

2. **Fixed context**  
   What assumptions are held constant across the campaign.

3. **Variable dimensions**  
   The chosen countable subset of real tunable settings exposed for variation.

4. **Stage plan and policy**  
   How the campaign moves through layered attack steps, selection, retries, concentration, and optional rescoring.

5. **Outputs and reconstruction**  
   What the campaign emits for quick judgement, later comparison, and reliable reconstruction.

---

## 7. Campaign tuning dimensions

### 7.1 Rule

Campaign variation must come from a **chosen countable subset** of valid real run settings, assumptions, or ranges.

If a setting is a real part of valid run configuration or real run shaping, it may in principle be exposed as a campaign tuning dimension.

### 7.2 Typical examples

Examples may include:
- method subset
- text-length assumptions
- cipher assumptions
- transposition settings
- interrupter assumptions
- reading-order, reversal, or boustrophedon assumptions
- scorer choices or scorer-role schedules
- solver settings
- search budget settings
- stage thresholds or promotion counts

### 7.3 Countability rule

The variable dimensions must be describable as a countable search space.

Some dimensions may have very small ranges and some very large ones. That is fine. The important thing is that they are honestly defined and checkable.

### 7.4 Search-space description rule

The preferred campaign search-space description is **explicit dimensions and ranges**, because that is easier to understand and review.

Generator-style search definitions may be supported where useful, but they should still yield a clear enumerable search space in practice.

---

## 8. Campaign stages

### 8.1 Stages are essential

Stages are first-class campaign structure.

For LP they are expected to be central rather than optional garnish.

### 8.2 Typical stage purposes

Common stage purposes may include:
- broad exploration
- candidate filtering
- diversity preservation
- survivor carry-forward
- later concentration
- formal rescoring
- final comparison or narrowing

### 8.3 Stage defaults

The framework may provide a small standard set of stage and policy defaults.

Those defaults should be enough for the full LP campaign the project actually wants to run, while remaining extensible rather than restrictive.

### 8.4 Explicitness with defaults

A campaign should normally make clear:
- what problem is being attacked
- what is fixed
- what is variable
- how stages progress
- what outputs are produced

Defaults are allowed where helpful, but they must live inside the governed campaign surface, not as hidden local behaviour.

---

## 9. CampaignSpec

### 9.1 Role

CampaignSpec is the top-level serialisable description of a campaign.

### 9.2 Minimum required fields

The minimum required fields are:
- `campaign_spec_version`
- `campaign_id`
- `campaign_kind`
- `campaign_seed`
- `problem_definition`
- `fixed_context`
- `variable_dimensions`
- `stages`
- `policy_spec`
- `budget_spec`
- `output_policy`
- `asset_refs`
- `notes`

Where relevant, CampaignSpec may also include:
- `git_sha`
- `required_backend`
- `caps`
- `fixtures` or fixture-set refs
- `determinism_mode`

### 9.3 Campaign kind rule

`campaign_kind` is descriptive and validating. It is not meant to cap the actual seriousness of the workflow.

It exists to help identify and validate the broad campaign pattern being used, not to force all campaigns into a tiny menu of toy types.

### 9.4 Existing code mapping

The current community example config already shows part of the outer CampaignSpec shape:
- `campaign_spec_version`
- `campaign_id`
- `git_sha`
- `campaign_seed`
- `fixtures`
- grid-like variable dimensions
- `profile_ids`
- `required_backend`
- `caps`
- `notes`

That existing shape should be kept and generalised, not discarded.

---

## 10. StageSpec

### 10.1 Role

StageSpec is the serialisable description of one ordered stage within a campaign.

### 10.2 Minimum required fields

The minimum required fields are:
- `stage_id`
- `stage_kind`
- `purpose`
- `input_source`
- `run_spec_template` or `run_specs`
- `variable_dimensions` or stage-local search slice
- `selection_rule`
- `output_artefact_policy`

Optional fields may include:
- `rescore_step`
- `stop_condition`
- `promotion_rule`
- `diversity_rule`
- `telemetry_options`
- `params` for truly stage-local extras that do not yet deserve promoted first-class fields

### 10.3 Existing code mapping

The present `StageSpec` in `tools/benchmarks/periodic_sub_trans/common/stage_spec.py` already contains real stage substance:
- `stage_id`
- `search_objective`
- `decision_objective`
- `aux_objectives`
- `pool_keep`
- `promote_top`
- `basin_cap`
- `params`

That should be treated as a strong existing stage-execution core.

For the formal v1 spec, this shape should be widened so that outer campaign concepts such as stage purpose, input source, run-spec generation, selection, and output policy are stated explicitly.

### 10.4 Aux objectives and scorer roles

Auxiliary objectives and scorer-role scheduling are real and useful. They should survive.

The convergence task is to place them cleanly inside a governed stage/policy structure rather than leaving them as copied dict patterns or hidden local conventions.

---

## 11. PolicySpec

### 11.1 Role

PolicySpec is the campaign-level policy object that governs progression, selection, retry, survivor handling, and bounded adaptation.

### 11.2 Minimum required areas

PolicySpec should cover at least:
- stage progression rules
- selection rules
- retry rules
- budget and stop rules
- survivor or diversity rules
- batching rules where relevant
- rescore rules where relevant
- resume rules

### 11.3 Existing code mapping

The present `AdaptivePolicySpec` already contains a real inner policy slice:
- `policy_id`
- `tie_band_eps`
- `ambiguity_expand_top_k`
- scaling rules
- `params`

That should be treated as an existing **inner adaptive-selection policy block**, not as the whole final outer PolicySpec.

The v1 convergence task is to wrap this kind of real policy behaviour inside a broader formal policy surface.

### 11.4 Bounded control loops

Simple bounded control loops are allowed and expected where needed.

Examples include:
- keep collecting candidate trials until a count target is met
- keep collecting until a diversity target is met
- stop after explicit iteration, time, or compute budgets
- batch survivors according to explicit rules

Deep opaque learning or auto-derived search redesign belongs mainly outside v1 campaign logic.

---

## 12. Search-space execution model

### 12.1 Broad rule

Campaigns are free to organise search broadly so long as they remain honest about the problem definition, variable dimensions, stages, and outputs.

### 12.2 Allowed patterns

The framework should support, at minimum:
- full grids
- targeted sweeps
- explicit stage-to-stage narrowing
- survivor carry-forward
- retry under budget rules
- formal rescoring stages
- reservoir-like collection and later batching patterns where needed

### 12.3 Reservoirs, batching, and survivor structures

Reservoirs, batching, and survivor structures should be treated as **framework-supported patterns**, not the sole definition of campaigns.

That keeps the campaign layer extensible while still letting serious LP attack patterns be first-class and well supported.

---

## 13. Resume, determinism, and reconstruction

### 13.1 Determinism rule

Campaigns must preserve enough information for deterministic replay where that is part of the supported workflow.

### 13.2 Minimum campaign-level retained state

At minimum, campaign state should preserve:
- campaign identity and version
- campaign seed
- stage identities and status
- concrete RunSpec or the information needed to reconstruct it deterministically
- selected survivors or logical refs to them
- policy state needed for explicit bounded control loops
- linked report refs
- logical asset refs

### 13.3 Reconstruction rule

At minimum, the campaign must preserve enough information that the solve can be reconstructed later, even if a rerun is needed to collect more detail.

Campaign-level outputs should also surface the big-ticket items needed for quick checking and comparison.

### 13.4 Relationship to SolverReport and ScorerReport

Campaign reconstruction does not replace run-level reporting.

Campaign summary should build on telemetry, ScorerReport, SolverReport, and related stage outputs rather than inventing a detached rival truth store.

---

## 14. Campaign outputs

### 14.1 Minimum outputs

A campaign should emit:
- campaign summary
- stage summaries
- linked run reports
- comparison summaries
- telemetry summaries
- logical artefact refs

### 14.2 CampaignSummary

CampaignSummary is a campaign-level summary object built from lower-level reports and telemetry.

Its job is to present useful projected views of the campaign results, not to monopolise the underlying truth.

### 14.3 StageSummary

Each stage should emit a stage summary describing, at minimum:
- stage identity
- stage purpose
- input size or source summary
- output size or survivor summary
- key selection or promotion outcomes
- stop or completion status
- linked artefact refs

### 14.4 Opt-in telemetry views

The campaign system should support opt-in telemetry outputs to help with optimisation and later analysis.

These should remain governed, portable, and privacy-safe.

### 14.5 Privacy and output rules

Campaigns may choose what to emit, but they must use the shared writer and shared privacy rules.

Absolute paths must not appear in portable outputs.

---

## 15. Existing code mapping summary

The present code already gives a strong starting point.

| Existing code | Current role | Draft formal role |
|---|---|---|
| `tools/benchmarks/community/examples/campaign_config_v1_1.json` | outer campaign config example | seed of CampaignSpec boundary form |
| `tools/benchmarks/periodic_sub_trans/common/stage_spec.py::StageSpec` | stage-execution object | strong inner StageSpec core to keep and widen |
| `tools/benchmarks/periodic_sub_trans/common/policy_spec.py::AdaptivePolicySpec` | adaptive selection policy slice | inner policy block inside wider PolicySpec |
| `tools/benchmarks/periodic_sub_trans/common/stage_engine.py::StageEngine` | ordered stage sequencer with events and pool shaping | generic campaign/stage engine seed to keep and narrow |

This is why the current task is best understood as extraction, cleanup, and formalisation rather than zero-to-one invention.

---

## 16. Convergence goals for implementation planning

The implementation plan built from this spec should aim to:
- extract the formal campaign surface from the existing code
- simplify override and switch sprawl into named policy blocks
- separate outer campaign definition from stage internals and runner-local plumbing
- preserve full LP-attack capability
- make deterministic resume and reconstruction explicit
- move important campaign architecture toward first-class `campaigns/` ownership
- add campaign-level contract tests and parity gates

---

## 17. Things intentionally left flexible

This spec does **not** yet over-formalise:
- the final detailed campaign-summary analysis space
- the exact final package names
- the exact final internal class names
- the full long-term set of advanced generator-style search helpers

Those should remain implementation-planning or later evolution questions unless they block the immediate convergence work.
