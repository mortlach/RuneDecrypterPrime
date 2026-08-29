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
