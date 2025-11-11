# Solvers - Deep Commentary

Audience: Expert
Time: 8-12 minutes
Outcome: Understand common telemetry fields, patience logic, and how to extend SolverBase
Prereqs: Read Solvers overview; basic familiarity with GA/SA/beam search

Files: solvers/beam.py, solvers/ga.py, solvers/sa.py, solvers/hybrid.py, solvers/solver_base.py, solvers/progress/{logger.py,mixin.py}

## Common base
- Exposes counters (step, evals, since_improve) and the current best.
- Accepts injected RNG streams; never uses global RNG.
- Emits progress events via the progress mixin; integrates with io/run_logger.RunLogger.

## Beam
- Deterministic frontier expansion; tie-breaks explicitly ordered.
- Use for tight key spaces (columnar with small cols).

## GA
- PMX-style recombination for permutations; mutation preserves bijectivity.
- Population sizing and generation budgets must be deterministic.

## SA
- Neighbour moves use cipher-appropriate KeyOps.
- Temperature schedule is explicit (no wall-clock timers).

## Hybrid
- Ordered phases (e.g., Beam -> GA -> SA) recorded in telemetry.
- Budget split is deterministic; carryover of the best candidate is explicit.

## Example (hybrid)
```python
from rune_decrypter_prime.api.wrappers.by_name import by_name
from rune_decrypter_prime.api.run import RunAPI
from rune_decrypter_prime.api.specs import KeySpec, SolverSpec, ScoringConfig
from rune_decrypter_prime.core.types import Direction, Device

SEED = 42
cipher = by_name.cipher("columnar", cols=9)
key = KeySpec.permutation(len=9)
solver = SolverSpec.hybrid(beam={"beam_width": 128}, sa={"sa_iters": 4000}, seed=SEED)
scoring = ScoringConfig(model="bigram", direction=Direction.LTR)

sol = RunAPI.run(
    text=[5, 12, 21, 21, 4, 17, 14, 12, 1],
    cipher=cipher,
    key=key,
    solver=solver,
    device=Device.CPU,
    scorer="rune",
    scorer_params={"encoding_dir": Direction.LTR, "objective": "pct.logp.win10"},
    telemetry_on=True,
    encoding_dir=Direction.LTR,
)
```

## Related tests
- `tests/solvers/test_permutation_optimizers.py`
- `tests/telemetry/test_solver_pipeline_block.py`

