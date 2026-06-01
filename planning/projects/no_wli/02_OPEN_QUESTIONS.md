# Open questions

## P0 - next branch questions

### 0A. What should happen after broad local-rescue policy widening closed?

Status:

- active decision / external review

Current answer:

- do not launch another broad local-rescue runtime batch from the current
  evidence
- local rescue is real, but the current acceptance/policy layer is not
  policy-clean
- the latest acceptance-boundary audit found no perfect action-safe
  single-rule or two-feature separator

Review handoff:

- synthesis:
  - `planning/projects/no_wli/40_review_summaries/no_wli_solver_development_pivot_synthesis_2026-05-02.md`
- review pack:
  - `planning/projects/no_wli/40_review_summaries/no_wli_solver_development_pivot_review_pack_2026-05-02/`
- sendable zip:
  - `planning/projects/no_wli/40_review_summaries/no_wli_solver_development_pivot_review_pack_2026-05-02.zip`

Recommended next:

- build an experiment ledger / oracle-gap layer over retained outputs
- or, if review prefers direct validation, write a held-out validation harness
  for the Stage-2 checkpoint line before more runtime

### 0. Can late-stage-only handoff/archive rescue improve the retained `1111` focus-family lanes without recomputing full pipelines?

Status:

- active planning
- branch:
  - `stage35_resume_from_handoff_focus_family_rescue_v1`
- plan:
  - `planning/projects/no_wli/20_active_plans/no_wli_stage35_resume_from_handoff_focus_family_rescue_plan_2026-04-29.md`

Question:

- broad saved-surface reshuffling did not beat reorder-only controls
- the six-job Stage-3 entry full-pipeline panel capped after one completed
  control job
- retained handoff/archive artefacts now exist for the priority `1111` lanes
- can a late-stage-only selector or rescue variant improve the retained result
  without paying another full-pipeline cost?

Target order:

- `1111/search7005`
  - primary selector/rescue headroom target
- `1111/search7004`
  - secondary fragmentation target
- `1111/search7002`
  - control / proof-of-runner target

Needed evidence before any runtime launch:

- one repo-local inventory of the handoff/archive inputs:
  - complete:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T043455Z__stage35_resume_from_handoff_focus_family_rescue_v1/`
  - result:
    - `3 / 3` target handoff roots feasible
    - `17 / 17` archive seed rows have selected-row key/plaintext material
    - `artifact_resume.run_stage35_from_selected_trial_row` can be used without
      upstream recompute
    - selected-row headroom:
      - `1111/search7005`:
        - `+0.044`
      - `1111/search7004`:
        - `+0.009`
    - `1111/search7002`:
      - `-0.002`
- one late-stage-only runner or extractor that does not recompute Stage 1,
  Stage 2, Stage 3 Phase A, Phase B, and Phase C from scratch
  - smoke preflight complete:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T044610Z__stage35_resume_from_handoff_focus_family_rescue_v1__smoke_preflight/`
  - result:
    - selected-row loading and partial/progress writeback work
    - real science runtime launched:
      - `0`
- one explicit timing estimate from retained references or a completed
  same-family canary
  - retained same-lane Stage 3.5 anchor:
    - `1111/search7005`
    - `1996.242s`
    - about `33m16s`
- one stop condition
  - proposed for the first real micro-canary:
    - stop after one bounded Stage 3.5 round or `3600s`, whichever comes first

Current guard:

- do not launch a run expected to take about an hour or more without asking
  first
- because the `7005` real micro-canary estimate is close to the one-hour guard
  after margin, require explicit launch confirmation
- do not launch another full-pipeline panel as the next step
- do not use the incomplete v79 candidate comparison as evidence for
  `constant_local_depth`

Newest evidence:

- first real selected-row `7005` run:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T060445Z__stage35_resume_from_handoff_focus_family_rescue_real_7005_v1__real_selected_best_frontier_one_round/`
- result:
  - retained:
    - `0.372`
  - selected start:
    - `0.416`
  - resume best:
    - `0.416`
  - accept reason:
    - `search_score_drop_guard_failed`
  - elapsed:
    - `2.991s`
- current recommendation:
  - same-target `7005` guard-selector follow-up accepted a real improvement:
    - accepted resume best `0.422`
    - `+0.050` versus retained
    - `+0.006` versus selected-row start
    - selected candidate `7068135ec036da03`
  - `7004` secondary confirmation did not repeat under the strict guard:
    - selected-row start `0.432`
    - reported local top resume `0.425`
    - accept reason `search_score_drop_guard_failed`
    - selected `0`
    - rank 6 was truth-positive at `0.438` but failed the search-score guard
  - close the strict runtime shape as mixed
  - first offline guard-selector archive policy audit is complete:
    - `2` cases
    - `24` archive rows
    - accepted-positive cases `1 / 2`
    - cases with blocked truth-positive rows `1 / 2`
  - next open question is whether a broader offline guard-relaxation/policy
    audit over retained Stage 3.5 archives is justified before any more runtime

Success condition:

- a late-stage-only comparison produces interpretable result deltas against
  retained anchors and preserves enough partial artefacts to extract incomplete
  work if capped

Failure / close condition:

- if the handoff/archive path cannot isolate late-stage work, close this
  branch as not ready and design a cheaper static archive analysis first

### 1. Can the selector checkpoint handoff be reconciled into an evidence-clean external review package?

Status:

- closed 2026-04-25
- answer:
  - yes; the subtopic is review-ready after provenance reconciliation
- final audit:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260425T190612Z__stage2_topk_selected_family_low_edge_phasea_checkpoint_best_init_window_family_provenance_audit_v1/`
- handoff:
  - review pack:
    - `planning/projects/no_wli/40_review_summaries/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_review_pack_2026-04-25.zip`
  - paired source bundle:
    - `output/tools/get_src_extended_review_bundle/get_src_extended_review_bundle__20260425T191004Z.zip`

Question:

- the restart32 best-init contract still appears to pass semantically across
  the fixed `1111` family
- the kept-`7004` timing postmortem still says the overrun does not read like a
  gate-logic failure
- but the first external-review pass found a provenance/reporting mismatch in
  the decisive remaining-family microbatch bundle
- the remaining question is how to reconcile that bundle into an
  evidence-clean handoff

Needed evidence:

- one shared role-contract fix
- one focused regression test proving `filtered_family` is evaluated as a
  filtered lane
- one rerun or explicitly reconciled family bundle whose:
  - rows
  - state
  - final event
  - summary
  - recommendation
  - readout
  all agree

Success condition:

- the checkpoint subtopic should be shareable without asking the reviewer to
  decide which conflicting artefact layer is authoritative

Result:

- success condition met
- final audit reports:
  - recommendation `advance`
  - row mismatch count `0`
  - all five recommendation layers present and set to `advance`

### 2. What is the narrowest honest live canary if this branch reopens after reconciliation and review?

Status:

- active planning
- plan:
  - `planning/projects/no_wli/20_active_plans/no_wli_stage2_topk_selected_family_low_edge_phasea_checkpoint_live_canary_plan_2026-04-25.md`
- current answer:
  - prepare one filtered collapse-lane live canary only after harness/preflight
    checks pass
  - preferred first canary cell:
    - fixed `1111/search7002`
  - max runtime:
    - `08:00:00`
  - no matrix, no threshold tuning, no automatic second canary

Question:

- review-readiness does not automatically justify live runtime
- if experimentation resumes later, it should do so through one explicit live
  canary rather than by drifting back into replay families
- the open question is which single live cell, budget, and stop rule would be
  honest for that reopening

Needed evidence:

- one written live-canary definition
- one budget sized from the carried checkpoint-action evidence
- one stop rule that preserves the same discipline this subtopic established

Success condition:

- no live runtime should reopen by implication
- the next runtime should exist only if it is narrow enough to defend before
  launch

Current guard:

- live runtime remains blocked until the plan's Day 2 harness/preflight checks
  prove that one canary can emit and audit the required checkpoint fields and
  artefact layers

### 3. Once provenance is fixed, should this selector checkpoint line stop there and hand off to review?

Status:

- closed 2026-04-25
- answer:
  - yes; do review handoff now and move any new science into a separate
    branch/run note

Question:

- the branch now has a carried contract, a likely full-family semantic pass,
  and a bounded explanation for the only timing caveat
- so the real question may now be whether more study inside this exact subtopic
  would be lower value than fixing provenance and asking for external review

Needed evidence:

- one reconciled evidence surface
- one clear synthesis with an explicit non-claim that live runtime is still
  blocked

Success condition:

- if the answer is yes, the next work after reconciliation should be packaging
  rather than another replay-family investigation

Result:

- success condition met
- live runtime remains blocked
- production/general policy is not claimed

## P1 - runtime and integrity questions

### 5. What counts as the first timing anchor for a materially new runtime family?

Question:

- the closed `v78` probe was incomplete and therefore did not earn timing
  authority
- what exact rule should keep incomplete runs from becoming budget anchors by
  accident?

Current rule:

- only a completed run in the materially new family earns anchor status
- incomplete probes may still teach stop discipline, but they do not set the
  new runtime budget

### 6. How should partial extractors be standardized so every future long run emits stop-decision fields before completion?

Question:

- the current branch benefited from rescued partial checkpoints
- what minimum fields should always be extractable mid-run so that stop
  decisions are evidence-based?

Minimum likely fields:

- coverage count
- best-so-far outcome
- retained-anchor comparison
- missing-work list
- stop-signal flags

Success condition:

- partial long-run evidence becomes a routine first-class output rather than an
  ad hoc rescue

## P2 - frozen background hold questions

### 7. Stop / family-quality / triage follow-on

- These lines remain useful background evidence.
- They are not the active stream.
- Re-open them only if the fixed-instance solver-development branch forces a
  return.

### 8. Candidate3 and richer-pool downstream replacement follow-on

- Candidate3 is closed without promotion.
- The richer-pool downstream replacement reopen is also closed.
- Re-open downstream ordering only if a new conditioned rule or a materially
  different saved-surface mechanism appears.

## Planning / log hygiene

- Full logs stay append-only.
- The top-level `00-04` files must stay short and current.
- Every overnight runtime step must keep explicit:
  - Question
  - Suspicion
  - Main alternative
  - If suspicion is true, expect
  - If alternative is true, expect
  - Tomorrow's decision rule
- Also write one explicit mechanism-layer claim:
  - supply
  - selection
  - ordering
  - allocation
  - or local search / rescue

## P0 - active Stage 3.5 local-rescue question

### 9. Is rank-6/local-rescue a real mechanism or a shallow one-round artifact?

Question:

- the broad shallow frontier harvest found large accepted positives,
  especially in rank-6 rows, but the unfiltered policy also accepted
  regressions
- the next question is whether the strongest shallow-positive rows deepen or
  merely reproduce the shallow one-round result

Current run:

- `stage35_guard_selector_frontier_deepening_harvest_v1`
- source:
  - strongest shallow-positive cells from
    `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T152907Z__stage35_guard_selector_frontier_runtime_harvest_v1/`

Success condition:

- multiple cells improve beyond the shallow result without creating a new
  regression pattern

Hold condition:

- deepening mostly reproduces shallow results or admits new regressions

Recommended next if successful:

- design a narrower rank/slice-aware policy; do not promote the broad
  guard-selector as-is

Result:

- completed deepening harvest:
  - `15 / 15` cells
  - `12 / 15` better than shallow
  - `3 / 15` worse than shallow
  - mean delta versus shallow `+0.007533`
  - mean delta versus retained anchor `+0.004533`
- answer:
  - the mechanism is real but modest
  - rank-6/local-rescue deserves offline characterization, not immediate broad
    runtime widening

Next open question:

- which observable row/slice features separate the rank-6 cells that deepen
  safely from those that regress versus shallow?

Current evidence:

- join/dedup output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T003224Z__stage35_guard_selector_frontier_deepening_join_v1/`
- deduplicated result:
  - `11 / 14` better than shallow
  - `3 / 14` worse than shallow
- rank `6`:
  - `10 / 12` better
  - `2 / 12` worse
- best posthoc non-seed candidate gate:
  - `rank6_selected_start_ge_0p437`
  - `6 / 6` better
  - `0 / 6` worse

Current answer:

- selected-row start strength is the best observed separator, but it is posthoc
  and too small to promote directly

Next open question:

- can the `rank6_selected_start_ge_0p437` hypothesis be converted into a
  predeclared no-regression rule with enough offline support to justify a small
  policy canary?

Answer:

- not as-is
- the gate removed all observed rank-6 deepening regressions but rejected
  `4` real deepening positives
- exact threshold `0.437` remains posthoc and too lossy

Next open question:

- can a softened selected-start gate or a second non-seed feature preserve the
  safety benefit while recovering the rejected positive rows?

Current candidate answer:

- candidate:
  - rank `6`
  - `selected_start_match_ratio >= 0.437`
  - or `shallow_resume_minus_selected >= 0.400`
- observed dedup result:
  - kept `7`
  - kept better/worse `7 / 0`
  - rejected better/worse `3 / 2`
- status:
  - promising enough for a canary design note
  - not enough to launch runtime directly

Next open question:

- which exact tiny canary cells should test hard-gate keep, shallow-delta keep,
  observed-regression reject, and rejected-positive audit/control behavior?

Answer:

- hard-gate keep:
  - `1511/search7004 rank 6 51b7dab086e94186`
- shallow-delta keep:
  - `1111/search7002 rank 6 74dfe3cb559629f7`
- observed-regression reject:
  - `1111/search7004 rank 6 511a29668b8c44d1`
- rejected-positive audit/control:
  - `1411/search7005 rank 6 b47e22bc63e7c189`

Next open question:

- should the hardcoded four-cell canary runner be implemented and launched
  under the written `45m` / `2700s` budget?

Answer:

- yes; it was implemented and launched
- result:
  - completed `4 / 4`
  - executed rescue cells `2`
  - policy skips `2`
  - errors `0`
  - policy mismatches `0`
  - executed cells nonnegative versus shallow `2 / 2`

Next open question:

- does the same softened policy retain acceptable recall/opportunity cost on a
  small same-rule recall/audit microbatch, especially around rejected-positive
  boundary rows?

Answer:

- no, not cleanly enough to continue runtime
- recall/audit result:
  - `5 / 5` completed
  - `3` rejected positives versus shallow
  - `2` rejected regressions versus shallow
  - `5 / 5` reproduced prior deepening exactly
- interpretation:
  - policy is safe on the observed boundary but too conservative for recall

Next open question:

- what boundary features separate the three rejected positives from the two
  rejected regressions without simply widening the rule?

Answer:

- no simple numeric boundary feature found
- boundary-feature audit:
  - `27` numeric features
  - `172` threshold sketches
  - `0` perfect one-feature separators
- best zero-false-positive sketches recover only `2 / 3` positives

Next open question:

- can route-composition or family/lineage features separate this boundary, or
  should the rank-6 policy line close as mechanism insight rather than a policy
  candidate?

Answer:

- yes on the five-row boundary set, but only as a posthoc hypothesis
- route-lineage audit result:
  - `0` perfect single-feature separators
  - `141` perfect two-feature separators
- most interpretable separator family:
  - candidate source rank `1`
  - and high route novelty, for example
    `candidate_novelty_distance_to_anchor >= 173.5`
- current decision:
  - wait for external review
  - do not promote
  - do not launch more runtime yet

Next open question:

- is the source-rank-plus-route-novelty separator mechanistically coherent and
  stable enough to justify a tiny held-out/disagreement confirmation design?

Answer:

- external review says the mechanism is credible enough to continue, but not
  runtime-ready
- the requested strict offline confirmation-prep scan is complete:
  - valid rows:
    - `21`
  - invalid rows:
    - `1`
  - rule disagreements:
    - `9`
  - group A old reject / route keep:
    - `4`
  - group B old keep / route reject:
    - `5`
- missing lineage is now invalid, not reject
- the route-lineage action rule uses only:
  - `candidate_source`
  - `candidate_source_rank`
  - `candidate_novelty_distance_to_anchor`

Next open question:

- after inspecting groups A and B against existing shallow/deep evidence, which
  exact rows, if any, should form a fixed-rule tiny confirmation design?

Answer:

- route-lineage should not be tested as a replacement rule because group B
  includes old-keep / route-reject rows with existing positive evidence
- the coherent tiny design was therefore additive:
  - keep the old softened rule
  - additionally run group-A old-reject / route-keep cells
- additive confirmation output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T153119Z__stage35_rank6_route_lineage_additive_confirmation_v1/`
- result:
  - `4 / 4` cells completed
  - `0` errors
  - `3 / 4` nonnegative versus shallow
  - `1 / 4` regressed versus shallow
- key safety failure:
  - `1111/search7001 rank 6 d94845511e181f7c`
  - shallow `0.038`
  - confirmation `0.037`
  - delta `-0.001`

Next open question:

- after closing the route-lineage additive rule as policy-negative, what
  different mechanism branch should receive the next bounded data-taking slot?

Answer:

- reopen constant-local-depth only through saved handoff artefacts, not through
  the failed full-pipeline six-job panel
- offline activation passed:
  - output:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T022336Z__stage3_entry_const_local_depth_handoff_activation_v1/`
  - `3 / 3` target handoffs structurally active
  - `3 / 3` mechanism-widened
  - legacy init3 `64`
  - candidate init3 `288`
  - candidate new init3 keys `80`
  - candidate missing legacy keys `0`
- first runtime cell:
  - `1111/search7005`
  - one saved-handoff Stage-3 resume
  - `16h` watchdog cap

Next open question:

- does the one-cell `1111/search7005` constant-local-depth handoff resume
  improve beyond retained `0.372`, and does the output explain the mechanism
  well enough to justify a second handoff cell?

Answer:

- `7005` completed small-positive:
  - output:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T022917Z__stage3_entry_const_local_depth_handoff_7005_v1/`
  - retained:
    - `0.372`
  - candidate:
    - `0.374`
  - delta:
    - `+0.002`
  - elapsed:
    - `7139.745s`
- this justified exactly one second non-heavy cell, `1111/search7004`
- `7004` completed negative:
  - output:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T064716Z__stage3_entry_const_local_depth_handoff_7004_v1/`
  - retained:
    - `0.423`
  - candidate:
    - `0.406`
  - delta:
    - `-0.017`
  - elapsed:
    - `7755.439s`
- closeout:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage3_entry_const_local_depth_handoff_closeout_2026-05-01.md`

Decision:

- close this exact constant-local-depth handoff-resume shape as a policy
  candidate
- do not launch `1111/search7002` for this exact branch

Next open question:

- on `7004`, why did the widened-entry run find a `0.422` Phase-A candidate
  but finish at `0.406`, and can an offline downstream-selection audit produce
  a predeclared safety rule that would preserve the `7005` small positive while
  rejecting the `7004` regression?

Answer:

- downstream-selection audit output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T155731Z__stage3_entry_const_local_depth_downstream_selection_audit_v1/`
- extractor:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage3_entry_const_local_depth_downstream_selection_audit_v1.py`
- result:
  - cells: `2`
  - candidate positives: `1`
  - candidate negatives: `1`
  - `7005` Stage 3.5 accept passed and kept the `+0.002` result
  - `7004` Stage 3.5 accept failed with `search_score_drop_guard_failed`
  - posthoc gate "use widened-entry result only when Stage 3.5 accept passes;
    otherwise fall back to retained" kept `7005`, rejected `7004`, and had `0`
    gated negatives on these two cells

Decision:

- this is an offline lead only, not enough for runtime
- do not reopen constant-local-depth runtime from this two-cell audit

Next open question:

- does the Stage 3.5 accept-pass fallback gate remain nonnegative when applied
  offline to a broader set of retained handoff/frontier outputs, or is it just
  a two-cell coincidence?

Answer:

- broader offline audit output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T160206Z__stage35_accept_gate_broader_offline_audit_v1/`
- extractor:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage35_accept_gate_broader_offline_audit_v1.py`
- coverage:
  - `136` shallow frontier-harvest rows
  - `15` deepening rows
  - `151` total rows
- result:
  - Stage 3.5 accepted rows:
    - `147`
  - accept-gate negatives versus retained:
    - `75`
  - accept-gate negatives versus selected start:
    - `18`

Decision:

- close Stage 3.5 accept-pass as a general safety gate
- the two-cell `7005/7004` posthoc rule was a coincidence/local diagnostic,
  not a runtime-ready policy

Next open question:

- after closing constant-local-depth and the simple Stage 3.5 accept gate, is
  there any remaining offline feature design worth extracting from the `7004`
  regression, or should the next mechanism branch move away from entry
  allocation and simple Stage 3.5 acceptance entirely?

Current action:

- move to a bounded frontier-space robustness harvest in the local-search /
  rescue layer
- plan:
  - `planning/projects/no_wli/20_active_plans/no_wli_stage35_frontier_space_robustness_harvest_plan_2026-05-01.md`
- runner:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_frontier_space_robustness_harvest_v1.py`
- status:
  - launching under an `8h` wallclock budget
- question:
  - across held-out Stage 3.5 frontier strata, does deeper bounded local rescue
    stabilize useful gains or mostly amplify the shallow mixed signal?
- prediction:
  - rank-6 held-out positives mostly remain useful
  - shallow negatives and rank `1-5` neutral/positive rows remain mixed enough
    to block a simple policy
- decision rule:
  - promote no policy directly from this harvest
  - continue only if a predeclared stratum is strongly nonnegative and
    materially useful

Answer:

- completed output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T161846Z__stage35_frontier_space_robustness_harvest_v1/`
- closeout:
  - `planning/projects/no_wli/40_review_summaries/no_wli_stage35_frontier_space_robustness_harvest_closeout_2026-05-01.md`
- result:
  - `48 / 48` cells completed
  - `0` errors
  - elapsed `12602.918s`
  - selected rows `32 / 48`
  - selected rows better/worse than shallow:
    - `27 / 3`
  - selected rows nonnegative/negative versus selected start:
    - `28 / 4`
- interpretation:
  - deeper bounded rescue is real and broader than rank 6 alone
  - the accepted rank `1-5` moderate-positive slice is a new offline lead
  - shallow-negative and shallow-neutral strata remain mixed
  - no policy promotion is justified directly from this harvest

Next open question:

- can an offline acceptance-boundary extractor separate accepted positives and
  high-local-best guard failures from the accepted regressions using only
  action-safe features?

Answer:

- extractor:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage35_frontier_space_acceptance_boundary_audit_v1.py`
- output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T235632Z__stage35_frontier_space_acceptance_boundary_audit_v1/`
- result:
  - accepted positives:
    - `28`
  - accepted regressions:
    - `4`
  - guard failures:
    - `16`
  - single-rule scans:
    - `1087`
  - two-feature scans:
    - `20292`
  - perfect single-rule separators:
    - `0`
  - perfect two-feature separators:
    - `0`
- interpretation:
  - no action-safe separator is clean enough to justify more local-rescue
    runtime
  - best no-regression sketches are posthoc and either too lossy or tied to the
    same acceptance surface

Decision:

- close broad local-rescue policy widening for now
- keep the completed harvest as mechanism evidence
- move the next work up a level, unless a genuinely held-out validation design
  is written first

Prediction tracking:

- prediction ledger is stored in:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260430T014439Z__stage35_rank6_selected_start_gate_safety_v1/stage35_rank6_selected_start_gate_prediction_ledger.json`
- when this analysis branch closes, compare the final outcome against the
  ledger in chat

