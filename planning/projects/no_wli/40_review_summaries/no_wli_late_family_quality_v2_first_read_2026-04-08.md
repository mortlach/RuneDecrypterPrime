# Late Family Quality v2 First Read

## Inputs

- frozen family-quality v1 bundle:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v1/20260408T152322Z__late_family_quality_v1/`
- first v2 output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v2/20260408T154637Z__late_family_quality_v2/`

## Main pattern read

- shared acceptable pattern:
  - `A-A-B-A-A`
    - `611`
    - `1111`
- discriminator-only suspicious patterns:
  - `A-B-B-A-A`
    - `1311`
  - `A-B-A-B-B`
    - `1411`
- reference-only acceptable patterns:
  - `A-B-A-A-A`
    - `411`
  - `A-B-B-B-B`
    - `1011`

## What that means

- `1111` is no longer just a family-level “looks real” case
- it now matches one real-win split pattern exactly:
  - `611`
- the two false-fire seeds do not match any reference-win pattern
- that makes the family-quality line stronger as an explanatory discriminator

## Remaining limit

- the win side still spans three distinct acceptable patterns, not one
- so this is still not enough to justify one simple promoted family-quality
  head

## Recommendation

- freeze `late_family_quality_v2` after this first pass
- use it in the next external review
- only spec a narrower v3 or a score-head experiment if review agrees that the
  new pattern split is materially stronger than the v1 family-quality read
