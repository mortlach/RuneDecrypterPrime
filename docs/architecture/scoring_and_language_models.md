# Scoring and language models

Scoring turns candidate plaintext into ranking evidence.

```text
candidate plaintext
-> language-model evidence
-> optional specialist evidence
-> scoring objective
-> score
```

The solver sees the score, not the language-model internals.

## Character and WLI evidence

The ordinary lanes are:

**character n-grams** — likelihood of the rune sequence under the selected
model.

**WLI n-grams** — likelihood of the sequence with word-position and word-length
information.

Both are enabled by default.

See [Scoring](../guides/scoring.md) and
[Word-length information](../guides/word_length_information.md).

## Language-model tables

The runtime loads precomputed n-gram tables and calibration data.

Model selection depends on lane, n-gram order and text direction.

The V1 defaults use order 2 for both ordinary lanes.

Small model assets are bundled. Larger assets are installed separately.

Missing required model evidence is an error.

See [Installation](../setup/installation.md).

## Objective

`ScoringConfig.objective` turns the model evidence into one ranking value.

The default is percentile log probability with the standard window size of 10.

Alternative objectives are exposed through
`api.advanced.ScoringObjective`.

See [Scoring parameters](../reference/parameters/scoring.md).

## Direction

Text direction belongs to `RunSpec`.

The scorer receives that direction and selects the corresponding directional
model evidence.

See [Text direction](../guides/text_direction.md).

## Backend

Backend choice changes execution, not the requested evidence.

`AUTO` uses the ordinary CPU scorer on CPU runs and the Torch scorer on CUDA
runs.

An explicitly requested unavailable accelerator fails rather than silently
falling back to CPU.

See [CPU, CUDA and scoring](../setup/scorer_backend_selection.md).

## Specialist evidence

Optional facilities include Hamming, span-Hamming, hard cribs and word n-gram
judging.

A scoring feature should state whether it ranks candidates, gates candidates,
adds calibrated evidence or reports diagnostics only.

Requested, active, unavailable and report-only states are kept distinct.

## Search boundary

The scorer does not mutate keys or choose the next candidate.

See [Candidate evaluation](candidate_evaluation.md).

## Extending scoring

New scoring work belongs under `src/rdp/scoring/`.

The language-model runtime under `src/rdp/scoring/language_model/` owns table
loading, model indices, calibration data and the native fast loader.

See [Extending RDP](../guides/extending_rdp.md).

## Span-Hamming interval evidence

The span backend matches a flat rune stream against dictionary words without
requiring WLI. For a span of length `L` at bounded Hamming distance `d`, quality
is `1 - min(d, max_hd + 1) / (max_hd + 1)` and interval weight is quality times
`L`. Intervals below the configured quality threshold are discarded.

Weighted interval scheduling chooses non-overlapping spans. Weight comparisons
use a `1e-12` tolerance, then prefer greater character coverage and the
lexicographically earlier canonical `(end, start, -length)` schedule.

`coverage` is covered characters divided by text length, `quality` is selected
weight divided by covered characters, and `span_raw = coverage * quality`.
Zero-length denominators are guarded. Per-length metrics use fixed bins, and
candidate/truncation limits are deterministic. These backend measurements do
not themselves decide whether a configured lane ranks or only reports.
