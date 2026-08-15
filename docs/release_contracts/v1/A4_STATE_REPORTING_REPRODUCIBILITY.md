# A4 state, reporting and reproducibility contract

A4 completes the existing June V1 reporting contract. It does **not** introduce a second reporting or run-status framework.

The canonical durable run-status schema remains:

`rdp.run_status_contract.v1`

A4 extends that contract so four questions are represented separately:

1. Did execution run and return normally?
2. Why did execution stop?
3. Was scientific recovery assessed, and what was recovered?
4. Did a tutorial meet its declared acceptance policy?

`Solution.stop_reason` remains the low-level compatibility field. `SolverReport.details.run_status` is the canonical durable status object.

## State and termination

A4 adds `execution_status`:

- `completed`
- `blocked_before_run`
- `error`
- `manual_stop`
- `not_started`

The June coarse `stop_category` values remain unchanged:

- `success`
- `budget`
- `blocked_before_run`
- `error`
- `manual`
- `not_started`

Natural solver limits are producer-owned. Beam, GA, SA and Kaeding report their own configured work limits rather than leaving a missing reason or generic `done`. Hybrid and the staged two-period route report completion of their configured work as a budget/work-limit condition.

Legacy `done` and `success` are ambiguous and are **not** promoted to canonical success. If they reach the A4 mapper without a more precise producer reason they become `unknown_runtime_reason`, making the reporting defect visible.

Scientific recovery is separate and defaults to `not_assessed`. A completed run or a `success` stop category does not by itself prove correct plaintext/key recovery.

## Oracle / truth data

`run_status.oracle` and the compatibility `details.oracle` use the June fields:

- `available`
- `used_for_scoring`
- `used_for_ranking`
- `used_for_stop`
- `stop_reason`
- `mode`

A test-key shortcut is explicit test oracle use for stopping, not scoring/ranking. The existing V1 known-key fast-path contract is preserved as explicit reported test/tutorial truth use; it is not presented as an ordinary real-solve handoff and it never uses truth for scoring or ranking. The older `oracle_use` and `truth_data_policy` fields remain compatibility breadcrumbs.

## Requested and effective configuration

`details.configuration` contains compact requested/effective summaries for solver, scoring and cipher configuration. This is reporting metadata, not a replacement configuration API. A3 configuration contracts remain authoritative.

## June reproducibility mapping

Every June reproducibility field is emitted in `details.reproducibility` and repeated inside `details.run_status.reproducibility`:

`run_id`, `created_at_utc`, `rdp_version`, `git_branch`, `git_commit`, `python_version`, `backend`, `device`, `dtype`, `seed`, `stochastic`, `solver_config`, `scoring_config`, `objective`, `cipher`, `asset_ids`, `asset_hashes`, `dictionary_policy`, `stop_category`, `stop_reason`.

Values that cannot be established are `null`, `unknown`, or `not_applicable`; they are never guessed. In particular, `created_at_utc` comes from real logging metadata or the engine run-start timestamp, not report-construction time. To implement that existing June rule consistently, the carried-forward schema permits `stochastic: null` when stochasticity genuinely cannot be established; the original boolean values remain unchanged when known.

## Portable paths

Runtime filesystem paths may remain absolute in memory. Durable metadata must not expose private absolute Windows, POSIX or UNC paths, or parent traversal outside the repository/run root. Repository-local paths are POSIX relative paths. External locations are represented by explicit labels such as `<external:out_root>`.

The local development/release evidence root is tooling infrastructure, not an RDP user-facing runtime default.

## Tutorial acceptance

The release tutorial runner records process success and acceptance separately. Existing thresholds and run-set membership are unchanged. The aggregate compatibility result remains:

`passed = process_succeeded and acceptance_met`

The lower-level tutorial benchmark contract is not given a new acceptance field because it does not own the release runner's `TutorialAcceptanceKind` policy.
