# PhaseB Span-Hamming Multiscore Review And Coherence Next Plan - 2026-05-14

## What changed

Reviewed the multiscore span-Hamming hard-pair report and added the next
report-only active plan.

Review note:

- `planning/projects/no_wli/40_review_summaries/phaseB_span_hamming_multiscore_hard_pair_report_v1_review_note_2026-05-14.md`

Next plan:

- `planning/projects/no_wli/20_active_plans/phaseB_order_phrase_ngram_coherence_hard_pair_report_v1_plan_2026-05-14.md`

## Why it matters

The multiscore report found one genuinely promising span-Hamming rung, but broad
span-Hamming-only scoring still breaks too many current-correct pairs.

Best individual row:

- `phaseA14_normal_selected`
- length `7`
- HD `2`
- `exact_count_norm`
- truth preference `0.776`
- rescues `286`
- breaks `234`
- net `+52`

Best broad score:

- `S5_local_null_positive_selected`
- truth preference `0.739`
- rescues `210`
- breaks `284`
- net `-74`

## Next step

Implement a report-only order/phrase/ngram coherence hard-pair report using the
same `2594` pairs and existing candidate text/token renderings.

## What did not change

- Data-taking remains paused.
- No production scoring policy changes are authorized.
- Stage 4 and calibration outputs remain untouched.

## Coherence implementation update

Implemented and ran:

```text
tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_order_phrase_ngram_coherence_hard_pair_report_v1.py
```

Output:

```text
output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_order_phrase_ngram_coherence_hard_pair_report_v1
```

Review pack:

```text
planning/projects/no_wli/40_review_summaries/phaseB_order_phrase_ngram_coherence_hard_pair_report_v1_review_pack_2026-05-14.zip
```

Review note:

```text
planning/projects/no_wli/40_review_summaries/phaseB_order_phrase_ngram_coherence_hard_pair_report_v1_review_note_2026-05-14.md
```

Key result:

- `C7_len7_hd2_exact_support_plus_coherence`: truth preference `0.786`,
  rescues `330`, breaks `284`, net `+46`
- `C8_span_plus_coherence_conservative`: rescues `64`, breaks `0`, net `+64`
- coherence composite suppresses `248 / 362` Panel A breaks and `226 / 284` S5
  breaks

## Closeout / successor

The span-Hamming multiscore review and simple proxy coherence follow-up are now
closed as prior evidence layers.

Successor active plan:

- `planning/projects/no_wli/20_active_plans/phaseB_filtered_ngram_hard_pair_report_v1_plan_2026-05-14.md`

The successor asks whether true filtered strict/normal n-gram evidence can beat,
match, or explain the simple coherence proxy. It remains report-only and uses
the existing sample-mode filtered n-gram assets.
