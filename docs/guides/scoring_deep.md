# Scoring - Deep Commentary

Audience: Expert
Time: 8-12 minutes
Outcome: Configure objectives/backends; understand parity tests and telemetry stats
Prereqs: Read the Scoring overview and run one tutorial

> Tracks: Hands-on sections explain how to pick presets; Expert sections describe backend rules, configuration knobs, and tests.

## What Scoring Does
- Converts cipher output (runes + WLI) into numeric scores so solvers can compare candidates.
- Works the same for all solvers because it returns WLI pairs and canonical objective names.

## Hands-on Cheat Sheet
- Use the preset in tutorials: `ScoringConfig(objective="pct.logp.win10", encoding_dir=Direction.LTR)`.
- If you flip directions (RTL), set `encoding_dir` so scoring tables match.
- Inspect `sol.meta["telemetry"]["scorer"]` to see which backend ran (NumPy by default).

## Expert Details
### Interface Rules
- All scorers emit WLI arrays so solvers stay backend-agnostic.
- `scoring/scoring_adapter.py` is the lone entry point; normalise knobs there so tutorials/tests/telemetry stay in sync.
- Objectives (policy.py) must use canonical strings (e.g., `pct.logp.win10`).

### Backend Matrix
| Backend | Module | Pros | Caveats |
| --- | --- | --- | --- |
| NumPy | `scoring/rune_scorer.py` | Always available, deterministic on CPU | Limited to float32 |
| Torch | `scoring/torch_rune_scorer.py` | Shares kernels with research notebooks, CUDA support | Requires Torch install; seed via tests' RNG helpers |
| Unified | `scoring/unified_rune_scorer.py` | Bridges classic + LM tables under one API | Needs tables registered via `scoring/unified_tables.py` |

All backends consume the same RNG seed, so telemetry diffs highlight solver logic rather than scorer drift.

### Direction Awareness
- LTR vs RTL selects a different namespace of WLI tables.
- Tutorials/tests should pass `scorer_params.encoding_dir = encoding_dir` so scorers, pipeline blocks, and solution metadata agree.

### Example Config
```python
from rune_decrypter_prime.api.specs import ScoringConfig
from rune_decrypter_prime.core.types import Direction

scoring_cfg = ScoringConfig(
    objective="pct.logp.win10",
    char_weights={2: 0.3},
    wli_weights={2: 0.7},
    include_char=True,
    use_word_breaks=True,
    encoding_dir=Direction.LTR,
)
```

### Tests & Validation
- Backend selection/parity: `tests/scoring/test_backend_selection_and_parity.py`.
- Telemetry timing keys: `tests/telemetry/test_progress_events.py` (score_time_s).
- Tutorials: GA/SA/Hybrid regressions ensure scoring + solvers reach expected thresholds.

### Authoring Guidelines
- When adding objectives/backends, update `scoring/scoring_adapter.py`, policy modules, and docs (this page + quickstart if presets change).
- Add parity tests whenever you introduce a new backend or tweak WLI tables.
- Mention determinism constraints (seed usage) in PRs.

## Related Docs
- `guides/telemetry.md` - telemetry fields populated by scoring.
- `guides/outputs.md` - how scoring metrics show up in logs/solution.meta["work"].
- `howto/add_solver.md` - how solvers consume scoring configs.

