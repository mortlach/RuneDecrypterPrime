# `score_stop_shadow_v2` first family-panel readout

## Scope

Tiny modern offline panel:

- solved control: `p5/c1 seed511`
- selector-sensitive hard win: `p9/c3 seed411`
- selector-neutral hard win: `p9/c3 seed1011`
- selector-sensitive reject / no-lift: `p9/c3 seed811`
- selector-neutral reject / no-lift: `p9/c3 seed911`

Output:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/20260406T151959Z__score_stop_shadow_v2/`

## Main result

The family-aware dump layer is now stronger and still conservative.

- trust-led dump rule:
  - `trust0.30_xent24.00_margin0.00_support1`
- archive-uplift fallback:
  - `archive_search_uplift0.15`
- the current panel now fires on:
  - solved control `seed511`
  - selector-neutral hard win `seed1011`
  - selector-sensitive hard win `seed411`
- it still does not fire on:
  - selector-sensitive reject `seed811`
  - selector-neutral reject `seed911`
- no shadow stop fires on this panel

## Row-level contrast

The biggest difference is not family support yet. It is trust.

- `seed411` top late rows stay low-trust:
  - best observed trust around `0.083`
  - xent around `20.0`
- `seed1011` late winning rows reach:
  - trust around `0.321`
  - xent around `17.498`
- `seed811` reject rows get closer but still stay below the current trust floor:
  - trust around `0.292`
- `seed911` remains well below the trust floor

## Current read

- this is now a more plausible **dump** layer
- the trust-led rule still favors high-trust/clean-text late wins
- the new archive-uplift fallback catches the selector-sensitive `411` rescue
  shape without lowering trust
- the stop side remains stricter and appropriately inactive

## Miss-analysis update

The rerun with persisted non-firing diagnostics makes the main blocker clearer.

- `411`:
  - positive rival-family margin
  - but trust remains very low
  - and family support stays at `0`
- `811`:
  - also has positive rival-family margin
  - trust is much closer to the floor than `411`
  - but family support also stays at `0`

That led to the current widening:

- `411` is not missing because of rival-family weakness
- lowering trust alone still looks unsafe, because it is more likely to wake
  `811` than to rescue `411`
- so the widening was moved to a narrow non-oracle continuation-style axis:
  same-family archive search uplift versus `phaseC_start`

## Persistence-axis update

Late-family persistence is now persisted for every row, and the first read is
useful but negative as a discriminator.

- dominant-family persistence is broad:
  - `411`
  - `811`
  - `911`
  - `1011`
  all show a family that survives from `phaseC_start` through `stage35_archive`
- the non-anchor override-family signal is also not enough by itself:
  - `411` rescue family persists across `phaseC_start -> stage35_seed`
  - `811` override family also persists across `phaseC_start -> stage35_seed`

So:

- persistence is worth keeping as a diagnostic
- but persistence alone is too broad to become the next dump rule

## Archive-uplift update

The new fallback rule is intentionally narrow:

- boundary:
  - `stage35_archive` only
- signal:
  - same-family `replay_search_score` uplift versus the family's
    `phaseC_start` baseline
- threshold:
  - `+0.15`

Current panel behavior:

- `411`
  - archive family uplift about `+0.234`
  - rule fires
- `1011`
  - archive uplift near zero / slightly negative
  - still covered by the trust-led rule instead
- `811`
  - no archive-uplift trigger
- `911`
  - no archive-uplift trigger

So the new rule looks like a real rescue-style dump aid, but it is still only
proven on the tiny panel.

## Broader existing hard-panel check

Using the finished mapped hard-seed artifacts only, with no new live runs:

- dump fires on:
  - `411`
  - `611`
  - `711`
  - `1011`
- dump stays quiet on:
  - `811`
  - `911`
  - `1211`
- accepted win `1111` still misses

So the current read is now:

- better than the original tiny-panel result
- not just a `411` one-off rescue
- still not a general hard-win detector, because `1111` remains outside it

## `1111` miss read

Compared with the selector-neutral dump hits (`611`, `711`, `1011`),
`1111` is not a near-threshold miss.

Its late winning family stays weak on every current dump axis:

- best late trust only about `0.167`
- xent flat at `20.0`
- family support `0`
- archive same-family search uplift negative:
  - about `-0.038`

So the current interpretation is:

- `1111` is not another clean trust-style late win
- it is not another `411`-style archive-uplift rescue
- any further widening now needs a genuinely new signal, not just looser
  thresholds on the current ones

## Recommendation

Next stop-science slice:

1. treat `1111` as the next discriminator case
2. keep dump and stop separate
3. keep stop shadow-only and much stricter than dump
4. do not launch more live seed runs until that broader dump read is done
