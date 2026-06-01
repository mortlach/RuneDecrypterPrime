# PhaseB N-Gram Hamming Exact No-Cap Pilot Runtime Block Review Summary - 2026-05-29

Status: review-required
Pack subject: first guarded launch of `phaseB_ngram_hamming_exact_no_cap_pilot_v1`

## Decision Needed

The approved tiny comparability pilot was implemented and launched with the approved provenance amendments, but it stopped after the first scan because the projected full 120-scan run exceeded the hardcoded interactive budget.

This is a runtime sizing block, not a provenance or backend block.

## Run Result

```text
status = blocked
backend_impl = cpp_fast
python_fallback_allowed = false
claim_mode = hard_pair_candidate_comparability
broad_pilot = false
full_hard_pair_report = false
production_scorer_changes = false
completed_scans = 1 / 120
elapsed_seconds = 1.724
projected_seconds_after_first_scan = 206.918
budget_seconds = 120.0
blocked_reason = first scan projected 206.9s beyond 120.0s budget
```

## Provenance Result

```text
hard_pair_candidate_stream_verified = true
controlled_damage_stream_verified = false
controlled_damage_stream_required = false
candidate_full_texts_used_as_primary_scan_source = false
candidate_full_texts re-hash checks = pass for all selected candidates
```

The run uses `candidate_manifest_resolved.candidate_text_or_token_path` plus `candidate_chunk_manifest.csv` as the primary scan source. The `candidate_full_texts.jsonl.gz` rows are convenience/check rows only and were re-parsed to match the primary token streams.

## Scope Implemented

```text
cut = normal only
orders = 2, 3
profiles = P0, P1, P2
candidates = 10
chunks = 2 per candidate
planned scan cells = 120
```

Loaded phrase-entry counts:

```text
P0 normal order 2 = 3489
P0 normal order 3 = 15226
P1 normal order 2 = 3489
P1 normal order 3 = 15226
P2 normal order 2 = 3489
P2 normal order 3 = 15226
```

## Parity Status

Bounded Python parity was not run because the runner blocked immediately after the first C++ scan projection check.

```text
parity_row_count = 0
parity_not_run_due_to_block = true
all_required_parity_passed = false
```

## Review Questions

1. Should the next implementation rescope the first pilot to a smaller microbatch, for example one candidate, one chunk, and a single order/profile family?
2. Is the 120-second interactive budget too strict now that the compiled backend has a measured projection near 207 seconds for the approved 120-cell pilot?
3. Should we add an entry-index or grouped-by-length acceleration slice before attempting the 10-candidate pilot again?
4. Is it acceptable to run the exact approved 120-cell pilot in a separate PowerShell window with progress logging and a declared wallclock budget, or should the next step stay as an independently complete microbatch?

## Recommended Next Step

Prefer a microbatch review slice before a full 120-cell rerun:

```text
candidate_count = 1
chunks = 1
cut = normal
orders = 2, 3
profiles = P0, P1, P2
planned scan cells = 6
expected runtime from first observed scan = about 10-12 seconds plus parity
```

Then use the completed microbatch timing to decide whether to approve the full 10-candidate pilot, run it as a logged long-run, or implement a backend/entry-index acceleration slice first.
