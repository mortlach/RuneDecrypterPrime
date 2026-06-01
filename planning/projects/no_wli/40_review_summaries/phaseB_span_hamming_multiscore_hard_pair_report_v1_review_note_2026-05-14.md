# PhaseB Span-Hamming Multiscore Hard-Pair Report v1 Review Note - 2026-05-14

## Question

Review the whole-ladder span-Hamming multiscore hard-pair report and decide what
the next report-only planning step should be while data-taking remains paused.

## Inputs Reviewed

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_span_hamming_multiscore_hard_pair_report_v1/readout.md`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_span_hamming_multiscore_hard_pair_report_v1/score_family_pairwise_summary.csv`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_span_hamming_multiscore_hard_pair_report_v1/score_family_margin_sweep.csv`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_span_hamming_multiscore_hard_pair_report_v1/row_efficacy_report.csv`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_span_hamming_multiscore_hard_pair_report_v1/length_summary.csv`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_span_hamming_multiscore_hard_pair_report_v1/pairwise_score_gaps.csv.gz`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_span_hamming_candidate_manual_inspection_v1/pair_manual_inspection.csv`

Review pack:

- `planning/projects/no_wli/40_review_summaries/phaseB_span_hamming_multiscore_hard_pair_report_v1_review_pack_2026-05-14.zip`

## Headline Result

The report answers the immediate question clearly:

- span-Hamming remains useful local evidence
- smarter whole-ladder scoring improves the broad baseline only slightly
- span-Hamming alone is still not safe as a broad override
- the next evidence layer should target order, phrase, and ngram coherence

Panel A baseline reproduced the previous hard-pair result:

- truth preference: `1904 / 2594` (`0.734`)
- rescues: `274`
- breaks: `362`
- net: `-88`

Best broad span-Hamming-only score:

- `S5_local_null_positive_selected`
- truth preference: `1918 / 2594` (`0.739`)
- rescues: `210`
- breaks: `284`
- net: `-74`

This is a real improvement over Panel A on broad truth preference and net, but
it remains break-heavy.

Positive-net behavior appeared only in conservative/support-policy simulations:

- `S7_current_uncertainty_support_margin_0.01`: rescues `128`, breaks `114`, net
  `+14`
- `S8_anti_break_conservative_margin_0.25`: rescues `4`, breaks `2`, net `+2`
- Panel A margin sweep at threshold `0.4`: rescues `4`, breaks `0`, net `+4`

These are useful support-signal indications, not enough for scorer-policy change.

## Individual Row Findings

The strongest individual row is important:

- dictionary: `phaseA14_normal_selected`
- length: `7`
- HD: `2`
- feature: `exact_count_norm`
- truth preference: `0.775636`
- rescues: `286`
- breaks: `234`
- net: `+52`
- local-null effect: `6.686`
- block-shuffle effect: `0.489`
- status: `core_candidate`

This row should be carried forward as a named local span-Hamming support feature.
It is the best evidence that a specific rung, not the whole ladder, carries a
useful rescue signal.

Other high-truth-preference rows are still broad-override risky:

- normal length `7`, HD `2`, `hd_le_count_norm`: truth preference `0.758`, net
  `-20`
- normal length `6`, HD `2`, `exact_count_norm`: truth preference `0.745`, net
  `-54`
- normal length `6`, HD `1`, `hd_le_count_norm`: truth preference `0.742`, net
  `-40`
- normal length `5`, HD `1`, `hd_le_count_norm`: truth preference `0.736`, net
  `-74`

Worst break-heavy rows are mostly longer or relaxed HD rows:

- normal length `12`, HD `5`, `exact_count_norm`: net `-808`
- strict length `10`, HD `3`, `exact_count_norm`: net `-790`
- normal length `10`, HD `3`, `exact_count_norm`: net `-788`
- normal length `9`, HD `2`, `exact_count_norm`: net `-772`

Interpretation:

- lengths `5..7` contain the useful local evidence
- length `7` HD `2` exact evidence is the strongest single rung
- longer spans and relaxed HD rows are not currently useful as broad chooser
  evidence
- strict evidence is not a standalone fix; it remains possible precision/support
  metadata

## Pair-Level Inspection

Manual joined examples show the same pattern in both rescues and breaks:

- both sides often contain local English-like fragments
- rescues happen when local fragments are genuinely better in the truth-better
  candidate
- breaks happen when the truth-worse candidate has stronger local fragments even
  though the global candidate is worse
- many cases are exactly the expected failure mode for span-Hamming: local words
  without reliable order/coherence

Example S5 rescue pattern:

- current margin is slightly against the truth-better candidate
- truth-better snippet contains many local fragments such as `THE`, `SHE`, `OF`,
  `TO`, `THAT`, `WHEN`
- truth-worse also has fragments, but weaker or more scrambled

Example S5 break pattern:

- current scorer is correct
- span-Hamming prefers the truth-worse candidate because it has stronger local
  word-like fragments
- the snippets still look globally disordered, so a phrase/order layer should
  be able to reject some of these breaks

## Metric Caveats

- `length_summary.csv` sums rescues/breaks across many row families, so its net
  values are a row-family diagnostic, not a direct policy outcome.
- S7/S8 rows in `score_family_pairwise_summary.csv` are support-policy
  simulations. Their truth-preference rates count only applied preferences over
  the full pair denominator, so they should be read with coverage in mind.
- `score_family_margin_sweep.csv` is most useful for the base broad score
  families; S7/S8 already encode policy thresholds and should not be
  overinterpreted in the same sweep table.
- Hard-pair candidate feature rows cover lengths `5..14`; lengths `2..4` are
  not available for hard-pair scoring in this report.

## Decision

Do not tune additional span-Hamming-only weights right now.

Do not change production scorer weights, defaults, or ranking policy.

Do not resume calibration/data-taking.

Promote the following as report-only inputs to the next coherence plan:

- Panel A baseline
- `S5_local_null_positive_selected`
- named rung: normal length `7`, HD `2`, `exact_count_norm`
- conservative/support policy examples:
  - Panel A threshold `0.4`
  - `S7` current-margin support at `0.01`
  - `S8` conservative span margin `0.25`

## Next Plan

Build a report-only order/phrase/ngram coherence hard-pair report over the same
`2594` pairs and candidate token streams.

The next report should test whether a global/local order-coherence feature layer
can:

- preserve the span-Hamming rescues
- suppress span-Hamming breaks
- identify local-word but globally scrambled candidates
- combine transparently with Panel A / S5 / length-7-HD2 exact support

This should be evaluated with the same rescue/break accounting and should not
change production scoring policy.

