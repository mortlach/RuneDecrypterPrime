# Late Family Quality v1 First Read

## Inputs

- frozen stop bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/20260408T041415Z__score_stop_shadow_v2/`
- first family-quality output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v1/20260408T152322Z__late_family_quality_v1/`

## Main read

- `1111`
  - family-level truth, trust, full uplift, and persistence all point at
    family `f0`
  - archive uplift points at challenger family `f1`
  - read: `accepted_miss_family_looks_real`
- `1311`
  - family-level truth, full uplift, and persistence point at family `f0`
  - trust and archive uplift point at family `f1`
  - read: `trust_false_fire_family_looks_weak`
- `1411`
  - truth and archive uplift agree on family `f1`
  - trust, full uplift, and persistence sit on `f0`
  - the truth/archive family is still weak in absolute truth terms
  - read: `archive_false_fire_family_looks_weak`

## Reference wins

- `411`
  - `truth_trust_split`
- `611`
  - `truth_uplift_split`
- `1011`
  - `truth_trust_split`

## What this means

- the family-level study adds useful discrimination on the three target seeds:
  - `1111` now looks more real than the row-level stop harness could show
  - `1311` now looks weaker than its trust-led row-level false fire suggested
  - `1411` still looks weak, but not by a simple truth-versus-uplift family
    split
- the reference wins do not collapse to one clean family-winner pattern
- so this is a useful offline study, but not yet a proof that one simple
  family-quality head should replace the current row-level stop view
- markdown case tables are now metric-correct in the v1.1 cleanup:
  - `best value` is metric-specific per row
  - trend labels now match the displayed metric
  - persistence rows now show count plus `na` trend rather than a misleading
    truth-trend carry-over

## Recommendation

- freeze the current stop harness
- use this family-quality bundle for external review
- do not add more live seeds yet
- only spec a new offline family-quality score head if review agrees that this
  new read is materially better than the stop harness alone
