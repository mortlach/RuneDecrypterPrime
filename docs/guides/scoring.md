# Scoring - WLI Pairs

Audience: Hands-on / Expert
Time: 3-5 minutes
Outcome: Understand WLI outputs and how to set objectives
Prereqs: Completed one tutorial

> DRAFT - see `guides/scoring_deep.md` for objectives, backends, and telemetry.

- Output shape: a list of numeric pairs (WLI).
- Pass objectives via `scorer_params` (e.g., `"pct.logp.win10"`).
- Backends: NumPy by default; Torch available (CPU on v1 surface).

## Objectives
- Recommended: `pct.logp.win10` (percentile of log-probability across windows of size 10).
- Aliases map to canonical forms in `api/normalize.py`.

## Hands-on snippet
```python
from rune_decrypter_prime.api import RunAPI, SolverSpec, KeySpec, by_name
from rune_decrypter_prime.core.types import Direction

sol = RunAPI.run(
    text="??????",
    cipher=by_name.cipher("vigenere", key_len=6),
    key=KeySpec.repeat(len=6),
    solver=SolverSpec.sa(seed=42, progress_pct=1),
    scorer="rune",
    scorer_params={"objective": "pct.logp.win10", "encoding_dir": Direction.LTR},
    telemetry_on=True,
)
```

## Related tests
- `tests/scoring/test_pct_win10_stats_and_telemetry.py`
- `tests/scoring/test_backend_selection_and_parity.py`

