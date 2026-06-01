# no-WLI Stage3 Entry Constant-Local-Depth Handoff Resume Plan

Date: 2026-05-01

Status:

- closed
- two-cell saved-handoff runtime
- not a full-pipeline panel
- not a matrix

## Question

Starting from saved `1111` handoffs, can constant-local-depth Stage-3 entry
allocation improve beyond retained legacy-entry results without recomputing the
full pipeline?

## Why this branch

The rank-6 route-lineage additive rule failed as a policy candidate. More
rank-6 rule-tuning is not the right next compute target.

The older constant-local-depth entry-allocation question remained unanswered
because the six-job full-pipeline panel capped after one completed control job.
The right rescope is to use saved handoff material and test one independently
complete cell.

## Activation Gate

Offline activation extractor:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage3_entry_const_local_depth_handoff_activation_v1.py`

Output:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T022336Z__stage3_entry_const_local_depth_handoff_activation_v1/`

Result:

- target rows: `3`
- structurally active rows: `3`
- mechanism-widened rows: `3`
- runtime launched: `0`

For all three saved `1111` handoffs:

- legacy init3: `64`
- candidate init3: `288`
- delta: `+224`
- candidate new init3 keys: `80`
- candidate missing legacy keys: `0`
- Phase-A config unchanged
- Phase-B config unchanged
- Phase-B top-n unchanged

Interpretation:

- the candidate is structurally active and preserves legacy keys
- this clears the no-runtime activation gate for a one-cell canary

## First Runtime Cell

Cell:

- fixture seed: `1111`
- search seed: `7005`
- handoff:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/20260412T053512632846Z__bench_solve_pipeline_no_wli__9557c0f/resume_handoffs/fixture_001__p9_c3_l1000__text0__seed1111__search7005/`

Reason:

- retained full-pipeline result is low:
  - `0.372`
- previous selected-row handoff inventory found the strongest headroom on this
  target
- retained legacy full-pipeline wallclock is about:
  - `2.479h`
- it avoids using `1111/search7002` as the first runtime cell, because
  `search7002` is the known heavy timing trap

## Candidate Configuration

Run-config override:

- `stage3.period_scaling.init_keys_cap = 288`
- `stage3.entry.allocation_policy = "constant_local_depth"`
- `stage3.entry.mutations_per_promoted = 1`

The runner rebuilds `stage3_prep` from saved `stage2_resume.json` and does not
recompute Stage 1 or Stage 2.

Runner:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage3_entry_const_local_depth_handoff_7005_v1.py`

Console log:

- `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage3_entry_const_local_depth_handoff_7005_2026-05-01.log`

Launch script:

- `planning/projects/no_wli/60_launch_scripts/no_wli_stage3_entry_const_local_depth_handoff_7005_launch_2026-05-01.ps1`

Active output:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T022917Z__stage3_entry_const_local_depth_handoff_7005_v1/`

Initial status:

- process launched:
  - yes
- stage3 status file:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T022917Z__stage3_entry_const_local_depth_handoff_7005_v1/cell_0001_1111_search7005_const_local_depth/stage3_resume_status.json`
- first observed state:
  - `status = running`
  - `phase = phaseA`
  - `phaseA_done = 0`
  - `phaseA_total = 144`
  - `evals_total = 49921`

Latest early heartbeat checked:

- checked at:
  - `2026-05-01T02:34:30Z`
- status file:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T022917Z__stage3_entry_const_local_depth_handoff_7005_v1/cell_0001_1111_search7005_const_local_depth/stage3_resume_status.json`
- status:
  - `running`
- phase:
  - `phaseA`
- Phase-A progress:
  - `6 / 144`
- latest step:
  - `408 / 800`
- evals:
  - `444685`
- latest status update:
  - `2026-05-01T02:34:30Z`

## Runtime Budget

Retained same-cell full-pipeline legacy anchor:

- `1111/search7005`
- elapsed: `2.479h`

Activation widening:

- legacy init3 `64`
- candidate init3 `288`
- entry-count widening factor `4.5x`

Budget:

- intended wallclock: `16h`
- watchdog cap: `57600s`
- user-approved outer allowance in chat: up to `89h`

Why `16h`:

- large enough for a 4.5x widened entry surface plus overhead
- well below the user-approved outer allowance
- only one independently complete cell is launched

Stop condition:

- candidate Stage-3 resume completes
- candidate Stage-3 resume fails with extractable status
- watchdog reaches `16h` and stops the job

Progress:

- wrapper emits completed-versus-total, elapsed, budget, and remaining time
- runner writes repo-relative output paths
- `artifact_resume` writes Stage-3 status/progress inside the cell output

## Decision Rule

Advance only if:

- the run completes
- the result improves meaningfully beyond retained `0.372`
- output contains enough Stage-3/stage35 status to explain where the gain came
  from

Hold if:

- the run is flat but diagnostically shows useful route or stage behavior
- the run caps with extractable partial Stage-3 progress

Close if:

- the run completes flat or worse with no useful mechanism evidence
- the run caps without interpretable partial evidence

## Recommended Next After Completion

Analyze the one cell before launching any second handoff cell. If it is
positive, the next candidate cell should be chosen between `1111/search7004`
and a control replay based on the observed stage diagnostics, not by inertia.

## First Cell Result

Cell:

- `1111/search7005`

Output:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T022917Z__stage3_entry_const_local_depth_handoff_7005_v1/`

Result:

- status:
  - `completed`
- elapsed:
  - `7139.745s`
  - `1.983h`
- retained best:
  - `0.372`
- candidate best:
  - `0.374`
- delta versus retained:
  - `+0.002`
- best stage:
  - `stage35_substitution_only`
- stage:
  - unsolved, small positive

Interpretation:

- constant-local-depth is not a large breakthrough on `7005`
- the first same-family timing anchor is under `2h`, not near the `16h`
  watchdog cap
- because the result is positive but small, the next useful cell is the second
  non-heavy activated target, `1111/search7004`
- do not jump to `1111/search7002` inside this 8h data-taking window because
  that lane has known heavy full-pipeline timings above `13h`

## Second Cell Result

Cell:

- `1111/search7004`

Runner:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/run_stage3_entry_const_local_depth_handoff_7004_v1.py`

Launch script:

- `planning/projects/no_wli/60_launch_scripts/no_wli_stage3_entry_const_local_depth_handoff_7004_launch_2026-05-01.ps1`

Console log:

- `planning/projects/no_wli/50_console_and_watch_logs/no_wli_stage3_entry_const_local_depth_handoff_7004_2026-05-01.log`

Output:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T064716Z__stage3_entry_const_local_depth_handoff_7004_v1/`

Budget:

- intended remaining-window cap:
  - `6h`
- watchdog cap:
  - `21600s`

Timing basis:

- same-family completed `7005` handoff:
  - `1.983h`
- retained same-cell legacy full-pipeline `7004` anchor:
  - about `2.360h`

Stop condition:

- one `7004` candidate Stage-3 resume completes
- it fails with extractable status
- watchdog reaches `6h`

Result:

- status:
  - `completed`
- elapsed:
  - `7755.439s`
  - `2.154h`
- retained best:
  - `0.423`
- candidate best:
  - `0.406`
- delta versus retained:
  - `-0.017`
- best stage:
  - `stage3_full_refine`

Mechanism:

- Phase-A best:
  - `0.422`
  - candidate hash `6858f26bdc4c4d1f`
- Phase-C final for that candidate:
  - `0.406`
  - match gain `-0.016`
- Stage 3.5:
  - archive rank `1` found
  - accept reason `search_score_drop_guard_failed`

## Closeout Decision

Close this exact constant-local-depth handoff-resume shape as a policy
candidate.

Do not launch `1111/search7002` for this branch. The two non-heavy cells already
give one small positive and one material regression; `7002` remains a known
heavy timing lane.

Closeout note:

- `planning/projects/no_wli/40_review_summaries/no_wli_stage3_entry_const_local_depth_handoff_closeout_2026-05-01.md`

Immediate follow-up:

- completed an offline downstream-selection audit on `7004` to explain why the
  widened-entry Phase-A best `0.422` was not preserved through final selection

## Downstream-Selection Audit

Extractor:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage3_entry_const_local_depth_downstream_selection_audit_v1.py`

Output:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T155731Z__stage3_entry_const_local_depth_downstream_selection_audit_v1/`

Result:

- cells:
  - `2`
- candidate positives:
  - `1`
- candidate negatives:
  - `1`
- posthoc Stage 3.5 accept-pass fallback gate:
  - kept `7005`
  - fell back to retained on `7004`
  - gated negative cells: `0`

Interpretation:

- the `7004` regression is downstream of entry activation
- Stage 3.5 accept failure is a plausible non-truth safety signal for rejecting
  this widened-entry result
- this is only a two-cell offline lead and does not justify runtime

Recommended next:

- test the Stage 3.5 accept-pass fallback gate offline on broader retained
  handoff/frontier outputs before any new runtime

## Broader Accept-Gate Audit

Extractor:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/extract_stage35_accept_gate_broader_offline_audit_v1.py`

Output:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T160206Z__stage35_accept_gate_broader_offline_audit_v1/`

Coverage:

- shallow frontier harvest:
  - `136` rows
- deepening harvest:
  - `15` rows
- total:
  - `151` rows

Result:

- Stage 3.5 accepted rows:
  - `147`
- accept-gate negatives versus retained:
  - `75`
- accept-gate negatives versus selected start:
  - `18`

Decision:

- close Stage 3.5 accept-pass as a general safety gate
- the `7005/7004` posthoc rule is local diagnostic evidence only
- no runtime from this line
