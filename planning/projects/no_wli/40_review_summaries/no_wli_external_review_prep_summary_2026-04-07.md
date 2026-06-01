# No-WLI external review prep summary

Date: 2026-04-07, updated 2026-04-08

## Purpose

This note prepares the current no-WLI state for another external review pass.

It reflects the finished eleven-seed hard panel, the formalized core/pressure
stop harness, and the new explanation-layer outputs after `v69`.

## Short version

The atlas / taxonomy project is now reviewer-useful and is the stronger of the
two active science tracks.

The stop project has improved materially, but it is still a dump-calibration
harness, not a policy candidate:

- the locked harness-backed panel still behaves cleanly
- fresh reject seeds `1311` and `1411` now create real false-positive pressure
  on the current dump branches
- accepted win `1111` still misses
- the new case bundle now makes those three stories explicit rather than only
  implicit in raw threshold rows

So the programme is in a good review state, but the stop side should still be
described conservatively.

Fresh explanation bundle:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/score_stop_shadow_v2/20260408T142942Z__score_stop_shadow_v2/`

## Current programme read

### What is now supported

1. Bounded Stage 3.5 utility is broader than the original `411` family.

Supported by:

- selector-sensitive win:
  - `411`
- selector-neutral bounded late wins:
  - `611`
  - `711`
  - `1011`
  - `1111`

2. The hard-seed space is now a real multi-shape taxonomy.

Across the finished eleven-seed panel:

- selector-sensitive win:
  - `411`
- selector-neutral bounded late wins:
  - `611`
  - `711`
  - `1011`
  - `1111`
- selector-sensitive reject / no-lift:
  - `811`
- selector-neutral reject / no-lift:
  - `911`
- selector-neutral reject with `phaseA_selected` baseline:
  - `1211`
  - `1411`
- selector-neutral reject with `phaseB_topk` baseline and moderate late truth:
  - `1311`
  - `1511`

3. The atlas / key-space map is already useful for fresh-seed taxonomy and late
   compression reading.

Fresh outputs:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/space_map_v1_atlas/20260407T235219Z__space_map_v1_atlas/`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/space_map_v1_audit/20260407T235219Z__space_map_v1_audit/`

### What is still not supported

1. Selector generality is still not proven.

The only clearly causal selector-sensitive live win remains `411`.

2. Broad solver promotion is still not justified.

The panel is still small, and the reject side is now richer than before.

3. The stop layer is still not a real stop-policy benchmark.

It remains:

- offline only
- dump-first
- stop-shadow-only
- still not robust under broader fresh-seed falsification pressure

## Stop-science read

### Harness-backed result

The locked `score_stop_shadow_v2` panel now covers:

- solved control `511`
- hard seeds `411`, `611`, `711`, `811`, `911`, `1011`, `1111`, `1211`

From that harness-backed panel:

- trust-led dump fires on:
  - `511`
  - `611`
  - `711`
  - `1011`
- archive-only same-family uplift fallback fires on:
  - `411`
- dump stays quiet on:
  - `811`
  - `911`
  - `1211`
- accepted win `1111` still misses
- no shadow stop fires

### Wider fresh-seed falsification read

The new `v69` seeds were then checked against the same current dump logic:

- `1311`
  - would dump under the trust-led branch
- `1411`
  - would dump under the archive-uplift fallback
- `1511`
  - stays quiet

So the important update is:

- the locked harness still looks clean on its target set
- but the current dump layer does not generalize cleanly to the wider
  fresh-seed panel

### `1111` read

`1111` remains the main accepted-win miss.

Compared with dump hits like `611`, `711`, and `1011`, its winning late family
stays weak on the current non-oracle axes:

- best late trust about `0.167`
- xent flat at `20.0`
- family support `0`
- archive same-family search uplift about `-0.038`

So `1111` is not:

- another clean trust-style late win
- or another `411`-style archive-uplift rescue

The explanation bundle now labels it explicitly as:

- `accepted_miss_outside_current_model`

### Pressure false-positive read

The new explanation bundle also makes the two current pressure failures easy to
state:

- `1311`
  - `trust_false_fire`
  - current trust-led dump still admits a reject-side seed under pressure
- `1411`
  - `archive_false_fire`
  - current archive-uplift rescue can prefer a lower-truth archive row at the
    archive boundary

The explanation contract is also now clearer:

- nearest-pass `signed_margin` is genuinely signed
- nearest-pass `deficit` is the positive failure amount

## Recommended reviewer questions

1. Given `1311` and `1411`, should the current dump layer now be treated as
   fully exploratory rather than "nearly ready"?
2. Is a narrow offline archive full-score branch still worth reviewing, or do
   the new false positives make that too risky?
3. Is there a better way to model accepted late wins like `1111` that do not
   show trust/support/uplift strength?

## Recommendation

My recommendation before any more live seed runs is:

1. keep the eleven-seed panel as the current taxonomy baseline
2. keep stop shadow-only
3. do not loosen trust or support floors
4. use the widened false-positive read and the new explanation bundle as part
   of the next external review
5. only consider a new offline dump axis after that review

## Bottom line

The programme is in a good review state:

- the atlas / taxonomy side is already genuinely useful
- the stop side is much better than it was
- the stop side is now explainable in a compact, reviewer-friendly way
- but the stop side is still not ready to be described as a real stop-policy
  benchmark

That is the right point to pause, review, and tighten the stop science before
doing more live seed collection.
