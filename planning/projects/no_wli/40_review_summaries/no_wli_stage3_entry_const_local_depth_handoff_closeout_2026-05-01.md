# No-WLI Stage3 Entry Constant-Local-Depth Handoff Closeout

Date: 2026-05-01

## Question

Starting from saved `1111` handoff artefacts, can constant-local-depth Stage-3
entry allocation improve beyond retained legacy-entry results without
recomputing the full pipeline?

This branch was deliberately run as saved-handoff Stage-3 resumes, not as a
repeat of the expensive six-job full-pipeline panel.

## Inputs

Activation output:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T022336Z__stage3_entry_const_local_depth_handoff_activation_v1/`

Activation result:

- `3 / 3` target handoffs structurally active
- `3 / 3` mechanism-widened
- legacy init3 `64`
- candidate init3 `288`
- candidate new init3 keys `80`
- candidate missing legacy keys `0`

Runtime cells:

- `1111/search7005`
- `1111/search7004`

`1111/search7002` was not run in this branch because prior timing evidence
marks it as a heavy trap lane, including the prior `13:32:47` completed control
job in the full-pipeline panel.

## Outputs

`7005` output:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T022917Z__stage3_entry_const_local_depth_handoff_7005_v1/`

`7004` output:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/fixed_instance_solver_development_v1/20260501T064716Z__stage3_entry_const_local_depth_handoff_7004_v1/`

## Results

| cell | status | elapsed | retained | candidate | delta | candidate best stage |
|---|---:|---:|---:|---:|---:|---|
| `1111/search7005` | completed | `7139.745s` | `0.372` | `0.374` | `+0.002` | `stage35_substitution_only` |
| `1111/search7004` | completed | `7755.439s` | `0.423` | `0.406` | `-0.017` | `stage3_full_refine` |

Both cells completed inside their watchdog caps with `0` runner errors.

## Mechanism Notes

`7005`:

- Phase A selected candidate `3e100d56e882a80a` at `0.378`
- Phase C moved that candidate to `0.374`
- Stage 3.5 accepted an archive row
- final result was a small positive versus retained: `+0.002`

`7004`:

- Phase A selected candidate `6858f26bdc4c4d1f` at `0.422`
- Phase C moved that candidate to `0.406`
- Stage 3.5 found a higher-score archive row but failed the search-score guard:
  - accept reason: `search_score_drop_guard_failed`
  - selected archive rank: `1`
- final result regressed versus retained by `-0.017`

## Interpretation

Constant-local-depth is structurally active and can change the Stage-3 entry
surface, but the two-cell runtime evidence is not safe enough to widen.

The branch produced one small positive and one material regression. The
negative `7004` result matters more than the small `7005` gain for policy
purposes, because the candidate mechanism can damage an already decent retained
lane.

The useful mechanism signal is narrower:

- extra entry surface can preserve high Phase-A candidates
- downstream Phase C / Stage 3.5 acceptance can still lose truth match
- the current legacy Stage 3.5 guard prevented accepting the `7004` archive row,
  but the final Stage-3 path was already below retained

## Decision

Close this exact constant-local-depth handoff-resume shape as a policy
candidate.

Do not launch `1111/search7002` for this exact branch. The two non-heavy cells
already falsified safe widening, and `7002` remains a known heavy timing lane.

## Recommended Next

Stay off broad runtime. The next useful step is offline analysis of the saved
`7004` handoff output to identify why the `0.422` Phase-A candidate was not
preserved through final selection.

Concrete next analysis:

- compare Phase-A best, Phase-C winner, and Stage 3.5 baseline/guard rows for
  `7004`
- ask whether the issue is entry allocation itself or downstream selection /
  finalization after Phase A
- only design more runtime if that offline audit gives a predeclared safety
  rule that would have kept `7005` and rejected the `7004` regression
