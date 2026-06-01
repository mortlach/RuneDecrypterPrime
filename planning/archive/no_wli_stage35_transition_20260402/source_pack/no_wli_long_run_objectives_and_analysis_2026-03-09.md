# No-WLI Long Run Objectives and Analysis Plan (2026-03-09)

## Branching Decision

Current branch: `experimental/merge`  
Current state: not clean (multiple modified files still staged for merge integration work).

Decision:
- Do **not** switch to a new branch yet.
- First checkpoint this merge state (commit), then branch for post-merge tuning/experiments.

Recommended sequence:
1. Commit remaining merge-integration changes on `experimental/merge`.
2. Tag that commit as merge baseline.
3. Create new branch for tuning campaign work (example: `experimental/no_wli_longrun_tuning`).

## Long-Run Purpose

This run is not just a solve attempt. It is a measurement campaign to:
- Validate that merged scoring telemetry is emitted correctly at runtime.
- Quantify value of span-hamming + word-ngram report-side channels.
- Produce evidence for next tuning decisions (not intuition-only changes).

## Success Criteria

The run is successful only if all are true:
1. Runner completes within wallclock budget (about 20 hours cap).
2. Artifacts include expected word-ngram and scorer-report telemetry fields.
3. Stage2/Stage3 top-k report payloads are populated where available.
4. No absolute-path leaks or path-policy regressions in emitted configs/metadata.
5. We can rank next tuning knobs using measured impact.

## What We Expect To Learn

Primary learning:
- Which period/column regimes (9/11/13) are tractable under current compute budget.
- Whether span-basin judging improves phase-B seed quality materially.
- Whether word-ngram telemetry correlates with higher final match ratio.

Secondary learning:
- Which gate and pool knobs dominate quality/time tradeoff.
- Where pipeline time is spent (Stage1 vs Stage2 vs Stage3).

## Pre-Run Checklist

1. Confirm branch includes latest merge fixes.
2. Confirm word-ngram sqlite path resolves (report-side channel enabled).
3. Confirm fixture matrix config:
- fixture length override: 1000 chars
- periods: 9, 11, 13
- columns:
  - p9: 1, 3, 5
  - p11: 1, 3, 5
  - p13: 1, 3, 5
- scoring experiment profiles: `c_min_late`
- run seeds: 111, 211, 311
- torch scorer impl
- wallclock cap ~20h
4. Confirm output paths are repo-relative.

Expected campaign size from current config:
- fixtures: 1
- schedules: 1
- jobs: 27

## During-Run Monitoring

Track these from logs/events:
- per-job start/finish and elapsed time
- stage3 phase gate decisions
- stage3 solve-hit frequency and best match
- span basin judge call counts and timing
- any missing scorer-report/word-ngram report sections

Stop conditions:
- Repeated runtime/config failures.
- Telemetry missing in first completed jobs (indicates bad configuration).

## Post-Run Analysis Workflow

## 1) Collect Artifacts

From each run output directory, gather:
- `run_manifest.json`
- `iteration_audit_chain.csv` and `.jsonl`
- `final_instances/*.json`
- stage2/stage3 top-k payloads
- word-ngram report payloads

## 2) Validate Telemetry Presence

For each completed job, assert presence/shape of:
- `word_ngram_report`
- `stage2_topk_word_ngram_report`
- `stage3_topk_word_ngram_report`
- embedded scorer-report sections and compatibility fields

## 3) Compute Learning Tables

Create per-job summary table:
- fixture id, period, columns, seed
- final match ratio
- solved/not solved
- total runtime
- stage1/stage2/stage3 effort counters
- span judge activity/time
- word-ngram trust/xent/positions (where active)

Create top-k correlation table:
- correlation between word-ngram signals and match ratio
- correlation between stage2 score, judge score, and match ratio

## 4) Decide Next Tuning Moves

Pick only 1-2 knobs for next experiment based on evidence:
- `STAGE3_PHASEB_TOP_N`
- phase-B gate thresholds
- stage2 promotion/judge pool size

Do not change many knobs at once.

## Run-Specific Hypotheses

This run is intentionally different from the previous long run.  
The concrete hypotheses are:

1. On 1000-char runs, p13 with low columns (1/3/5) can reach materially higher best-match than prior baseline settings.
2. `c_min_late` with span basin-judge can improve phase-B seed quality without destabilizing determinism.
3. Word-ngram telemetry quality (positions/trust/xent) will separate better vs worse top-k candidates.

## Primary Readout for This Run

At run end, produce one comparison table:
- grouped by `(period, columns, run_seed)`
- metrics:
  - solved fraction
  - best match ratio
  - median runtime
  - stage3 phaseB entered rate
  - word-ngram active rate

If p13 (columns 1/3/5) does not show improvement over prior best-match baselines, tune Stage3 gates/top-N before expanding to harder columns.

## Decision Gate After This Run

Proceed to broad unsolved-cipher long scan only if:
1. Telemetry contract is complete and stable.
2. Correlations are interpretable (not empty/noisy).
3. No policy regressions (paths/privacy/report consistency).

If not, run one shorter targeted correction campaign before broad scan.

## Run Review Update (2026-03-10)

Observed from latest long run artifacts:
- Campaign stopped early at 15/27 jobs (`remaining_jobs=12`, `stopped_early=1`).
- Completed cells were p9/p11 only (p13 was not reached yet).
- Best completed result so far: p9 c3 seed211 with `best_match_ratio=0.637`.
- No solves in the 15 completed jobs.
- Stage3 Phase-B and span basin judging were active, but did not convert to solves.
- Word-ngram telemetry was present, but often inactive/low-trust for weak candidates.

### Key implication

The previous run did not actually test the main p13 objective.  
Next pass should prioritize p13 first and avoid expensive low-yield cells.

## Tune Pass v2 (configured)

Updated campaign knobs for the next pass:
- periods order: `13, 11, 9` (p13 first)
- columns per period: `(1, 3)` only (drop c5)
- length override: `1000`
- seeds: `111, 211, 311, 411, 511`
- profile id: `no_wli_a1_m12_b34_stage3avg_fulltext_v1`
- explicit schedule:
  - early: `a_char1_avg_fulltext`
  - middle: `m_char12_avg_fulltext`
  - late: `b_char4_avg_fulltext`
- scoring experiment: `c_min_late`

Rationale:
- Broader A/M scoring should improve candidate diversity and stage2 quality.
- p13-first ordering ensures the main objective is tested immediately.
- Removing c5 increases budget per useful cell/seed.

## Current Run Learning Goals (2026-03-10, Forced Phase-B)

This is the active run after enabling forced two-phase and longer Phase-B settings.

Primary goals:
1. Verify Phase-B actually runs in p13 cells (`phaseB_ran=1`) instead of being skipped.
2. Verify span-basin judge is engaged (`basin_judge_span_calls_total > 0`) for p13 c1/c3.
3. Measure whether p13 c1/c3 best-match improves vs early baseline (~0.22 to ~0.25 range).
4. Confirm stage2/stage3 top-k word-ngram report payloads remain populated and stable.

Decision thresholds for this run:
- Positive signal:
  - p13 c1 or c3 reaches `best_match_ratio >= 0.35`
  - and Phase-B + span-basin telemetry is active in most seeds.
- Strong signal:
  - p13 c3 reaches `best_match_ratio >= 0.50`.
- No-signal outcome:
  - p13 c1/c3 remains < 0.30 across seeds despite Phase-B and span-basin activity.

What to record from this run:
- per `(period, columns, seed)`:
  - `best_match_ratio`, `best_stage`, `status`
  - `stage3_diagnostics.phaseB_ran`
  - `stage3_diagnostics.basin_judge_span_calls_total`
  - `stage3_diagnostics.span_basin_judge_seconds`
  - `stage3_diagnostics.stage3_eval_count`
  - word-ngram final/top-k active rates

## Next Target Learning Runs

Run A: p13 c3 seed sweep (solve-focused)
- Goal: maximize solve chance on the hardest relevant low-column cell.
- Setup:
  - period 13 only
  - column 3 only
  - 8 to 12 seeds
  - keep forced two-phase and c_min_late
- Learn:
  - whether p13 c3 is fundamentally tractable with current scorer stack.

Run B: p13 c1 vs c3 direct compare (cost-vs-yield)
- Goal: quantify if c1 is just cheap smoke or actually predictive.
- Setup:
  - period 13 only
  - columns 1 and 3
  - same seed set
- Learn:
  - whether to spend future budget mostly on c3.

Run C: Phase-B sensitivity sweep
- Goal: find best Phase-B depth without wasting runtime.
- Setup:
  - fixed p13 c3 seed set
  - compare two configs:
    - current (`steps=5600`, `top_n=24`)
    - deeper (`steps=7200`, `top_n=32`)
- Learn:
  - improvement per additional Stage3 evals.

Run D: Gate sensitivity sweep
- Goal: determine if Phase-B gating is too strict or too loose.
- Setup:
  - fixed p13 c3 seed set
  - compare:
    - current gate (`delta=0.006`, `end_gain=0.003`)
    - looser gate (`0.004`, `0.002`)
- Learn:
  - whether additional Phase-B entries convert to better final match.

Run E: Scorer A/M contract compare (exploration quality)
- Goal: test whether broader A/M schedule is helping or harming entry quality.
- Setup:
  - same p13 c3 seed set
  - compare:
    - `a_char1_avg_fulltext + m_char12_avg_fulltext`
    - `a_char2_avg_fulltext + m_char4_avg_fulltext`
- Learn:
  - which Stage1/2 path produces stronger Stage3 starting points.
