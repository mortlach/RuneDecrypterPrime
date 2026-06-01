# Late Family Quality v3 First Read

## Inputs

- v1:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v1/20260408T152322Z__late_family_quality_v1/`
- v2:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v2/20260408T154637Z__late_family_quality_v2/`
- v3:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/late_family_quality_v3/20260408T162219Z__late_family_quality_v3/`

## Main read

- `1111`
  - `accepted_miss_reference_like`
- `411`
  - `reference_like_strong`
- `611`
  - `reference_like_strong`
- `1011`
  - `pattern_only_reference_like_but_strength_weak`
- `1311`
  - `inconclusive`
- `1411`
  - `inconclusive`

## What changed relative to v2

- `1111` is now stronger:
  - not only pattern-reference-like
  - also strength-compatible with the win side
- `1011` is now weaker:
  - pattern-reference-like
  - but truth-family strength is weak
- `1311` and `1411` do not sharpen into the hoped-for suspicious labels under
  the strict v3 truth-gap rules

## Practical meaning

- the family-quality line is still useful
- but it is not moving cleanly in one direction
- it strengthens the accepted-miss side more than the false-fire side
- it also makes the reference-win side less uniform than v2 alone suggested

## Recommendation

- freeze `late_family_quality_v3` here
- use v1 + v2 + v3 together in the next external review
- do not spec a promoted family-quality head from this read alone
