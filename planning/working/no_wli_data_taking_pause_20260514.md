# No-WLI Data-Taking Pause - 2026-05-14

Decision:

- Pause new calibration/data-taking runs for now.
- Do not launch another Stage 4 continuation, Stage 5 calibration, PCA run, PCB run,
  or any other multi-hour no-WLI data-taking job by default.
- The pause may be lifted later if downstream tests, road-test refreshes, or reviewer
  questions identify a specific data gap that materially affects the next decision.

Current calibration/data status:

- Stage 1:
  - completed earlier PCB FWD/full calibration baseline.
- Stage 2:
  - completed PCB FWD/full len2-14 continuation.
- Stage 3:
  - completed PCB FWD/full len5-14 continuation.
  - output:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/stage3_fwd_full_len5_14_pcb`
  - review pack:
    - `planning/projects/no_wli/40_review_summaries/stage3_fwd_full_len5_14_pcb_review_pack_2026-05-13.zip`
- Stage 4:
  - completed PCB FWD/full len8-14 continuation.
  - output:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/stage4_fwd_full_len8_14_pcb`
  - review analysis:
    - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/stage4_fwd_full_len8_14_pcb_review_analysis`
  - review pack:
    - `planning/projects/no_wli/40_review_summaries/stage4_fwd_full_len8_14_pcb_review_pack_2026-05-14.zip`

Stage 4 closeout facts:

- status:
  - `complete`
- clean chunks:
  - `12000`
- samples:
  - `444000`
- feature rows:
  - `35520000`
- elapsed:
  - `69326.90s`
  - `19.26h`
- observed throughput:
  - `512.36` feature rows/s
  - `6.404` samples/s
- next chunk start:
  - `34400`
- raw `feature_rows.csv`:
  - absent as intended
- histograms / quantiles:
  - written / written
- log scan:
  - no traceback, exception, warning, native command error, or unraisable-hook hits

Scientific status:

- Span-Hamming is real and useful local damaged-word evidence.
- Panel A, lengths `5..9`, is the strongest local evidence panel.
- Panel D, strict rows, adds useful precision/support evidence.
- Panel B, longer spans, is better supported after Stage 4 but remains weaker and
  should be treated as supporting evidence.
- Span-Hamming alone does not solve high-scoring gibberish or wrong-order candidates.
- The hard-pair test showed Panel A is directionally useful but not a safe standalone
  override:
  - truth-better preference `1904 / 2594` (`0.734`)
  - rescues `274`
  - breaks `362`
  - net `-88`

Current priority while paused:

1. Do not collect more calibration data unless a concrete later test shows it is
   needed.
2. Merge/refresh calibration bundles for report-only road-test use.
3. Refresh road-test Panel B with Stage 4 included.
4. Continue report-only order/phrase/ngram coherence work on the same hard-pair
   rescue/break dataset.
5. Use the manual inspection pack to understand bad candidates that local
   span-Hamming likes.

Unpause conditions:

- A reviewer or downstream test identifies a specific missing calibration slice.
- Stage 4-merged road tests show Panel B or another panel is unstable due to coverage.
- A new report-only scoring experiment needs a narrowly scoped canary that cannot be
  answered from the existing Stage 1-4 data.

If unpaused:

- write a new plan first
- declare the scientific question
- declare the exact run config
- justify runtime from retained wallclock evidence
- set a stop condition
- keep the run independently complete and as small as possible
- launch long jobs only in a separate PowerShell window with tee logs

Do-not-do list while paused:

- do not start Stage 5 calibration
- do not start PCA data collection
- do not start another PCB continuation
- do not change production scorer weights
- do not change scorer defaults or ranking policy
- do not treat Panel A as a final score
