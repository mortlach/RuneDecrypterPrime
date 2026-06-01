# No-WLI score-stop core/pressure transparency plan

Date: 2026-04-07

## Purpose

This plan turns the current `score_stop_shadow_v2` stop study into a cleaner
two-panel benchmark:

- a frozen **core benchmark panel** for continuity
- a frozen **pressure falsification panel** for broader false-positive checks

It also defines the first strict no-drift transparency pass on top of that
panel split.

This is an offline analysis change only. It does not change live solver
behaviour.

## Why this is the next move

The current evidence split is scientifically clean but too implicit:

- the extractor has a locked nine-run core panel
- the newer `v69` seeds were checked only as a wider falsification read

That was good enough for the first review, but it is not the right long-term
shape. If fresh pressure seeds remain only in planning prose, the next review
will keep getting stuck on:

- which seeds are actually in the benchmark?
- which results are harness-backed?
- what exactly does no-drift mean?

So the next step is not another dump rule. It is:

1. formalize the review panels in code
2. freeze both target contracts in tests
3. do the no-drift transparency hardening pass on top of that structure

## Frozen panel contracts

### Core benchmark panel

Ordered seed contract:

- `511`
- `411`
- `611`
- `711`
- `811`
- `911`
- `1011`
- `1111`
- `1211`

Role:

- continuity
- benchmark sanity
- fixed no-drift reference

### Pressure falsification panel

Ordered seed contract:

- `1311`
- `1411`
- `1511`

Role:

- broader falsification pressure
- false-positive detection
- anti-overfitting check

### No-drift expectations

Core panel must preserve current top-line verdicts:

- `511` dumps
- `411` dumps
- `611` dumps
- `711` dumps
- `1011` dumps
- `811`, `911`, `1211` stay quiet
- `1111` still misses
- `would_stop` stays separate from `would_dump`

Pressure panel must preserve current wider falsification read:

- `1311` would dump under the trust-led branch
- `1411` would dump under the archive-uplift branch
- `1511` stays quiet

## Implementation order

1. Freeze panel target contracts in tests.
2. Split current review targets into:
   - `CORE_PANEL_TARGETS`
   - `PRESSURE_PANEL_TARGETS`
3. Pass `target_panel_name`, `target_panel_role`, `target_label`, and
   `target_order` through row/run outputs.
4. Replace implicit panel discovery with explicit review-target discovery.
5. Add the transparency helpers:
   - deterministic rule iterators
   - signed-margin helpers
   - explicit dump-rule evaluation
   - explicit continuation-rule evaluation
   - full threshold matrix rows
   - nearest-pass selection
6. Keep current verdicts unchanged while adding:
   - threshold matrix outputs
   - gate margins
   - seed digests
   - family digests
7. Split markdown summaries by panel:
   - core benchmark
   - pressure falsification
   - combined caution note

## Explicit non-goals

Do not change:

- live solver behaviour
- threshold tuples
- `SCORE_PANEL_DISABLE_FAMILY_STOP`
- replay scoring
- family clustering
- candidate row collection
- current dump verdict semantics

Do not silently move future fresh seeds into either frozen panel.

## Expected deliverables

Existing outputs retained:

- `row_scores.jsonl`
- `run_shadow_summary.jsonl`
- `threshold_sweep_summary.json`
- `data_gap_report.json`
- `summary.md`

Additional outputs:

- `threshold_matrix_rows.jsonl`
- `threshold_matrix_summary.json`
- `gate_margin_rows.jsonl`
- `seed_gate_digest.jsonl`
- `seed_gate_digest.md`
- `family_gate_digest.jsonl`
- `family_gate_digest.md`

All new outputs should carry panel metadata where relevant.

## Decision after this pass

Only after the panel split and no-drift transparency pass are in place should
we decide between:

- another offline dump axis
- or a taxonomy / falsification validation pass

Until then, the stop project should remain:

- offline-only
- dump-led
- stop-shadow-only

## Progress note

Completed so far:

- frozen core / pressure review-panel split implemented in the extractor
- panel metadata now threaded through row/run outputs
- panel-split `summary.md` implemented
- explicit dump-rule iterator implemented
- explicit continuation-rule iterator implemented
- signed margin helpers implemented
- explicit gate evaluation helpers implemented
- threshold-matrix rows now emitted
- nearest-pass diagnostics now emitted

Current verified bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/20260408T024804Z__score_stop_shadow_v2/`

Current verified state:

- core panel verdicts unchanged
- pressure panel verdicts unchanged
- next remaining work is reviewer-facing digest/reporting polish, not
  behavioural repair

### 2026-04-08 score_stop_shadow_v2 explanation layer landed

Implemented the explanation-only pass on top of the split-plus-transparency
bundle:

- fixed case-study seeds:
  - `1111`
  - `1311`
  - `1411`
- deterministic selectors for:
  - best truth row
  - best trust row
  - best uplift row
  - best archive uplift row
  - current firing row
- new outputs:
  - `case_explanations.jsonl`
  - `case_explanation_summary.json`
  - `case_explanations.md`

Validation:

- `tests/tools/test_no_wli_score_stop_shadow_v2.py`
  - `42 passed`
- `py_compile` clean

Fresh extractor output:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/20260408T142942Z__score_stop_shadow_v2/`

Readout:

- `1111`
  - `accepted_miss_outside_current_model`
- `1311`
  - `trust_false_fire`
- `1411`
  - `archive_false_fire`

Interpretation:

- the stop bundle is now explainable without changing any verdicts
- next move is external review of the explanation outputs, not more structural
  refactoring
- nearest-pass output contract is now clearer:
  - `shadow_nearest_pass_margin` is signed
  - `shadow_nearest_pass_deficit` is the positive failure magnitude
  - the markdown now prints both as `signed_margin` and `deficit`

### 2026-04-08 stop harness frozen; late_family_quality_v1 started from frozen bundle

The stop transparency pass is now complete enough to treat
`score_stop_shadow_v2` as a frozen benchmark/explanation input.

Next study branch:

- `tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v1/`

Frozen input:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/20260408T041415Z__score_stop_shadow_v2/`

First real output:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v1/20260408T152322Z__late_family_quality_v1/`

First read:

- `1111`
  - accepted miss family looks real
- `1311`
  - trust false-fire family looks weak
- `1411`
  - archive false-fire family looks weak
- reference wins still split across truth/trust/uplift families, so this is
  promising but not yet a clean promoted score-head result
- small v1.1 cleanup also landed:
  - markdown winner tables now show metric-appropriate values and trends
  - optional threshold-matrix read is now explicitly documented as future-use
    scaffolding rather than accidental dead code

So the stop harness should now stay frozen except for bug/contract fixes, and
the next real question is whether external review agrees that the family-level
read is strong enough to justify a separate offline family-quality score head.
