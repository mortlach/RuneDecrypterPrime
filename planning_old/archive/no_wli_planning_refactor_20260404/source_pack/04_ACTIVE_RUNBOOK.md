# Active runbook

## Immediate next run

Run the single fresh hard-seed map collection:

- mode:
  - `candidate_single_p9_seed611`
- experiment:
  - `tune_v62_p9c3_seed611_stage35_baseline_selector_candidate_live_bounded_space_map_v1_single_1job`

## Why this is next

- `v61` already gave:
  - two solved `p7/c1` controls
  - one fresh mapped hard anchor on `p9/c3 seed411`
- `v61` did **not** give:
  - `p9/c3 seed611`
- so the remaining high-value missing evidence is the fresh hard-seed map,
  not another mixed panel.

## What to inspect first after `v62`

### Core artifact files

- `final_instances/*.json`
- `best/best_instance.json`
- `phasec_start_checkpoints.jsonl`
- if Stage 3.5 runs:
  - `stage35_progress.jsonl`
  - `stage35_partial_state.json`

### Analysis outputs

- `analysis/space_map_v1_atlas/...`
- `analysis/space_map_v1_audit/...`

## First comparison questions

### Outcome layer
- baseline row switched?
- Stage 3.5 accepted?
- best stage?
- best match ratio?

### Map layer
At each boundary:
- `stage2_promoted`
- `stage3_prep`
- `phaseC_pool`
- `phaseC_start`
- `stage35_seed`
- `stage35_archive`

Read:
- row count
- family count
- selected family count
- largest-family share
- continuity of the best family
- where diversity collapses

### Taxonomy layer
- Does `seed611` show the same broad hard-family shape as `seed411`?
- Or is it a materially different hard-seed structure?

## How to classify the result

### Green
- `seed611` runs cleanly
- `space_map_v1` populates cleanly
- the map is interpretable enough to compare to `seed411`

### Yellow
- run completes but the map is noisy because of ancestry/provenance gaps
- still useful, but keep conclusions modest

### Red
- run fails or key artifact layers are missing
- fix measurement path before broader interpretation

## Parallel offline work

While `v62` runs or waits:
- keep `score_stop_shadow_v2` offline-only
- do not widen it before the first tiny panel readout
- keep any stop-claim benchmark-only until separate non-oracle calibration is
  convincing
