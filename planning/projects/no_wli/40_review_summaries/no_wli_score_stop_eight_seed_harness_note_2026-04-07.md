# `score_stop_shadow_v2` harness-backed eight-seed readout

## Scope

Harness-backed offline panel:

- solved control: `p5/c1 seed511`
- hard seeds:
  - `411`
  - `611`
  - `711`
  - `811`
  - `911`
  - `1011`
  - `1111`
  - `1211`

Output:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/20260407T023505Z__score_stop_shadow_v2/`

## Main result

The stop harness is now broad enough that the current dump claim is
harness-backed rather than partly manual.

- trust-led dump rule:
  - `trust0.30_xent24.00_margin0.00_support1`
- archive-uplift fallback:
  - `archive_search_uplift0.15`
- dump fires on:
  - solved control `seed511`
  - selector-sensitive hard win `seed411`
  - selector-neutral hard wins `seed611`, `seed711`, and `seed1011`
- dump stays quiet on:
  - selector-sensitive reject `seed811`
  - selector-neutral rejects `seed911` and `seed1211`
- accepted hard win `seed1111` still misses
- no shadow stop fires

## What changed versus the earlier five-case read

The earlier family-panel note was directionally right, but it mixed:

- harness-backed evidence on `511`, `411`, `1011`, `811`, `911`
- broader manual read on `611`, `711`, `1111`, `1211`

That separation is no longer needed for the current main read:

- `611`, `711`, `1111`, and `1211` are now part of the hardcoded harness
- the broader dump claim is now benchmark-backed

## Current interpretation

- the dump layer is materially stronger than the original trust-only read
- archive-search-uplift is a real rescue-style dump aid for `411`
- the dump layer is still not a general hard-win detector because `1111` stays
  outside it
- stop remains correctly shadow-only and inactive

## `1111` remains the key miss

`1111` is still not a near-threshold false negative.

Current winning-family read:

- late trust only about `0.167`
- xent flat at `20.0`
- family support `0`
- same-family archive search uplift negative:
  - about `-0.038`

So:

- `1111` is not another clean trust-style late win
- it is not another `411`-style archive-uplift rescue
- the next widening should only happen if a genuinely new axis is justified

## Recommendation

Next stop-science step:

1. keep dump and stop separate
2. keep stop shadow-only
3. treat `1111` as the main discriminator case
4. do not add another dump axis until external review says there is a
   plausible way to catch `1111` without waking the reject set
