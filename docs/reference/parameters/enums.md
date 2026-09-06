# Common public enums

These values are exported through `api` or `api.advanced`.

## Run fields

| Enum | Values |
| --- | --- |
| `TextDirection` | `LEFT_TO_RIGHT`, `RIGHT_TO_LEFT` |
| `ComputeDevice` | `CPU`, `CUDA` |
| `WordLengthPolicy` | `DISABLED`, `INFER`, `REQUIRE` |

## Solver and cipher controls

| Enum | Values |
| --- | --- |
| `BeamExpansionMode` | `EXHAUSTIVE`, `SAMPLE`, `SWEEP` |
| `KaedingBlockSchedule` | `RANDOM`, `ROUND_ROBIN` |
| `KaedingSlipPolicy` | `FIXED_INTERVAL`, `ON_STALL` |
| `InterruptorSearchStrategy` | `AUTO`, `BRUTE_FORCE`, `KEY_OPERATIONS` |
| `PeriodicColumnarOrder` | `COLUMNAR_THEN_SUBSTITUTION`, `SUBSTITUTION_THEN_COLUMNAR` |
| `ScheduledStreamSchedule` | `OVERLAY`, `ALTERNATING`, `MASK` |
| `ScheduledStreamOperation` | `ADD`, `ADD_SUBTRACT`, `SUBTRACT_ADD`, `BEAUFORT_SUM` |

## Language-model scoring

| Enum | Values |
| --- | --- |
| `SmoothingMethod` | `NONE`, `LIDSTONE`, `JEFFREYS`, `AUTO_GOOD_TURING` |
| `OutOfVocabularyPolicy` | `FLOOR_MINIMUM_SEEN`, `LIDSTONE` |
| `LanguageModelBoundaryMode` | `EXCLUDE_BOUNDARIES`, `INCLUDE_BOUNDARIES` |
| `ScoreDirection` | `MAXIMIZE`, `MINIMIZE` |
| `ScorerBackend` | `AUTO`, `NUMPY`, `TORCH`, `UNIFIED` |
| `ScoringObjectiveKind` | `PERCENTILE`, `AVERAGE`, `NEGATIVE_LOG_PROBABILITY` |
| `ScoreStatistic` | `LOG_PROBABILITY`, `Z_SCORE_SUM`, `MEDIAN_ABSOLUTE_DEVIATION_SUM` |
| `AverageWindowPolicy` | `FIXED_WINDOW`, `FULL_TEXT` |
| `FloatDType` | `FLOAT32`, `FLOAT64` |

## Hamming and span-Hamming

| Enum | Values |
| --- | --- |
| `HammingDictionaryPolicy` | `STRICT`, `NORMAL`, `BROAD`, `RESEARCH` |
| `HammingTextDirectionMode` | `MATCH_TEXT`, `BOTH` |
| `SpanHammingMode` | `OFF`, `RAW_BONUS`, `CALIBRATED` |
| `SpanHammingBucketPolicy` | `NEAREST_SMALLER_ON_TIE` |
| `SpanHammingCombineMode` | `MINIMUM`, `WEIGHTED_SUM` |
| `SpanHammingGateFailurePolicy` | `SCORE_FLOOR`, `CHARACTER_ONLY` |
| `SpanHammingLanguageModelProfileSource` | `RAW_SPAN_BY_LENGTH`, `CHARACTERS_COVERED_BY_LENGTH` |

For practical use, see [API reference](../README.md).

See also [Parameter reference](README.md) and [Defaults at a glance](../defaults.md).
