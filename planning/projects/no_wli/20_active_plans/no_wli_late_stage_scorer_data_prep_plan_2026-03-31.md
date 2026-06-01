# No-WLI late-stage scorer data-prep plan

## Purpose

Prepare the pipeline and saved artifacts so the next late-stage scorer experiment can use a real explored frontier with replayable candidate material, instead of reconstructing candidates ad hoc from partial telemetry.

This is deliberately a data-capture and replay-readiness slice, not a new scorer or selector intervention.

## What is now in place

### 1. Phase-C start summaries now carry replayable candidate material

Live Phase-C start summaries now persist:

- `init_key_idx`
- `init_plaintext_idx`
- `final_key_idx`
- `final_plaintext_idx`

These fields are threaded through the same saved frontier path used for:

- `stage3_diagnostics.phaseC_start_summaries`
- `phasec_start_checkpoints.jsonl`

This means future late-stage runs can be turned into scorer fixtures without reconstructing challenger keys from unrelated artifacts.

### 2. Contract hardening now protects that capture path

`tools/benchmarks/periodic_sub_trans/no_wli/phasec_diagnostics_contract.py`
now treats the replay-capture fields as required whenever:

- Phase-C ran
- and start summaries are being persisted

This is important because it turns frontier-capture completeness into an explicit contract, not a best-effort convenience field.

### 3. Frontier export scaffold exists

New exporter stack:

- `tools/benchmarks/periodic_sub_trans/no_wli/late_stage_frontier_fixture.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/export_late_stage_frontier_fixture.py`

This can already export a saved run into a frozen frontier bundle with:

- winner hash
- oracle-best explored challenger hash
- candidate telemetry
- completeness flags for replayable key/plaintext material

## What the current `v45` export proves

Current export:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_frontier_fixtures/v45_seed411_late_frontier.json`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_stage_frontier_fixtures/v45_seed411_late_frontier.md`

What it shows:

- `candidate_count = 6`
- `winner hash = 73eee2bf84b7c07f`
- `oracle-best explored hash = 9002ee09917e5a0d`
- `frontier_key_material_complete = 0`
- `candidates_with_final_key_idx = 0`
- `candidates_with_final_plaintext_idx = 0`

Interpretation:

- the exporter is working
- the current historical `v45` artifact is still useful as a telemetry fixture
- but it is not yet a fully replayable scorer fixture because the run happened before the new Phase-C frontier capture fields landed

## Immediate consequence

We do **not** need another scorer design pass first.

We need one clean post-hardening late-stage run on the same class of case so the frontier export contains:

- the explored candidates
- their final keys
- their final plaintexts

After that, the scorer experiment can replay real candidate keys directly.

## Recommended next data-prep step

1. Keep the current late-stage scorer study spec separate from implementation.
2. Use the next appropriate `411`-style late-stage run as the first replay-ready frontier source.
3. Export that run immediately with `export_late_stage_frontier_fixture.py`.
4. Promote the exported frontier into a frozen test fixture only once:
   - key/plaintext coverage is complete
   - and the frontier is clearly the intended benchmark failure case

## Guardrails

- Do not add oracle truth to live selector behavior.
- Do not add another temporary replay shim just for old `v45`.
- Do not weaken the new Phase-C frontier capture contract to accommodate older artifacts.
- Keep the scorer experiment boundary separate from this data-prep slice.

## Success condition

The next scorer-spec implementation should be able to take:

- one exported frontier fixture
- its candidate `final_key_idx`
- its candidate `final_plaintext_idx`
- and trial keys

and run cheap late-stage selector experiments without rerunning the full pipeline.
