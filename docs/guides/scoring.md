# Scoring quick reference

The scorer ranks candidate plaintexts so the solver can decide which keys
look promising. Choose its settings with `api.ScoringConfig`, then pass that
configuration to `RunSpec`:

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

The problem input supplies the rune indices and any word-location information.
Set text direction and device on `RunSpec` separately.

RDP reports a block if a requested scoring lane cannot run. Check
`result.scorer_report` for the objective, score, timing and details of the
scoring that ran. Diagnostic-only lanes and truth/oracle data do not affect
the ranking.

Use the enum values from `api.advanced` as shown above. If you are loading
settings from a dictionary of serialized strings, use `ScoringConfig.from_dict`.

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
shows where the scoring code lives and where to start extending it.
