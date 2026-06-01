# PhaseB Order/Phrase/Ngram Coherence Hard-Pair Report v1 Plan - 2026-05-14

Status: closed / superseded
Work status: implemented_report_run_closed
Project: no_wli
Owner: agent
Last updated: 2026-05-14
Superseded by:
- planning/projects/no_wli/20_active_plans/phaseB_filtered_ngram_hard_pair_report_v1_plan_2026-05-14.md
Source-of-truth parents:
- planning/working/no_wli_data_taking_pause_20260514.md
- planning/working/no_wli_current_status_handoff_data_pause_20260514.md
- planning/projects/no_wli/40_review_summaries/phaseB_span_hamming_multiscore_hard_pair_report_v1_review_note_2026-05-14.md
- output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_span_hamming_multiscore_hard_pair_report_v1/readout.md

## Purpose

Build the next report-only evidence layer for the historical hard-pair set:
order, phrase, and ngram coherence.

The question is:

```text
Can order/phrase/ngram coherence preserve span-Hamming rescues while suppressing
span-Hamming breaks caused by local word-like but globally scrambled candidates?
```

This is not a production scorer change.
This is not a new calibration/data-taking run.

## Why This Is Next

The multiscore span-Hamming report showed:

- Panel A is useful local evidence but broad override net is negative:
  - rescues `274`
  - breaks `362`
  - net `-88`
- `S5_local_null_positive_selected` slightly improves broad behavior:
  - truth preference `0.739`
  - rescues `210`
  - breaks `284`
  - net `-74`
- one specific row is genuinely promising:
  - normal dictionary
  - length `7`
  - HD `2`
  - `exact_count_norm`
  - truth preference `0.776`
  - rescues `286`
  - breaks `234`
  - net `+52`
- many breaks are still local-fragment false positives.

Therefore the next missing evidence is not more local span-Hamming calibration.
It is coherence: whether fragments appear in plausible phrase/order structure.

## Inputs

Use existing hard-pair and manual-inspection outputs:

- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_span_hamming_hard_pair_road_test_v1`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_span_hamming_candidate_manual_inspection_v1`
- `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_span_hamming_multiscore_hard_pair_report_v1`

Expected files:

- `candidate_manifest_resolved.csv`
- `pairwise_road_test_summary.csv`
- `candidate_multiscore_summary.csv`
- `pairwise_score_gaps.csv.gz`
- `candidate_full_texts.jsonl.gz`
- `pair_manual_inspection.csv`

If text rows are unavailable from the manual-inspection output, rebuild text
renderings from:

- `planning/projects/no_wli/40_review_summaries/no_wli_historical_partial_text_and_scorer_review_pack_2026-05-02/historical_partial_texts/unique_partial_text_rows.csv`

## Candidate Features To Test

Start with cheap, transparent features. Do not train a complex model in v1.

Word/order-like features:

- common bigram hit rate
- common trigram hit rate
- rare/bad bigram rate
- repeated 3-gram and 4-gram rate
- run-length / repetition summary
- vowel/consonant or rune-class transition roughness if available
- word-boundary proxy consistency if a local parser exists
- phraselet count using a small hardcoded list of common English fragments
- local fragment density versus ordered-fragment density

Span-Hamming carry-forward features:

- Panel A
- Panel D
- `S5_local_null_positive_selected`
- normal length `7`, HD `2`, `exact_count_norm`

## Evaluation

Use the same `2594` hard pairs.

For every coherence score and combined score, report:

- truth-better preference count/rate
- binomial 95% CI
- rescues
- breaks
- net rescues
- current-scorer correct/misrank splits
- margin sweeps
- performance on span-Hamming rescues
- performance on span-Hamming breaks
- top rescued pairs
- top avoided-break pairs
- top remaining breaks

## Combined Report-Only Score Families

Suggested transparent variants:

- C0: current scorer baseline
- C1: phrase/ngram coherence only
- C2: repetition penalty only
- C3: Panel A plus coherence support
- C4: S5 plus coherence support
- C5: length-7-HD2 exact span-Hamming plus coherence support
- C6: current-margin support using coherence only
- C7: current-margin support using span-Hamming plus coherence
- C8: anti-break conservative rule requiring both span-Hamming support and
  coherence support

All score definitions must be saved to `score_definition_manifest.json`.

## Output Folder

Write outputs to:

```text
output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_order_phrase_ngram_coherence_hard_pair_report_v1
```

Required outputs:

- `config.json`
- `input_manifest.json`
- `score_definition_manifest.json`
- `candidate_coherence_summary.csv`
- `pairwise_coherence_summary.csv`
- `score_family_pairwise_summary.csv`
- `score_family_margin_sweep.csv`
- `span_hamming_rescue_break_coherence_audit.csv`
- `top_rescues_by_score.csv`
- `top_breaks_by_score.csv`
- `top_avoided_span_hamming_breaks.csv`
- `readout.md`

## Readout Questions

`readout.md` must answer:

- Does coherence separate span-Hamming rescues from span-Hamming breaks?
- Does any coherence-only score beat Panel A or S5?
- Does any combined score give positive net rescues at useful coverage?
- Which features suppress local-word false positives?
- Is the best use of span-Hamming override, support, or diagnostic?
- Is there enough evidence for a later held-out scorer simulation?

## Guardrails

- Keep the work report-only.
- Do not use CLI arguments; use hardcoded constants.
- Resolve repo root from script location.
- Keep output paths repo-relative.
- Do not change production scorer weights/defaults/ranking policy.
- Do not launch new calibration/data-taking.
- Do not use REV data in FWD evaluation.

## Success Criteria

A strong result would show:

- span-Hamming rescues mostly keep positive coherence
- span-Hamming breaks mostly show weaker coherence or stronger repetition/order
  warnings
- a combined report-only score produces positive net rescues with meaningful
  coverage

A still useful result would show:

- coherence flags many false-positive local-word candidates
- no broad override is safe yet
- the next step should be a held-out combined-feature simulation, not more
  span-Hamming calibration

## Implementation Status - 2026-05-14

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

Run facts:

- candidates: `604`
- hard pairs: `2594`
- elapsed: about `13s`

Initial result:

- `C7_len7_hd2_exact_support_plus_coherence`
  - truth preference `2038 / 2594` (`0.786`)
  - rescues `330`
  - breaks `284`
  - net `+46`
- `C8_span_plus_coherence_conservative`
  - applied count `1212`
  - rescues `64`
  - breaks `0`
  - net `+64`
- `coherence_composite`
  - preserves `198 / 274` Panel A rescues
  - suppresses `248 / 362` Panel A breaks
  - preserves `148 / 210` S5 rescues
  - suppresses `226 / 284` S5 breaks

Conclusion:

- simple coherence features do reduce the span-Hamming break problem
- this remains report-only
- this proxy-coherence line is closed as the prior evidence layer
- next step is the true filtered n-gram hard-pair report, not production
  integration

## Closeout - 2026-05-14

This plan is closed as implemented and superseded.

The report answered the proxy/order-coherence question well enough to justify a
more direct filtered n-gram test:

- proxy coherence gave a positive combined support result
- conservative support produced zero-break net-positive behavior on this
  hard-pair set
- the remaining question is whether true filtered phrase/ngram evidence can
  beat, match, or explain that proxy result

Carry-forward plan:

- planning/projects/no_wli/20_active_plans/phaseB_filtered_ngram_hard_pair_report_v1_plan_2026-05-14.md

Do not reopen this proxy plan unless filtered n-gram v1 explicitly needs a
baseline rerun or a field-name compatibility fix.
