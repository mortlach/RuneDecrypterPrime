# Cipher-development lessons

## Purpose

This registry preserves lessons that should survive individual runs, campaign changes and chat boundaries. It is manually curated from reviewed evidence. Runtime code and milestone synthesis never edit this file automatically.

## Status definitions

- `candidate`: plausible, but not yet supported by enough reviewed evidence;
- `supported`: backed by reviewed evidence in at least one relevant campaign;
- `general`: independently supported across materially different campaigns;
- `limited`: useful only within the stated scope or with important qualifications;
- `superseded`: retained for history and linked to a replacement;
- `rejected`: retained because evidence contradicted it.

## Evidence requirements

Implementation alone is not evidence that a solver technique works. Canaries may support engineering and reproducibility lessons, but they cannot establish solver-performance claims. Evidence should cite committed code, run IDs, configuration hashes and persisted artifacts where available.

## Promotion procedure

Promotion is a human decision. Review the raw experiment result, candidate artifacts, replay evidence, milestone synthesis and known limits before changing a status. Record the evidence reviewed in the lesson entry.

## Supersession procedure

Lesson IDs are never reused or deleted. A superseded lesson remains visible and names its replacement. Rejected lessons also remain visible.

## Review rules

- Keep search-visible evidence separate from benchmark truth.
- Prefer exact artifact and run identifiers over narrative recollection.
- State counterexamples and limits.
- Do not infer a general lesson from one campaign.
- Do not promote lessons automatically.

No general solver-performance lesson has yet been promoted from WP3 or WP4.

## CSL-001 — Persist exact candidates, not only best scores

Status: supported

Category: engineering

Scope: all cipher-development campaigns

Observation: A score without the corresponding exact candidate cannot be replayed, independently checked or handed to another method.

Operational implication: Persist candidate identity, payload, named scores and provenance in a content-addressed archive or replay batch.

Evidence: WP2 archive/replay contracts; WP3 and WP4 final-candidate persistence; review corrections that added missing control/final candidates.

Counterexamples or limits: Large payloads belong in runtime artifacts, not ledgers or permanent documentation.

Last reviewed: 2026-07-22

Supersedes: none

Superseded by: none

## CSL-002 — Terminally evaluated candidates must be persisted

Status: supported

Category: methodological

Scope: benchmark and comparison runs

Observation: Terminal reference evaluation is reproducible only when the evaluated candidate ID, originating arm and containing artifact are recorded.

Operational implication: Before terminal truth evaluation, verify that the candidate exists in a persisted archive or replay batch.

Evidence: WP3 evidence-contract review and correction; WP4 best-candidate artifact contract.

Counterexamples or limits: Truth-free production runs may omit reference evaluation but still require candidate persistence.

Last reviewed: 2026-07-22

Supersedes: none

Superseded by: none

## CSL-003 — Handoff comparisons must not introduce unrelated restarts

Status: limited

Category: methodological

Scope: seeded handoff and exploitation comparisons

Observation: A random restart hidden inside a seeded solver run can win and make the reported result unrelated to the selected candidate.

Operational implication: Each comparison trajectory starts from the selected candidate. Independent random starts belong in an explicit control arm.

Evidence: WP4 exploitation-contract review and correction.

Counterexamples or limits: Production solvers may legitimately mix seeded and random restarts when the experiment is not attempting to measure handoff quality.

Last reviewed: 2026-07-22

Supersedes: none

Superseded by: none

## CSL-004 — Search-visible evidence must remain separate from truth

Status: supported

Category: engineering

Scope: all benchmark campaigns

Observation: Truth-bearing fields in configurations, candidate payloads or replay contexts can leak into ranking, stopping or interpretation.

Operational implication: Keep plaintext, known keys and match metrics in terminal reference objects only. Reject truth/reference field names in shared evidence contracts.

Evidence: WP1 experiment contract; WP2 archive guards; WP3 and WP4 truth-boundary reviews.

Counterexamples or limits: A clearly labelled benchmark reference evaluator may use truth after search has completed.

Last reviewed: 2026-07-22

Supersedes: none

Superseded by: none

## CSL-005 — Canaries validate execution, not scientific hypotheses

Status: supported

Category: methodological

Scope: all campaign canary profiles

Observation: Small smoke budgets can prove construction, bounded execution and artifact validity but are underpowered scientific comparisons.

Operational implication: Canary runs always return `refine` and make no promote/close claim.

Evidence: WP3 and WP4 decision contracts.

Counterexamples or limits: A canary may support an engineering lesson such as deterministic replay.

Last reviewed: 2026-07-22

Supersedes: none

Superseded by: none

## CSL-006 — Policy comparisons must state every scoring difference

Status: limited

Category: methodological

Scope: ranking and scoring-policy comparisons

Observation: Comparing a raw full-text character score with a calibrated character-plus-WLI score changes more than WLI alone.

Operational implication: Describe the complete policies being compared and avoid claiming a single-component causal effect without a true ablation.

Evidence: WP4 review and campaign clarification.

Counterexamples or limits: A dedicated ablation may hold every other scoring field constant.

Last reviewed: 2026-07-22

Supersedes: none

Superseded by: none

## CSL-007 — Saved candidate surfaces permit reranking without rediscovery

Status: candidate

Category: scientific

Scope: candidate archives with replayable score contexts

Observation: A retained candidate surface should allow later score verification or reranking without repeating expensive discovery.

Operational implication: Persist a truth-free replay context beside candidate batches and verify it through deterministic replay.

Evidence: WP5 implementation contract only; real campaign replay evidence is still pending.

Counterexamples or limits: A saved surface cannot answer questions about candidates that discovery never generated.

Last reviewed: 2026-07-22

Supersedes: none

Superseded by: none
