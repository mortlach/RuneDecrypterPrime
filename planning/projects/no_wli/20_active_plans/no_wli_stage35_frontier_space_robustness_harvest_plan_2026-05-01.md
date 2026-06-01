# No-WLI Stage35 Frontier Space Robustness Harvest Plan

Date: 2026-05-01

Status:

- completed

## Question

Across held-out Stage 3.5 frontier strata, does deeper bounded local rescue
stabilize useful gains or mostly amplify the shallow mixed signal?

This is not a policy-promotion run. It is a data-taking run to map a different
part of the local-rescue space after these policy candidates closed:

- softened rank-6 local rescue
- source-rank plus route-novelty additive rescue
- constant-local-depth handoff-resume
- simple Stage 3.5 accept-pass fallback

## Mechanism Layer

- local search / rescue

More specifically:

- deeper bounded Stage 3.5 continuation from saved frontier rows
- stratified by prior shallow behavior rather than by one proposed policy rule

## Inputs

Source shallow frontier rows:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T152907Z__stage35_guard_selector_frontier_runtime_harvest_v1/stage35_guard_selector_frontier_runtime_rows.csv`

Prior deepening rows used for calibration-repeat marking:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260429T155324Z__stage35_guard_selector_frontier_deepening_harvest_v1/stage35_guard_selector_frontier_deepening_rows.csv`

Runner:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage35_frontier_space_robustness_harvest_v1.py`

Console log:

- `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage35_frontier_space_robustness_harvest_2026-05-01.log`

## Queue Shape

The queue is capped at `48` unique logical cells, deduped by:

- fixture seed
- search seed
- candidate rank
- candidate hash

Planned strata:

- calibration repeats from prior deepening
- shallow negatives
- shallow neutrals
- rank `1-5` moderate positives
- rank `1-5` high positives
- held-out rank-6 positives

Cheap preflight queue check selected:

- total cells: `48`
- calibration repeats: `6`
- shallow negatives: `14`
- shallow neutrals: `10`
- rank `1-5` moderate positives: `13`
- held-out rank-6 positives: `5`

## Runtime Budget

Intended wallclock budget:

- `8h`

Hardcoded caps:

- run wallclock cap: `28800s`
- per-cell cap: `1800s`
- max cells: `48`

Stage 3.5 override:

- `rounds = 6`
- `seed_keep = 6`
- `beam_width = 3`
- `archive_keep = 36`
- `mini_search_steps = 3`
- `mini_search_beam_width = 4`
- `mini_search_top_symbols = 12`
- `mini_search_final_keep = 6`
- `accept_guard_passing_selector_mode = top_score_then_search`

Timing basis:

- shallow frontier harvest completed `136` cells in `721.112s`
- prior focused deepening completed `15` cells in `1919.390s`
- this run uses a deeper per-cell configuration, so it is a new timing shape
- first-cell projection must be printed and used as the budget anchor

## Stop Condition

Stop when the first of these occurs:

- queue exhausted
- wallclock cap reached
- first-cell serial projection exceeds the `28800s` session budget

Partial output is written after every cell.

Progress must include:

- completed-versus-total cells
- successful and error cells
- elapsed seconds
- rough ETA
- last-cell elapsed seconds

## Prediction Ledger

Prediction recorded before launch for later comparison:

- suspicion:
  - rank-6 held-out positives will mostly remain useful, but shallow negatives
    and rank `1-5` neutral/positive rows will stay mixed enough to block a
    simple policy
- main alternative:
  - a deeper rescue budget may reveal a broader stable stratum outside rank 6,
    or may recover shallow regressions often enough to justify a new feature
    design branch
- if suspicion is true, expect:
  - rank-6 held-out rows have a high nonnegative rate
  - non-rank-6 and shallow-negative rows produce both gains and regressions
- if alternative is true, expect:
  - at least one non-rank-6 or shallow-negative stratum shows a clean recovery
    pattern large enough to justify a narrow follow-up rule

## Tomorrow's Decision Rule

Promote no policy directly from this harvest.

Continue only if a predeclared stratum is strongly nonnegative and materially
useful. Otherwise close local-rescue policy widening and keep the output as
mechanism evidence.

## Recommended Next

After completion, analyze stratum-level results first, then update:

- `00_CURRENT_STATE.md`
- `01_EXPERIMENT_INDEX.md`
- `02_OPEN_QUESTIONS.md`
- `03_DOCUMENT_MAP.md`
- `04_ACTIVE_RUNBOOK.md`
- `10_full_logs/no_wli_science_run_log_2026-03-26.md`
- runtime timing references, if the completed run materially adds timing
  evidence

## Completed Result

Output:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T161846Z__stage35_frontier_space_robustness_harvest_v1/`

Closeout:

- `planning/projects/no_wli/40_review_summaries/no_wli_stage35_frontier_space_robustness_harvest_closeout_2026-05-01.md`

Result:

- status: `completed`
- completed cells: `48 / 48`
- errors: `0`
- elapsed: `12602.918s`
- Stage 3.5 selected cells: `32 / 48`
- better than shallow among selected: `27 / 32`
- worse than shallow among selected: `3 / 32`
- nonnegative versus selected start among selected: `28 / 32`
- negative versus selected start among selected: `4 / 32`

Decision:

- do not promote a policy directly from this harvest
- do not launch another broad local-rescue runtime batch immediately
- next step is an offline acceptance-boundary extractor over the completed
  harvest
