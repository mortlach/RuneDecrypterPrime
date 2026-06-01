# Span-Hamming Stage 2 Fixed-500 Summary - 2026-05-03

## Complete Evidence

- Fixed-500 normalized full scan completed:
  - output: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/span_hamming_500_normalized_full_v1`
  - coverage: 604 token hashes, 1812 chunks, 2594 pairs, 5 configs, 9060 scores
  - elapsed: about 322 seconds
  - parity failures: 0
  - strongest simple feature: strict-selected middle chunk short-fuzzy-noise lower, net +84
  - strongest useful interpretation: medium/long span evidence is only useful relative to short fuzzy noise.

- Stage 2 composite sweep over saved fixed-500 rows completed:
  - output: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/span_hamming_500_composite_rules_v1`
  - coverage: 1440 config/rule/aggregator rows
  - elapsed: about 9 seconds
  - strongest overall row: `strict_selected_len3_14_hd2_cap256_norm500`, middle chunk, `err20_exact5_minus_noise_lam1p0`, 506 rescues / 354 breaks, net +152
  - caveat: diagnostic split by fixture seed is unstable; the same top row is positive on odd-seed fixtures and negative on even-seed fixtures.

- Fixed-500 len-8 HD bucket canary completed:
  - output: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/span_hamming_500_len8_hd_buckets_canary_v1`
  - coverage: 80 token hashes, 720 scores, 3 configs
  - elapsed: about 24 seconds
  - canary projected the full run at about 5 minutes.

- Fixed-500 len-8 HD bucket full scan completed:
  - output: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/span_hamming_500_len8_hd_buckets_full_v1`
  - coverage: 604 token hashes, 1812 chunks, 5 configs, 9060 scores
  - elapsed: about 341 seconds
  - strongest pair rows are weak: exact len-8 HD0 lower on suffix gives only 10 rescues / 2 breaks, net +8, with 2558 ties.
  - most len-8 HD bucket counts are not useful as direct pairwise rules on the full data.
  - high-HD len-8 bucket interpretation is cap-limited: candidate-cap-pruned rates are about 0.88-0.91 with cap256.

- Fixed-500 length/HD fingerprint canary completed:
  - output: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/span_hamming_500_length_hd_fingerprint_canary_v1`
  - coverage: 80 token hashes, 240 chunks, 1200 per-length scores
  - configuration: strict selected dictionary, lengths 6-10, max_hd = length - 3, cap100000
  - elapsed: about 108 seconds
  - cap-prune rates: 0 for all scored lengths/chunks
  - canary top row was strong but did not fully survive full-data widening.

- Fixed-500 length/HD fingerprint full strict-selected pass completed:
  - output: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/span_hamming_500_length_hd_fingerprint_full_v1`
  - coverage: 604 token hashes, 1812 chunks, 9060 per-length scores
  - configuration: strict selected dictionary, lengths 6-10, max_hd = length - 3, cap100000
  - elapsed: about 846 seconds
  - cap-prune rates: 0 for all lengths/chunks, so the fingerprint is not cap-shaped
  - strongest rows are modest: suffix raw len8 matched-window mass net +58; middle selected exact fingerprint net +56; prefix selected len6 exact net +50.
  - raw matched-window mass is nearly saturated, about 0.999, so most of the useful signal is in distribution shape/exactness rather than whether a window matches at all.

- Fixed-500 fingerprint + noise composite sweep completed:
  - output: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/span_hamming_500_fingerprint_noise_composites_v1`
  - inputs: saved normalized full rows plus uncapped fingerprint full rows
  - coverage: 1812 joined candidate rows, 384 rule/aggregator rows, 2594 pairs
  - elapsed: about 4 seconds
  - features are z-scored per chunk before composition
  - strongest row: `selected_exact_span_minus_noise_lam0p75`, middle chunk, 470 rescues / 246 breaks, net +224
  - broad diagnostic splits for that row are positive: margin >=0.01 net +156, margin <0.01 net +68, seed_7000s net +82, seed_x11 net +142
  - seed parity remains unstable: even fixture seeds net -50, odd fixture seeds net +274

- Word-ngram data/model inspection completed:
  - live default discovery points to `output/tools/benchmarks/scoring/word_ngrams_sqlite_assets/20260308T024914Z__build_word_ngram_sqlite_asset_phase2_v1/word_ngrams_tokenized64_phase2_v1.sqlite`
  - the default asset is not the raw Google ngram builder output; it is the phase2 tokenized-PG SQLite built from 64 hashed-selected books out of 512 `assets_packed/tokenized_pg/*_fwd.npz` books
  - model coverage: about 2.69M distinct 3-grams, 3.54M distinct 4-grams, 3.78M distinct 5-grams, with about 3.89M total events per order
  - report extraction scores exact HD0 span-Hamming selected intervals only, segmented into adjacent rune-token word sequences
  - activation is gated by `word_ngram_judge_min_positions`; default is 12, many lexical Phase-C presets force 6
  - the current scorer-component audit has word-ngram available for 604/604 candidates but active for only 333/604 at the default threshold, so inactive must be treated as missing/no-decision evidence, not as bad-language evidence
  - a threshold probe on saved candidate rows shows active candidates would be 548/604 at min_positions=6, but direct xent/miss signals get worse at lower thresholds; support/trust-style evidence remains cleaner
  - raw-exact interval extraction was checked on an 80-row canary and did not improve word-ngram positions versus the selected exact intervals; it slightly reduced mean positions, so simply feeding all exact raw intervals is not an obvious improvement

- Fixed-500 fingerprint + noise + word-ngram report-only sweep completed:
  - output: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/span_hamming_500_fingerprint_noise_word_ngram_composites_v1`
  - inputs: saved fingerprint/noise joined rows plus `scorer_component_feature_audit_v1` word-ngram candidate features
  - coverage: 1812 joined candidate rows, 2594 pairs, 4550 rule/aggregator rows
  - elapsed: about 36 seconds
  - strongest row: `selected_exact_span_noise_plus_word_ngram_trust_lam0p75_w0p25`, middle chunk, 468 rescues / 214 breaks, net +254
  - this improves over the prior span-only composite net +224, mostly by reducing breaks
  - seed parity remains unstable: even fixture seeds net -50, odd fixture seeds net +304

- Word-ngram support-threshold audit completed:
  - output: `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/word_ngram_support_thresholds_v1`
  - coverage: 604 candidate token hashes, 2594 pairs, 63 feature/threshold rows
  - elapsed: about 56 seconds after fixing the interval-object handoff
  - this is report-only; runtime behaviour was not changed
  - uses `FastSpanHammingBackend` for selected interval extraction, so it also acts as a lightweight-path timing canary: about 604 candidate lexical reports in 56 seconds, compared with the earlier slow-path profile of 32 lexical calls in about 73 seconds
  - activation by min_positions: 1 => 604/604, 3 => 597/604, 6 => 548/604, 9 => 443/604, 12 => 333/604, 18 => 172/604, 24 => 90/604
  - strongest direct row is `n_positions` at min_positions 12: 94 rescues / 6 breaks, net +88
  - strongest support/trust-style rows are also at min_positions 12: `support_ge1_ge10_ge100` net +36, `support_ge100_only` net +30, `support_ge10_ge100` net +28
  - min_positions 18 is cleaner but smaller: top rows have 18-20 rescues and 0 breaks
  - raw xent/miss-rate does not currently add direct pairwise value in this audit
  - split caveat remains strong: the top min_positions 12 row is even-seed net 0 and odd-seed net +88

## Working Read

- Stage 2 is not pointing at a single pure len-8 count gate.
- The better signal is composite: reward normalized medium/long approximate span support, penalize short fuzzy noise, and keep the 500-token chunk fixed.
- The current best composite is promising enough for a report-only Stage 2 candidate, but not yet stable enough to promote into runtime scoring without a proper holdout or grouped validation.
- Policy cuts did not materially differentiate the len-8 bucket diagnostic for selected dictionaries; raw-all differs mostly through cap pressure and timing.
- Uncapped length/HD fingerprints are feasible for report-only analysis, but the first full pass suggests they are diagnostic shape features rather than a standalone gate.
- Combining fingerprint shape with span evidence and short-noise penalty improves the best overall net from +152 to +224, but does not solve the fixture-seed instability.
- Adding word-ngram trust improves the best report-only pairwise net from +224 to +254, but it still does not solve the even-seed counter-signal.
- Word-ngram is a joint-probability side channel over exact selected word-token sequences. It is not a replacement for span-Hamming and should not be promoted as a hard lexical gate from this evidence.
- Word-ngram support evidence is more useful than raw xent/miss-rate, and min_positions 12 remains the best direct threshold in the saved historical pairs.
- The most plausible remaining module improvement is a faster lightweight extraction path plus grouped validation, not raw xent scoring.

## Planned / Not Complete

- Add grouped validation for the composite candidates beyond the current simple even/odd seed split.
- Check whether the even-seed instability is a fixture-family issue rather than a true rule failure.
- Inspect the even-seed negative groups to decide whether they represent a fixture-family artifact, a repeated-pattern confound, or a real counter-signal.
- If promoting Stage 2 later, use the fixed-500 composite as a secondary tie-breaker or diagnostic first, not a hard gate.
- The broad robust composite sweep attempt timed out before producing completed evidence; it is not counted.
- Word-ngram active/inactive handling still needs a stricter joint validation pass before any decision-influencing use.
- Completed from the prior planned word-ngram checks: prefix-support fields were added to the report-only audit, min-position/support thresholds were swept, and a report-only FastSpanHamming-backed lexical extraction path was timed.
- Still planned / not complete: compare the 64-book asset against a wider tokenized-book asset and validate any lexical tie-break jointly with span/fingerprint features before changing Phase-C budgets.
- Asset check note: no wider word-ngram SQLite is currently present under `output/tools/benchmarks/scoring/word_ngrams_sqlite_assets`; only the 64-book phase2 SQLite exists. Building a wider asset is a new runtime class and should start with a canary/budget, not a blind full build.
