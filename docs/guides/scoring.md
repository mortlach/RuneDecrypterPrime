# Scoring quick reference

Scoring configuration is a typed `api.ScoringConfig` owned by `RunSpec`.

```python
from rdp import api

scoring = api.ScoringConfig(
    objective=api.advanced.ScoringObjective.average_log_probability(),
    backend=api.advanced.ScorerBackend.NUMPY,
    compute_dtype=api.advanced.FloatDType.FLOAT32,
    character_lane_enabled=True,
    word_length_lane_enabled=False,
)
```

Rune indices and optional word-length information come from the typed problem
input. Direction and device are separate `RunSpec` fields; they are not hidden
inside a scorer-parameter dictionary.

Requested lanes must run or report a clear block. Diagnostic-only lanes and
truth/oracle data do not affect ranking. `RunResult.scorer_report` records the
objective, score, timing, capability evidence and relevant details.

Enum fields receive values from `api.advanced`. Serialized strings belong only
at the `ScoringConfig.from_dict` boundary.

## Useful choices

- **Character evidence:** `character_order_weights` selects n-gram orders and
  their weights. Pairs capture different structure from individual runes.
- **Word information:** `word_length_lane_enabled` and
  `word_length_order_weights` select the corresponding evidence. Supply aligned
  word-location information; invented boundaries change the problem.
- **Objective:** average log probability and calibrated percentile objectives
  measure the evidence differently. Compare scores under the same objective.
- **Backend:** NumPy is the reference CPU path; see
  [backend selection](../setup/scorer_backend_selection.md) before choosing an
  optional Torch/device configuration.

Higher n-gram orders can require the full model pack. Start from a working
configuration, change one contribution and inspect `result.scorer_report` to
see what actually ran. The [scoring source map](../../src/rdp/scoring/README.md)
locates the implementations and extension boundaries.
