# No-WLI Current Status Handoff - Data-Taking Paused - 2026-05-14

This note is for a new agent picking up the no-WLI / PhaseB span-Hamming work.

## Current Decision

Calibration/data-taking is paused.

Do not launch any new multi-hour no-WLI calibration/data run unless a later
report-only test or reviewer question identifies a concrete data gap. The pause can
be lifted, but only with a new written plan, runtime justification, exact config, and
stop condition.

## Repo Rules To Remember

- Follow `AGENTS.md`.
- No CLI args for repo automation/helper scripts unless explicitly requested.
- Use hardcoded constants in scripts.
- Keep paths repo-relative where controllable.
- Long-running benchmark/investigation jobs must run in a separate PowerShell window
  with tee logs.
- Do not change production scorer weights/defaults/ranking policy from the current
  evidence.

## Completed Calibration/Data Runs

Stage 1:

- completed earlier PCB FWD/full calibration baseline.

Stage 2:

- completed PCB FWD/full len2-14 continuation.
- output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/stage2_fwd_full_len2_14_pc_b`

Stage 3:

- completed PCB FWD/full len5-14 continuation.
- output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/stage3_fwd_full_len5_14_pcb`
- review pack:
  - `planning/projects/no_wli/40_review_summaries/stage3_fwd_full_len5_14_pcb_review_pack_2026-05-13.zip`

Stage 4:

- completed PCB FWD/full len8-14 continuation.
- output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/stage4_fwd_full_len8_14_pcb`
- review analysis:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/stage4_fwd_full_len8_14_pcb_review_analysis`
- review pack:
  - `planning/projects/no_wli/40_review_summaries/stage4_fwd_full_len8_14_pcb_review_pack_2026-05-14.zip`
- key closeout:
  - `444000` samples
  - `35520000` feature rows
  - `12000` clean chunks
  - `19.26h`
  - `512.36` feature rows/s
  - next chunk start `34400`
  - raw `feature_rows.csv` absent as intended
  - no error/warning log hits found

## Road-Test Outputs

Real candidate road test v1:

- script:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_span_hamming_real_candidate_road_test_v1.py`
- output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_span_hamming_real_candidate_road_test_v1`
- review pack:
  - `planning/projects/no_wli/40_review_summaries/phaseB_span_hamming_real_candidate_road_test_v1_review_pack_2026-05-13.zip`
- result:
  - `246` candidates
  - `492` chunks
  - Panel A separates good from bad on average but many bad candidates still pass.

Hard-pair road test v1:

- script:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_span_hamming_hard_pair_road_test_v1.py`
- output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_span_hamming_hard_pair_road_test_v1`
- review pack:
  - `planning/projects/no_wli/40_review_summaries/phaseB_span_hamming_hard_pair_road_test_v1_review_pack_2026-05-13.zip`
- result:
  - `2594` historical pairs
  - `604 / 604` token streams resolved
  - `602` current-scorer misranks
  - Panel A truth preference `1904 / 2594` (`0.734`)
  - Panel A rescues `274`
  - Panel A breaks `362`
  - net `-88`
  - conclusion: Panel A is directionally useful but not safe as a standalone override.

Candidate manual inspection pack:

- script:
  - `tools/benchmarks/periodic_sub_trans/no_wli/analysis/build_phaseB_span_hamming_candidate_manual_inspection_v1.py`
- output:
  - `output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_span_hamming_candidate_manual_inspection_v1`
- review pack:
  - `planning/projects/no_wli/40_review_summaries/phaseB_span_hamming_candidate_manual_inspection_v1_review_pack_2026-05-13.zip`
- result:
  - `604 / 604` candidate texts resolved
  - `2594 / 2594` pairs have both texts resolved
  - includes snippets and full compressed token/latin renderings.

## Current Scientific Interpretation

- Span-Hamming is useful local damaged-word evidence.
- Panel A, lengths `5..9`, is the strongest local evidence.
- Panel D strict rows add useful precision/support evidence.
- Panel B longer spans gained better calibration from Stage 4 but remains weaker and
  should be refreshed before interpretation.
- Span-Hamming alone does not solve high-scoring gibberish.
- Many bad candidates have local word-like fragments; order/phrase/ngram coherence is
  the needed next evidence layer.

## Recommended Next Work While Paused

1. Merge/refresh the Stage 1-4 calibration bundle for report-only analysis.
2. Rerun or refresh road-test Panel B using Stage 4 long-span calibration.
3. Build/report an order/phrase/ngram coherence layer.
4. Evaluate any combined report-only scorer simulation on the hard-pair dataset with
   rescue/break accounting.
5. Use the manual inspection pack to annotate failure patterns:
   - local words
   - order-scrambled
   - repetition
   - short-word overmatch
   - periodic/lane artifact
   - partial plaintext
   - possible label issues

## Unpause Conditions

Only resume data-taking if:

- merged Stage 1-4 road tests expose a concrete missing calibration slice;
- Panel B remains unstable for a reason that more data can address;
- a specific new report-only experiment requires a narrowly scoped canary.

If data-taking is unpaused:

- write a new plan first
- justify runtime from retained timing evidence
- use the smallest independently complete run
- define exact config and stop condition
- do not launch serial matrices by inertia

## Do Not Do

- do not start Stage 5 calibration by default
- do not use PCA for new data collection by default
- do not start another PCB continuation by default
- do not change production scorer weights
- do not change scorer defaults
- do not change ranking policy
- do not treat Panel A as a final score
