# No-WLI Fixed-Instance Mode Infrastructure Plan

Status note:

- completed and frozen as of `2026-04-14`
- this remains the baseline record for the infrastructure phase
- active follow-on work now lives in:
  - `planning/projects/no_wli/20_active_plans/no_wli_fixed_instance_solver_development_plan_2026-04-14.md`

Authoritative spec:

- `planning/projects/no_wli/30_analysis_specs/no_wli_fixed_instance_mode_v1_spec_2026-04-08.md`

## Purpose

Land a new no-WLI input mode where the benchmark instance is frozen and solver
variation comes only from `search_seed`.

This stream is infrastructure, not solver science.

## Frozen background

The stop / family-quality / triage stack is now frozen as review-ready
background:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/20260408T142942Z__score_stop_shadow_v2/`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v1/20260408T152322Z__late_family_quality_v1/`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v2/20260408T154637Z__late_family_quality_v2/`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v3/20260408T162219Z__late_family_quality_v3/`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/seed_family_triage_shadow_v1/20260408T172151Z__seed_family_triage_shadow_v1/`

Do not mutate that stream while landing fixed-instance mode except for bug
fixes.

## First frozen panel

Use these frozen instances in v1:

- `611`
- `1111`
- `1411`
- `1511`

The first panel manifest is required and must stay fixed:

- `tools/benchmarks/periodic_sub_trans/no_wli/fixed_instance_panels/p9_c3_solver_panel_v1.json`

## Patch order

### Patch 1 - exporter, schema, manifest

Files:

- `tools/benchmarks/periodic_sub_trans/no_wli/fixed_instance_models.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixed_instance_io.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/export_fixed_instance_fixtures.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixed_instance_panels/p9_c3_solver_panel_v1.json`
- `tests/tools/test_no_wli_fixed_instance_mode.py`

Status:

- completed on 2026-04-08
- generated fixtures now live under:
  - `tools/benchmarks/periodic_sub_trans/no_wli/fixed_instances/`
- validation:
  - `tests/tools/test_no_wli_fixed_instance_mode.py`
  - `6 passed`

Done means:

- fixtures validate
- `true_key_idx` is present
- re-encryption matches stored ciphertext
- `target_wli` is reconstructed and verified

### Patch 2 - state/config plumbing

Files:

- `tools/benchmarks/periodic_sub_trans/no_wli/runner_state_defaults.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/run_config_builder.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/run_mode_apply.py`
- `tests/tools/test_no_wli_fixed_instance_mode.py`

Status:

- completed on 2026-04-08
- validation:
  - `tests/tools/test_no_wli_fixed_instance_mode.py`
  - `10 passed`

Done means:

- generated mode still uses `KEY_SEEDS`
- fixed mode uses `INSTANCE_FIXTURE_IDS` and `SEARCH_SEEDS`
- saved config distinguishes generated vs fixed mode honestly

### Patch 3 - runtime branch

Files:

- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_runtime.py`
- `tests/tools/test_no_wli_fixed_instance_mode.py`

Done means:

- generated mode unchanged
- fixed mode consumes stored ciphertext/plaintext/true key
- fixed mode roundtrip and oracle helpers verify cleanly

Status:

- completed on 2026-04-08
- validation:
  - `tests/tools/test_no_wli_fixed_instance_mode.py`
  - targeted mixed slice:
    - `tests/tools/test_no_wli_fixed_instance_mode.py`
    - `tests/tools/test_no_wli_iteration_runtime_word_ngram_sidechannel.py`
    - `tests/tools/test_no_wli_iteration_matrix_fixed_seed_parity.py`
    - `tests/tools/test_no_wli_stage_engine_parity_smoke.py`
  - `27 passed`

### Patch 4 - iteration-loop branch

Files:

- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_matrix_flow.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_pre_stage3.py`
- `tests/tools/test_no_wli_fixed_instance_mode.py`

Done means:

- generated loop unchanged
- fixed loop is tier x instance fixture x search seed
- no on-the-fly plaintext slicing or ciphertext regeneration in fixed mode

Status:

- completed on 2026-04-08
- validation:
  - `tests/tools/test_no_wli_fixed_instance_mode.py`
  - targeted mixed slice:
    - `tests/tools/test_no_wli_fixed_instance_mode.py`
    - `tests/tools/test_no_wli_iteration_runtime_word_ngram_sidechannel.py`
    - `tests/tools/test_no_wli_iteration_matrix_fixed_seed_parity.py`
    - `tests/tools/test_no_wli_stage_engine_parity_smoke.py`
  - `27 passed`

### Patch 5 - identity/output/resume/proven plumbing

Files:

- `tools/benchmarks/periodic_sub_trans/no_wli/artifact_resume.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/run_summary.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/autoskip_proven.py`
- payload / bridge builders that emit row identity
- final artifact naming paths
- `tests/tools/test_no_wli_fixed_instance_mode.py`

Done means:

- fixed identity is based on `(instance_fixture_id, search_seed)`
- generated identity stays `(fixture, text_id, key_seed)`
- no resume/proven collisions across modes or search seeds
- fixed-mode outputs contain the new identity fields everywhere relevant

Status:

- completed on 2026-04-08
- landed helper:
  - `tools/benchmarks/periodic_sub_trans/no_wli/iteration_identity.py`
- landed identity/output/resume files:
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage_iteration_payload.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/iteration_finalize.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/iteration_post_stage3.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/autoskip_proven.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/run_summary.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/stage_iteration_commit.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/run_completion.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/artifact_resume.py`
  - `tests/tools/test_no_wli_fixed_instance_mode.py`
- validation:
  - focused identity/resume slice:
    - `tests/tools/test_no_wli_fixed_instance_mode.py`
    - `tests/tools/test_no_wli_run_completion.py`
    - `tests/tools/test_no_wli_stage_iteration_commit.py`
    - `tests/tools/test_no_wli_resume_handoff_artifacts.py`
    - `34 passed`
  - broader mixed slice:
    - `tests/tools/test_no_wli_fixed_instance_mode.py`
    - `tests/tools/test_no_wli_iteration_runtime_word_ngram_sidechannel.py`
    - `tests/tools/test_no_wli_iteration_matrix_fixed_seed_parity.py`
    - `tests/tools/test_no_wli_stage_engine_parity_smoke.py`
    - `tests/tools/test_no_wli_artifact_resume.py`
    - `47 passed`

### Patch 6 - first fixture-matrix execution path

Files:

- fixture-matrix path only
- no broader entrypoint retrofit yet

Done means:

- one fixed-instance panel can be executed through the fixture-matrix path
- outputs are honest and resumable

Status:

- completed on 2026-04-08
- landed fixture-matrix files:
  - `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_models.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_jobs.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_api.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_mainflow.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_plan.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_runtime.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/run_fixture_matrix.py`
- landed runner/config bridge files:
  - `tools/benchmarks/periodic_sub_trans/common/campaign_run_config.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/runner_entrypoints.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/campaign_config_apply.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/runner.py`
  - `tools/benchmarks/periodic_sub_trans/no_wli/run_pipeline_execution.py`
  - `tests/tools/test_no_wli_fixed_instance_mode.py`
  - `tests/tools/test_no_wli_fixture_matrix.py`
  - `tests/tools/test_no_wli_fixture_matrix_mainflow.py`
  - `tests/tools/test_no_wli_fixture_matrix_runtime.py`
- validation:
  - focused fixture-matrix slice:
    - `tests/tools/test_no_wli_fixed_instance_mode.py`
    - `tests/tools/test_no_wli_fixture_matrix.py`
    - `tests/tools/test_no_wli_fixture_matrix_mainflow.py`
    - `tests/tools/test_no_wli_fixture_matrix_runtime.py`
    - `60 passed`
  - broader compatibility slice:
    - `tests/tools/test_no_wli_fixed_instance_mode.py`
    - `tests/tools/test_no_wli_fixture_matrix.py`
    - `tests/tools/test_no_wli_fixture_matrix_mainflow.py`
    - `tests/tools/test_no_wli_fixture_matrix_runtime.py`
    - `tests/tools/test_no_wli_fixture_matrix_hardening.py`
    - `tests/tools/test_periodic_sub_trans_campaign_run_config.py`
    - `tests/tools/test_no_wli_artifact_resume.py`
    - `84 passed`
- note:
  - the code path is landed and validated under fixture-matrix tests
  - no long live fixed-mode matrix campaign was launched in this patch

### Post-patch-6 hardening

Files:

- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_config.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_mainflow.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_runtime.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/iteration_matrix_flow.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/artifact_resume.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixed_instance_io.py`
- `tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_jobs.py`
- `tests/tools/test_no_wli_fixed_instance_mode.py`
- `tests/tools/test_no_wli_fixture_matrix_mainflow.py`
- `tests/tools/test_no_wli_fixture_matrix_runtime.py`

Done means:

- checked-in defaults do not leave fixed canary active by accident
- fixed mode does not depend on campaign config loading
- mapping-based fixed specs use shared validation
- fixed-mode tier mismatch cannot silently resolve to zero jobs
- fixed-mode resume identity fails hard when required fields are missing

Status:

- completed on 2026-04-08
- validation:
  - `tests/tools/test_no_wli_fixed_instance_mode.py`
  - `tests/tools/test_no_wli_fixture_matrix_mainflow.py`
  - `tests/tools/test_no_wli_fixture_matrix_runtime.py`
  - `tests/tools/test_no_wli_fixture_matrix.py`
  - `67 passed`
- note:
  - the already-started `v70` fixed canary was left running
  - checked-in config is now back to safe generated defaults

## Current operational staging

- `v70` fixed canary is complete:
  - `tune_v70_fixed_p9c3_fixture611_search7001_stage35_baseline_selector_score_plus_novelty_canary_1job`
- `v71` fixed long panel is now stopped locally at the intended handoff point:
  - `tune_v71_fixed_p9c3_panelv1_search7001_7005_stage35_baseline_selector_score_plus_novelty_live_bounded_20job`
  - local completion state:
    - jobs `1-3` complete
    - original job `4` started but did not complete
- the original fixed 20-job panel is now fully collected across retained runs:
  - `v71` local slice:
    - original jobs `1-3`
  - `v72a`:
    - panel:
      - `tools/benchmarks/periodic_sub_trans/no_wli/fixed_instance_panels/p9_c3_solver_panel_v1_jobs04_05.json`
    - `2 / 2` jobs completed at `2026-04-11T05:09:42Z`
  - `v72b`:
    - panel:
      - `tools/benchmarks/periodic_sub_trans/no_wli/fixed_instance_panels/p9_c3_solver_panel_v1_jobs06_10.json`
    - `5 / 5` jobs completed at `2026-04-12T08:04:07Z`
  - `v73`:
    - panel:
      - `tools/benchmarks/periodic_sub_trans/no_wli/fixed_instance_panels/p9_c3_solver_panel_v1_jobs11_20.json`
    - `10 / 10` jobs completed at `2026-04-14T08:42:39Z`
- completed-data audit:
  - `20` completed-job report bundles are retained with `run_manifest.json`,
    `final_instances`, and `best/best_instance.json`
  - one extra interrupted local `v71` job-4 bundle remains without
    `best/best_instance.json`
  - one stale `v72b` log reference points to a non-retained path

Constraint:

- keep checked-in config on:
  - `FIXED_INSTANCE_EXECUTION_PROFILE = "off"`
- launch all fixed follow-on slices only through the dedicated scripts

## Non-negotiables

- do not overload `FixtureSpec`
- do not overload `KEY_SEEDS`
- do not postpone identity/output/resume/proven work
- do not treat `source_key_seed` as solver randomness in fixed mode
- do not start solver experiments before the infrastructure branch is solid

