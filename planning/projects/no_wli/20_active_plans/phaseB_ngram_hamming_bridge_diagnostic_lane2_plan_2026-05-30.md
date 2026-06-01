# PhaseB N-Gram Hamming Bridge Diagnostic Lane 2 Plan - 2026-05-30

Status: preparation_only
Work status: await_full_raw_order2_order3_provenance_before_broad_run
Project: no_wli
Owner: agent

## 2026-05-31 Preparation Status

Lane 2 synthetic-only preparation has started.

Implemented support:

- `src/rune_decrypter_prime/scoring/ngram_hamming/bridge.py`
- `tests/scoring/ngram_hamming/test_bridge_profiles_and_clusters.py`

Prepared surfaces:

- canonical and bridge profile specs with explicit authority fields;
- profile manifest rows and manifest hash;
- overlap/touch phrase cluster grouping;
- separate score-candidate cluster scope via allowed profile filtering;
- exact-hit presence/count as cluster fields, not synthetic profiles;
- cluster row, candidate summary row, pair ledger, and zero-hit audit schema
  validators;
- score-candidate profile-id filtering helper;
- Lane 2 contract-pack builder;
- Lane 2 readiness checker;
- Lane 2 synthetic contract smoke;
- Lane 2 prep status index;
- Lane 2 gated diagnostic scaffold;
- Lane 2 input contract;
- Lane 2 prep bundle;
- full raw provenance review-pack scaffold;
- Lane 2 launch decision record;
- Lane 2 external review pack.

Verification:

```text
python -m py_compile src\rune_decrypter_prime\scoring\ngram_hamming\bridge.py
python -m pytest tests/scoring/ngram_hamming/test_bridge_profiles_and_clusters.py tests/scoring/ngram_hamming/test_reference_ngram_hamming.py -q
```

Result:

```text
latest focused Lane 2 set: 41 passed in 0.99s
```

This implementation is still preparation only. It does not launch a broad bridge
scan and does not change production scoring.

Live full-raw shard-build watch, manual check on 2026-05-31:

```text
running_python_pid = 7348
extractable_shard_manifests = 600 / 1118
passing_shard_manifests = 600 / 1118
last_completed_log_line = shard_done=600/1118 order=3 shard=400
last_started_log_line = shard_start=601/1118 order=3 shard=401
latest_log_eta_by_completed_bytes = 15h17m47s
log_path = output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_asset_shards_v1/full_raw_asset_shards_optimized_resume_20260530_164433.log
```

Crash/restart check on 2026-05-31:

```text
previous_python_worker = not_running
restart_launcher_pid = 15232
resumed_python_pid = 12928
completed_shards_at_restart_manifest = 641 / 1118
resume_log_line = resume_completed_shards=641/1118
restart_log_line = shard_start=642/1118 order=3 shard=442
run_root = output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_asset_shards_v1/20260530T120414Z__phaseB_ngram_hamming_full_raw_asset_shards_v1
live_watch_log = planning/projects/no_wli/50_console_and_watch_logs/phaseB_ngram_hamming_full_raw_asset_shards_resume_2026-05-31.log
```

The resumed run completed successfully. The final watch log reports
`status=pass completed_shards=1118/1118`, and the refreshed provenance summary
now reflects the full raw extraction.

Partial provenance helper prepared and run:

```text
script = tools/benchmarks/periodic_sub_trans/no_wli/analysis/summarise_phaseB_ngram_hamming_full_raw_asset_shards_v1.py
output = output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_asset_shard_provenance_v1
status = pass
completed_shards = 1118 / 1118
missing_shards = 0
failed_shards = 0
missing_output_files = 0
missing_required_output_combos = 0
phrase_length_distribution_rows = 98
word_length_distribution_rows = 140
length_partition_source_output_files = 2236
length_partition_parsed_output_files = 1728
length_partition_unparsed_output_files = 508
length_partition_source_aggregate_rows = 1115443486
length_partition_parsed_aggregate_rows = 1115443486
length_partition_unparsed_aggregate_rows = 0
source_bytes_completed_fraction = 1.000000
full_raw_ngram_rebuild_confirmed = true
```

The shard provenance output is now a full raw provenance pass for the completed
order-2/order-3 FWD normal/strict shard build.

Lane 2 contract pack prepared and run:

```text
script = tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_bridge_lane2_contract_pack_v1.py
output = output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_contract_pack_v1
status = pass
profile_manifest_hash = bc48b348d6afa6f0402514f6055cbe4ec33fb328e1b658144c67d4f812b85e28
canonical_profile_count = 7
bridge_profile_count = 5
total_profile_count = 12
no_broad_scan_launched = true
no_production_scorer_changes = true
gate_status = await_full_raw_order2_order3_provenance_before_broad_run
```

The contract pack freezes schema/profile surfaces only. It is not a review
approval and does not authorize broad bridge execution.

Lane 2 readiness checker prepared and run:

```text
script = tools/benchmarks/periodic_sub_trans/no_wli/analysis/check_phaseB_ngram_hamming_bridge_lane2_readiness_v1.py
output = output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_readiness_v1
status = pass
bridge_broad_scan_ready = true
completed_shards = 1118 / 1118
blocked_reasons = none
```

This readiness result means the data-plane provenance gate is now clear. It is
not itself launch approval for real bridge diagnostics; the hardcoded launch
approval switch remains false pending review.

Full raw provenance review-pack scaffold prepared and run:

```text
script = tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_full_raw_provenance_review_pack_v1.py
output = output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_provenance_review_pack_v1
status = review_ready
completed_shards = 1118 / 1118
missing_shards = 0
failed_shards = 0
run_logs_copied = 2
manifest_hashes_present = true
normal_strict_row_counts_present = true
phrase_length_distribution_rows = 98
word_length_distribution_rows = 140
pending_review_checks = none
no_broad_scan_launched = true
no_production_scorer_changes = true
```

This pack is ready for Lane 1 provenance review. It still does not approve or
start the real bridge diagnostic.

Permanent Lane 1 asset contract prepared and validated:

```text
asset_home = assets/ngram_hamming/phaseB_full_raw_v1
asset_manifest = assets/ngram_hamming/phaseB_full_raw_v1/asset_manifest.json
asset_status = review_ready_candidate
payload_storage_mode = manifest_index_external_payload_due_large_size
listed_payload_files = 2236
provenance_files = 7
asset_validation_status = pass
hash_failures = 0
missing_files = 0
```

The retained shard payload is about 71GB compressed, so the permanent asset home
records repo-relative payload paths and SHA256 hashes instead of copying all
payload files into git-tracked assets.

Lane 2 launch decision record prepared and run:

```text
script = tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_bridge_lane2_launch_decision_record_v1.py
output = output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_launch_decision_record_v1
status = blocked
bridge_broad_scan_ready = true
provenance_review_pack_status = review_ready
allow_real_bridge_scan_after_review = false
intended_first_launch_scope = post-review microbatch only
stop_condition = readiness_pass_and_explicit_hardcoded_approval_or_block
no_broad_scan_launched = true
no_production_scorer_changes = true
```

This record is a launch guard and discussion aid. It does not approve or start
the broad bridge diagnostic.

Final Lane 1 closure review pack prepared:

```text
script = tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_lane1_closure_review_pack_v1.py
zip = planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_lane1_full_raw_language_asset_closure_review_pack_2026-06-01.zip
status = packed_review_ready
entry_count = 42
backslash_entries = 0
missing_files = 0
no_production_state = true
no_real_scan_state = true
50_asset_index = asset manifest, README, and mirrored permanent asset provenance files
```

Lane 1 closure does not approve Lane 2 launch, does not approve production
scorer changes, does not reject order 4, and does not delete future order 5
diagnostic scope. Counts and log-counts remain diagnostic only.

Lane 2 external review pack prepared:

```text
script = tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_bridge_lane2_external_review_pack_v1.py
folder = planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_lane1_lane2_full_review_pack_2026-05-31
zip = planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_lane1_lane2_full_review_pack_2026-05-31.zip
status = packed_with_blocks
completed_shards = 1118 / 1118
bridge_broad_scan_ready = true
review_position = pre-launch blocked preparation review; do not approve real bridge scans from this pack
```

This is the natural review break for Lane 2 preparation so far. It packages the
research/canon planning docs, no-WLI planning state, Lane 1 provenance
summaries, Lane 2 component outputs, source, tests, review summary, and reviewer
questions.

First-pass external review hygiene fix:

```text
issue = external review pack was not self-contained for source replay
missing_before = src/rune_decrypter_prime/scoring/ngram_hamming/reference.py
missing_before = src/rune_decrypter_prime/scoring/ngram_hamming/fast_backend.py
fix = added both files to SOURCE_FILES_REL in the external review pack builder
test = test_external_review_pack_includes_ngram_hamming_dependency_closure
test = test_external_review_pack_zip_contains_ngram_hamming_dependency_closure
full_review_zip_entries = 84
verification = 41 passed in 0.99s
supersedes = planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_bridge_lane2_prep_external_review_pack_2026-05-31.zip
supersedes = planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_bridge_lane2_prep_external_review_pack_dependency_closure_2026-05-31.zip
```

Lane 2 synthetic contract smoke prepared and run:

```text
script = tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_ngram_hamming_bridge_lane2_synthetic_contract_smoke_v1.py
output = output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_synthetic_contract_smoke_v1
status = pass
no_real_candidate_scan = true
no_production_scorer_changes = true
raw_hit_count = 3
all_cluster_count = 2
score_cluster_count = 2
all_candidate_summary_row_count = 3
score_candidate_summary_row_count = 2
pair_ledger_row_count = 1
zero_hit_audit_row_count = 1
```

This smoke exists only to exercise output schemas end to end with artificial
hits. It is not bridge evidence and carries no candidate interpretation.

Lane 2 prep status index prepared and run:

```text
script = tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_bridge_lane2_prep_status_index_v1.py
output = output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_prep_status_index_v1
status = blocked
bridge_broad_scan_ready = true
contract_pack = pass
synthetic_contract_smoke = pass
shard_provenance = pass
full_raw_provenance_review_pack = review_ready
launch_decision_record = blocked
external_review_pack = packed_with_blocks
readiness_gate = pass
completed_shards = 1118 / 1118
```

This index is the quick handoff surface for Lane 2 preparation status. Its
blocked state is expected because Lane 2 real-scan approval remains false even
after Lane 1 closure.

Lane 2 gated diagnostic scaffold prepared and run:

```text
script = tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_ngram_hamming_bridge_lane2_gated_diagnostic_v1.py
output = output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_gated_diagnostic_v1
status = blocked
real_candidate_scan_started = false
allow_real_bridge_scan = false
blocked_reasons =
  - ALLOW_REAL_BRIDGE_SCAN is false
```

This scaffold is intentionally double-gated: even after shard provenance passes,
it still cannot start a real bridge scan until the hardcoded approval switch is
changed in source after a separate launch decision.

Lane 2 prep bundle prepared and run:

```text
script = tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_bridge_lane2_prep_bundle_v1.py
output = output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_prep_bundle_v1
status = pass
copied_files = 31 / 31
bridge_broad_scan_ready = true
no_broad_scan_launched = true
no_production_scorer_changes = true
```

This bundle is a preparation handoff only, not a review approval pack.

Lane 2 input contract prepared and run:

```text
script = tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_bridge_lane2_input_contract_v1.py
output = output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_input_contract_v1
status = pass
no_real_candidate_scan = true
no_production_scorer_changes = true
candidate_chunk_required_fields = 10
pair_input_required_fields = 6
run_config_required_fields = 9
```

This contract fixes the future runner input schemas for candidate chunks, pair
inputs, and run config before any real bridge diagnostic code is launched.

## Canonical Reference

Original v3.2 canon/bridge document:

- `planning/temp_files/ngram_scorer_june_2026_docs/rdp_ngram_phrase_coherence_v3_2_canon_review.md`

This file is the direct drift-check reference for Lane 2. If this plan, any
runner, any manifest, any readout, or any review pack disagrees with the v3.2
canon/bridge document, the v3.2 document wins unless a later explicitly named
canon update supersedes it.

## Purpose

Prepare the order-2/order-3 bridge diagnostic implementation while the full raw
order-2/order-3 shard build continues.

This Lane 2 plan is not a launch approval.

Lane 2 is allowed to prepare:

- profile authority schema
- bridge profile manifest
- cluster output schema
- candidate summary schema
- pair ledger schema
- panel-rescue zero-hit audit schema
- synthetic tests for cluster/profile-authority behavior
- provenance review checklist

Lane 2 is not allowed to launch broad real-candidate bridge scans until the full
raw order-2/order-3 provenance review passes.

## Current Data-Plane Gate

Current active data-plane work:

```text
scope = full raw FWD order-2/order-3 normal/strict shard build
asset_mode = full
sample_line_limit_per_order = None
full long matrix = not launched
```

Broad bridge interpretation remains blocked until:

1. the shard build completes or fails with a clear extractable state;
2. completed shard coverage is summarized;
3. a full raw order-2/order-3 provenance review pack is produced;
4. the provenance review passes.

## Destination Versus Stage

Destination:

```text
research-led phrase coherence scorer
```

Canonical destination families:

```text
diagnostic:
  B2R
  N3S_diag
  F5D

score-candidate:
  N3C
  S3W
  N4L
  S34C_main
```

Current stage:

```text
temporary order-2/order-3 bridge diagnostics
```

The bridge does not replace the destination. It exists because the current full
raw data tranche contains order 2 and order 3 only.

## Non-Negotiable Drift Guards

Every profile row must declare:

```text
profile_id
profile_origin
canonical_profile_id
parameter_status
score_authority
orders
cuts
min_phrase_token_length
max_total_phrase_hd
max_word_hd
role
scope_reason
equivalent_research_profile
promotion_status
```

Where applicable, include:

```text
broader_than_profile
narrower_than_profile
threshold_diff_summary
```

No profile may silently change:

```text
order
cut
min phrase token length
max total HD
max word HD
score-bearing role
diagnostic role
```

Any change creates a new profile or a labelled non-canonical variant.

## Bridge Profile Draft

The bridge profiles are diagnostic/probe views only unless explicitly stated
otherwise in a later review.

| profile_id | origin | canonical link | orders | cuts | min len | max total HD | max word HD | authority |
|---|---|---|---:|---|---:|---:|---:|---|
| `BR_O2_soft` | `bridge_derived` | `B2R` | 2 | normal, strict separate | 7 | 2 | 2 | diagnostic only |
| `BR_O2_len8_conservative` | `bridge_derived` | none | 2 | normal, strict separate | 8 | 2 | 1 | blocked bridge candidate |
| `BR_O2_len10_long` | `bridge_derived` | none | 2 | normal, strict separate | 10 | 2 | 1 | diagnostic only |
| `BR_O3_soft` | `bridge_derived` | `N3S_diag` for normal only | 3 | normal, strict separate | 7 | 2 | 2 | diagnostic only |
| `BR_O3_conservative` | `bridge_derived` | `N3C` for normal only | 3 | normal, strict separate | 8 | 2 | 1 | blocked bridge candidate |

Important profile notes:

- `BR_O3_conservative` strict is not `S3W`.
- `S3W` is strict order-3, min length `7`, total HD `2`, max word HD `2`.
- `BR_O3_conservative` strict is strict order-3, min length `8`, total HD `2`,
  max word HD `1`.
- `S34C_main` is not part of the order-2/order-3 bridge unless a later run
  explicitly includes canonical strict order-3/order-4 confirmation. The main
  canonical `S34C_main` min length remains `10`.

## Cluster Scope Draft

The bridge implementation should emit two cluster scopes:

```text
all_profile_overlap_touch_cluster
score_candidate_overlap_touch_cluster
```

`all_profile_overlap_touch_cluster`:

- includes diagnostic and bridge-candidate profiles;
- supports inflation/concentration analysis;
- must not be used as a score-candidate support unit unless explicitly promoted.

`score_candidate_overlap_touch_cluster`:

- includes only profiles whose `score_authority` permits score-candidate
  simulation;
- excludes diagnostic-only profiles from shaping score-candidate clusters.

Default interval rule:

```text
interval = [hit_start, hit_end)
same cluster if next.start <= current_cluster_end
new cluster if next.start > current_cluster_end
```

## Required Output Schemas

### Profile Manifest

Minimum fields:

```text
profile_id
profile_origin
canonical_profile_id
parameter_status
score_authority
direction
orders
cuts
min_phrase_token_length
max_total_phrase_hd
max_word_hd
normalised_hd_ceiling
role
scope_reason
equivalent_research_profile
promotion_status
threshold_diff_summary
```

### Cluster Rows

Minimum fields:

```text
run_id
cluster_scope
candidate_id
chunk_id
cluster_id
start_offset
end_offset
profiles_present
cuts_present
orders_present
raw_hit_count
unique_phrase_id_count
unique_start_count
exact_hit_present
exact_hit_count
best_hit_signature
```

### Candidate Summary Rows

Minimum fields:

```text
candidate_id
profile_id
profile_origin
canonical_profile_id
parameter_status
score_authority
direction
cut
order
raw_hit_count
cluster_count
exact_hit_count
exact_cluster_count
unique_phrase_id_count
unique_start_count
hit_to_cluster_ratio
top_phrase_share
best_hit_signature
```

### Pair Ledger Rows

Minimum fields:

```text
pair_id
expected_better_id
expected_worse_id
baseline_winner
phrase_tuple_winner
order2_tuple_better
order2_tuple_worse
order3_tuple_better
order3_tuple_worse
normal_support_delta
strict_support_delta
first_diff_component
outcome_label
panel_rescue_flag
concentration_flags
null_lift_summary
unsafe_interpretation_flags
```

### Panel-Rescue Zero-Hit Audit Rows

Minimum fields:

```text
pair_id
candidate_id
role
chunk_id
panel_rescue_flag
span_hamming_best_support
ngram_hit_count_by_order
phrase_opportunity_count_by_order
best_failed_or_near_phrase_note
likely_no_hit_reason
```

## Synthetic Test Targets

Prepare tests before broad bridge execution:

```text
test_profile_manifest_requires_authority_fields
test_bridge_profile_does_not_equal_s3w_when_thresholds_differ
test_s34c_main_min_length_is_10
test_s34c_len8_requires_diagnostic_variant_id
test_overlap_clusters_merge
test_touching_clusters_merge
test_one_token_gap_starts_new_cluster
test_diagnostic_profiles_do_not_shape_score_candidate_clusters
test_raw_hit_count_can_exceed_cluster_count
test_exact_hits_are_fields_not_profiles
test_normal_and_strict_remain_separate
test_profile_manifest_hash_changes_when_thresholds_change
```

Synthetic tests should use tiny fixtures and must not depend on the live full raw
asset build.

## Provenance Review Checklist

Before any broad bridge scan:

```text
shard_count_total
shard_count_pass
shard_count_failed
missing_shard_list
source_bytes_covered
order_cut_direction_counts
normal_strict_row_counts
phrase_length_distributions
word_length_distributions
duplicate_collapse_metadata
count_log_count_availability
manifest hashes
run logs
resume/interruption history
known limitations
```

## Allowed While Full Raw Build Runs

Allowed:

- edit this plan;
- prepare schemas;
- prepare synthetic tests;
- inspect current implementation interfaces;
- prepare review-pack builders;
- check live build progress and extractable shard counts.

Not allowed:

- broad bridge scan launch;
- full hard-pair report;
- order-4/order-5 expansion;
- production scoring changes;
- direct additive use of P2/current score;
- controlled damage-ladder claims from candidate-comparability outputs.

## Next Review Pack

The next review pack that should close this discussion phase is:

```text
full raw order-2/order-3 provenance summary review pack
```

The bridge diagnostic pack comes after that review passes.

## Lane 2 gated diagnostic scoring evidence

Lane 1 is closed for the order-2/order-3 FWD normal/strict language asset tranche.

Lane 2 may now run a small post-review diagnostic microbatch.

This is not production scoring.

This is not a production ranking change.

This is not a broad candidate search.

This is an evidence run over controlled positives, deterministic damage tiers, and matched nulls.

The goal is to decide whether the n-gram Hamming phrase-coherence evidence is strong enough to proceed to report-only scorer integration.

Order 4 remains part of the canonical scorer plan but is outside the current Lane 1 asset tranche.

Order 5 remains optional diagnostic future scope.

S34C_main cannot be fully tested until order 4 is available.

Counts/log-counts remain diagnostic only.

Raw hit counts remain diagnostic only.

Order-2 support remains diagnostic unless it clears a later higher proof burden.

Implemented diagnostic evidence microbatch:

- phase:
  - `phaseB_ngram_hamming_lane2_gated_diagnostic_evidence_v1`
- runner:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_ngram_hamming_lane2_gated_diagnostic_evidence_v1.py`
- output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_lane2_gated_diagnostic_evidence_v1/`
- review pack builder:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_ngram_hamming_lane2_gated_diagnostic_evidence_review_pack_v1.py`
- next review pack:
  - `planning/projects/no_wli/40_review_summaries/phaseB_ngram_hamming_lane2_gated_diagnostic_evidence_review_pack_2026-06-01.zip`

The diagnostic evidence run scans a generated controlled evaluation corpus only.
It records `real_candidate_scan_started=false`,
`broad_candidate_scan_started=false`, and `production_scorer_change=false`.
