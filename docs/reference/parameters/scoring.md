# ScoringConfig parameters

The table is split by lane because `ScoringConfig` covers the ordinary language
model and several specialist scoring features.

## Core language-model scoring

| Parameter | Type | Default | Notes / constraint |
| --- | --- | --- | --- |
| `language_model_root` | `Path | None` | `None` | Optional explicit model root. |
| `smoothing` | `SmoothingMethod` | `AUTO_GOOD_TURING` | See [Common enums](enums.md). |
| `smoothing_alpha` | `float` | `0.5` | Finite. |
| `out_of_vocabulary_policy` | `OutOfVocabularyPolicy` | `FLOOR_MINIMUM_SEEN` | See [Common enums](enums.md). |
| `character_lane_enabled` | `bool` | `True` | Enables character LM scoring. |
| `wli_lane_enabled` | `bool` | `True` | Enables WLI LM scoring. |
| `character_ngram_order` | `int` | `2` | Positive. |
| `wli_ngram_order` | `int` | `2` | Positive. |
| `window_size` | `int` | `10` | Positive. |
| `stride` | `int` | `1` | Positive. |
| `boundary_mode` | `LanguageModelBoundaryMode` | `EXCLUDE_BOUNDARIES` | V1 supports only `EXCLUDE_BOUNDARIES`; `INCLUDE_BOUNDARIES` is rejected. |
| `base_lane_weights` | `tuple[float, float] | None` | `None` | Optional base character/WLI lane weights. |
| `score_direction` | `ScoreDirection` | `MAXIMIZE` | V1 accepts only `MAXIMIZE`; `MINIMIZE` is rejected because the objective owns ranking sense. |
| `character_order_weights` | mapping or `None` | `None` | Positive integer n-gram orders to non-negative weights. |
| `wli_order_weights` | mapping or `None` | `None` | Positive integer n-gram orders to non-negative weights. |
| `backend` | `ScorerBackend` | `AUTO` | `AUTO`, `NUMPY`, `TORCH`, or `UNIFIED`. A resolved AUTO backend is reported as effective runtime state when scorer telemetry establishes it. |
| `compute_dtype` | `FloatDType` | `FLOAT32` | `FLOAT32` or `FLOAT64`. |
| `accumulator_dtype` | `FloatDType` | `FLOAT64` | `FLOAT32` or `FLOAT64`. |
| `objective` | `ScoringObjective` | percentile log probability, window `10` | Typed objective. |
| `average_window_policy` | `AverageWindowPolicy` | `FIXED_WINDOW` | `FIXED_WINDOW` or `FULL_TEXT`. |
| `ecdf_clamp_minimum` | `float` | `1e-6` | Finite. |
| `ecdf_clamp_maximum` | `float` | `1 - 1e-6` | Finite. |
| `diagnostics_enabled` | `bool` | `False` | Enables scoring diagnostics. |
| `hard_crib` | `HardCribConfig | None` | `None` | Optional hard crib rules. |

## ScoringObjective constructors

| Constructor | Parameters | Default |
| --- | --- | --- |
| `percentile_log_probability` | `window_size: int` | `10` |
| `percentile_z_score_sum` | `window_size: int` | `10` |
| `percentile_median_absolute_deviation_sum` | `window_size: int` | `10` |
| `average_log_probability` | none | n/a |
| `negative_log_probability` | none | n/a |

Percentile window sizes must be positive.

## HardCribConfig

| Parameter | Type | Default | Notes |
| --- | --- | --- | --- |
| `enabled` | `bool` | `False` | Enables hard crib filtering. |
| `mode` | `HardCribMode` | `HARD` | `HARD` is the current supported mode. |
| `require_wli_for_word_rules` | `bool` | `True` | Requires WLI for word-level rules. |
| `fixed_characters` | mapping or `None` | `None` | Text position to allowed rune indices. |
| `per_word_allowed` | mapping or `None` | `None` | Word index to allowed rune sequences. |
| `global_allowed_by_length` | mapping or `None` | `None` | Word length to allowed rune sequences. |

Rune indices in hard-crib rules are in `0..28`.

## Hamming lane

| Parameter | Type | Default | Notes / constraint |
| --- | --- | --- | --- |
| `hamming_enabled` | `bool` | `False` | Enables the Hamming lane. |
| `hamming_dictionary_policy` | `HammingDictionaryPolicy` | `NORMAL` | `STRICT`, `NORMAL`, `BROAD`, or `RESEARCH`. |
| `hamming_dictionary_root` | `Path | None` | `None` | Optional dictionary-policy root. |
| `hamming_wordlist_directory` | `Path | None` | `None` | Optional word-list directory. |
| `hamming_build_right_to_left` | `bool` | `False` | Builds RTL Hamming data when requested. |
| `hamming_weight` | `float | None` | `None` | Optional explicit weight. |
| `hamming_maximum_weight` | `float` | `0.01` | Finite. |
| `hamming_ramp_start_fraction` | `float` | `0.2` | Finite. |
| `hamming_ramp_end_fraction` | `float` | `0.7` | Finite. |
| `hamming_maximum_distance` | `int` | `1_000_000` | At least `0`. |
| `hamming_length_weights` | mapping | empty | Positive integer lengths to non-negative weights. |
| `hamming_text_direction_mode` | `HammingTextDirectionMode` | `MATCH_TEXT` | `MATCH_TEXT` or `BOTH`. |

## Span-Hamming lane

| Parameter | Type | Default |
| --- | --- | --- |
| `span_hamming_enabled` | `bool` | `False` |
| `span_hamming_wordlist_directory` | `Path | None` | `None` |
| `span_hamming_weight` | `float` | `0.0` |
| `span_hamming_minimum_length` | `int` | `3` |
| `span_hamming_maximum_length` | `int` | `14` |
| `span_hamming_maximum_distance` | `int` | `2` |
| `span_hamming_start_stride` | `int` | `1` |
| `span_hamming_maximum_windows` | `int` | `0` |
| `span_hamming_maximum_candidates_per_window` | `int` | `256` |
| `span_hamming_maximum_intervals_per_start` | `int` | `4` |
| `span_hamming_minimum_quality` | `float` | `1e-9` |
| `span_hamming_return_debug_intervals` | `bool` | `False` |
| `span_hamming_require_selection` | `bool` | `True` |
| `span_hamming_mode` | `SpanHammingMode` | `OFF` |
| `span_hamming_assets_directory` | `Path | None` | `None` |
| `span_hamming_assets_dictionary_policy` | `HammingDictionaryPolicy | None` | `None` |
| `span_hamming_allow_dictionary_mismatch` | `bool` | `False` |
| `span_hamming_bucket_policy` | `SpanHammingBucketPolicy` | `NEAREST_SMALLER_ON_TIE` |
| `span_hamming_ecdf_clamp_minimum` | `float | None` | `None` |
| `span_hamming_ecdf_clamp_maximum` | `float | None` | `None` |
| `span_hamming_combine_mode` | `SpanHammingCombineMode` | `MINIMUM` |
| `span_hamming_span_weight` | `float` | `1.0` |
| `span_hamming_character_weight` | `float` | `0.0` |
| `span_hamming_minimum_coverage` | `float` | `0.0` |
| `span_hamming_minimum_gate_quality` | `float` | `0.0` |
| `span_hamming_minimum_span_percentile` | `float | None` | `None` |
| `span_hamming_minimum_character_percentile` | `float | None` | `None` |
| `span_hamming_gate_failure_policy` | `SpanHammingGateFailurePolicy` | `SCORE_FLOOR` |
| `span_hamming_gate_score_floor` | `float | None` | `None` |
| `span_hamming_language_model_assets` | `Path | None` | `None` |
| `span_hamming_language_model_profile_source` | `SpanHammingLanguageModelProfileSource` | `RAW_SPAN_BY_LENGTH` |
| `span_hamming_language_model_tail_start` | `int` | `5` |
| `span_hamming_language_model_weight` | `float` | `0.0` |

Length and stride fields are positive unless the field explicitly uses `0` as
the disabled or unlimited value. `span_hamming_maximum_length` must not be below
`span_hamming_minimum_length`.

The enum values are listed in [Common enums](enums.md).

## Word n-gram judge

| Parameter | Type | Default |
| --- | --- | --- |
| `word_ngram_judge_enabled` | `bool` | `False` |
| `word_ngram_judge_database` | `Path | None` | `None` |
| `word_ngram_judge_alpha` | `float` | `0.4` |
| `word_ngram_judge_missing_log_probability` | `float` | `-20.0` |
| `word_ngram_judge_minimum_positions` | `int` | `12` |
| `word_ngram_judge_prefix_thresholds` | `tuple[int, ...]` | `(1, 10, 100)` |

The specialist lanes are off by default. A run that enables one should normally
explain why it is part of that experiment.

For practical use, see [Scoring](../../guides/scoring.md).
