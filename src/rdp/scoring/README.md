# Scoring candidate text

Scoring turns candidate plaintext into ranking evidence. Character sequences, word-location information and configured dictionary contributions measure different things; the selected objective determines how that evidence becomes a score.

## Where to look

- [rune_scorer.py](rune_scorer.py) — CPU scorer boundary and capability reporting.
- [rune_scorer_impl.py](rune_scorer_impl.py) — CPU scoring implementation.
- [torch_rune_scorer.py](torch_rune_scorer.py) — Torch scoring implementation.
- [unified_rune_scorer.py](unified_rune_scorer.py) — Dispatch through the configured scorer backend.
- [windowing.py](windowing.py) — Word-location and character window alignment.
- [language_model/](language_model/) — N-gram tables and calibration loading.
- [hamming/](hamming/) — Dictionary-distance scoring support.
- [span_hamming/](span_hamming/) — Span matches and calibration support.
- [ngram_hamming/](ngram_hamming/) — Report-only phrase diagnostics.
- [word_ngrams/](word_ngrams/) — Word-token sequence models and reports.
- [scorer_report_builder.py](scorer_report_builder.py) — Build the structured scoring report.
- [retained_state.py](retained_state.py) — Rescore a retained plaintext candidate.

## Choices and extension

`api.ScoringConfig` selects lanes, n-gram orders and weights. Character evidence can work without spaces; word-location evidence needs corresponding word information. Increasing an order may require assets beyond the bundled set. `api.advanced.ScoringObjective` selects the objective. Backend selection is explicit and optional dependencies must be available.

When extending scoring, keep requested, active, unavailable and report-only capabilities distinct. A diagnostic contribution must not silently enter ranking.

Continue with the [guide](../../../docs/guides/scoring.md) or the [package map](../README.md).
