# PhaseB Order/Phrase/Ngram Coherence Hard-Pair Report v1 Review Note - 2026-05-14

## Question

Can simple order/phrase/ngram coherence preserve span-Hamming rescues while
suppressing span-Hamming breaks on the same `2594` hard pairs?

## Inputs Reviewed

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_order_phrase_ngram_coherence_hard_pair_report_v1/readout.md`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_order_phrase_ngram_coherence_hard_pair_report_v1/score_family_pairwise_summary.csv`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_order_phrase_ngram_coherence_hard_pair_report_v1/coherence_vs_span_hamming_rescue_break_summary.csv`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_order_phrase_ngram_coherence_hard_pair_report_v1/pairwise_score_gaps.csv.gz`

Review pack:

- `planning/projects/no_wli/40_review_summaries/phaseB_order_phrase_ngram_coherence_hard_pair_report_v1_review_pack_2026-05-14.zip`

## Run Facts

- candidates: `604`
- pairs: `2594`
- elapsed: about `13s`
- output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_order_phrase_ngram_coherence_hard_pair_report_v1`

No calibration/data-taking was launched.
No production scorer weights, defaults, or ranking policy were changed.

## Headline Result

The coherence report gives a positive answer.

Simple auditable coherence features reduce the span-Hamming break problem, and
the best combined report-only score improves over the current broad span-Hamming
scores.

Best broad combined family:

- `C7_len7_hd2_exact_support_plus_coherence`
- truth preference: `2038 / 2594` (`0.786`)
- rescues: `330`
- breaks: `284`
- net: `+46`

Best conservative support family:

- `C8_span_plus_coherence_conservative`
- applied count: `1212`
- rescues: `64`
- breaks: `0`
- net: `+64`

This is the first report-only result in this thread that gives positive net
rescues at broad or meaningful support coverage without changing production
policy.

## Coherence-Only Behavior

Coherence-only is useful but not enough as a broad chooser:

- `C1_char_ngram_coherence`
  - truth preference `0.683`
  - rescues `276`
  - breaks `474`
  - net `-198`
- `C2_phrase_or_ngram_coherence_if_available`
  - truth preference `0.625`
  - rescues `348`
  - breaks `720`
  - net `-372`
- `C3_repetition_penalty`
  - truth preference `0.490`
  - rescues `206`
  - breaks `924`
  - net `-718`

Interpretation:

- coherence alone is not a final chooser
- coherence has useful independent shape as a suppressor/support term
- repetition by itself is too blunt

## Span-Hamming Break Suppression

Using the `coherence_composite` gap:

Panel A cases:

- Panel A rescues preserved: `198 / 274`
- Panel A breaks suppressed: `248 / 362`

S5 cases:

- S5 rescues preserved: `148 / 210`
- S5 breaks suppressed: `226 / 284`

This directly answers the report question: coherence does reduce the
span-Hamming break problem.

## Correlation / Independence Check

The simple coherence and combined scores are still correlated with existing
signals:

- `C1_char_ngram_coherence`
  - correlation with current margin: `0.759`
  - correlation with Panel A margin: `0.677`
  - correlation with S5 margin: `0.628`
- `C7_len7_hd2_exact_support_plus_coherence`
  - correlation with current margin: `0.878`
  - correlation with Panel A margin: `0.917`
  - correlation with S5 margin: `0.903`

Interpretation:

- this is not an entirely independent evidence source
- it still adds enough shape to improve rescue/break accounting
- a later held-out simulation should treat correlation carefully

## Decision

Do not change production scorer policy yet.

Do not restart calibration/data-taking.

Promote the following report-only result for the next review step:

- `C7_len7_hd2_exact_support_plus_coherence` as the best broad combined candidate
- `C8_span_plus_coherence_conservative` as the best zero-break support policy
- `coherence_composite` as a useful suppressor of span-Hamming breaks

## Recommended Next Step

Build a compact review pack / external-review note around:

- Panel A baseline
- S5 span-Hamming selected score
- length-7-HD2 exact support
- coherence composite
- C7 broad combined result
- C8 conservative support result

The next implementation step, if any, should be a held-out or source-family split
simulation of the combined features, not more feature invention and not
production integration.

