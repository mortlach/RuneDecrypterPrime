# Hamming scorer

The Hamming lane is an optional lexical shaping component owned by the scoring
runtime. Normal users configure it through typed `api.ScoringConfig` fields:

```python
from rdp import api

scoring = api.ScoringConfig(
    objective=api.advanced.ScoringObjective.percentile_log_probability(
        window_size=10
    ),
    hamming_enabled=True,
    hamming_build_right_to_left=False,
    hamming_maximum_weight=0.08,
    hamming_ramp_start_fraction=0.2,
    hamming_ramp_end_fraction=0.7,
    hamming_maximum_distance=10,
)
```

The runtime loads its selected dictionary assets, calculates per-word distance
evidence and reports lane status. If the lane is requested but unavailable, the
request must block or report an explicitly authorised fallback; it must not be
silently omitted.

Contributor-level backend work imports the exact owners under
`rdp.scoring.hamming`. That implementation surface is not a
normal tutorial API.

Diagnostic Hamming sections must not influence ranking unless the typed scoring
configuration explicitly makes the lane part of the production objective.
