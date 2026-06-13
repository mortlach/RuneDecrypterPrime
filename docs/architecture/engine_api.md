# Engine & API

Audience: Hands-on / Expert
Time: 4-6 minutes
Outcome: Understand how RunAPI builds and runs a solve
Prereqs: Completed one tutorial

**Concept**  
The Engine builds and runs a decryption experiment. It seeds RNG, applies the Pipeline, initialises the Cipher, KeyOps, Scorer, and Optimiser, and records Telemetry.

**Usage**
- Entry point: `RunAPI.run(...)`
- Accepts enums and dataclasses on the public surface; normalisers handle friendly strings.
- Shared semantics for budgets and patience across all optimisers.
- CPU-first; Torch (if present) is kept on CPU for determinism and parity.

**Example**
```python
from rune_decrypter_prime.api import RunAPI
from rune_decrypter_prime.api.specs import CipherSpec, KeySpec, SolverSpec
from rune_decrypter_prime.core.types import Direction

result = RunAPI.run(
    text="KPHIBKRZM...",
    cipher=CipherSpec(name="Substitution"),
    key=KeySpec.permutation(len=29),
    solver=SolverSpec.sa(eval_budget=50_000, patience=2_000, seed=12345),
    encoding_dir=Direction.LTR,
    telemetry_on=True,
)
print(result.score, result.plaintext_str[:80])
```

## Config objects (shape)
- `CipherSpec(name, **params)`
- `SolverSpec(name, eval_budget, time_budget_s=None, patience=None, **params)`
- `KeySpec(...)` (optional; constrain or fix parts of a key)

## Determinism & RNG
- One master RNG per run (`seed`).
- Named child streams per module (examples below).
- No global RNG calls inside core; all randomness is injected.

### RNG streams (named children)
| Stream name           | Used by              | Notes                              |
|-----------------------|----------------------|------------------------------------|
| `optim.sa`            | Simulated Annealing  | Temperature, neighbour choices     |
| `optim.ga`            | Genetic Algorithm    | Selection, crossover, mutation     |
| `optim.beam`          | Beam Search          | Tie-breaks, candidate shuffles     |
| `keyops.permutation`  | Permutation keys     | Swap/insert/reorder operations     |
| `keyops.vector`       | Vector keys          | Per-element tweaks (mod-29)        |
| `misc.bootstrap`      | Engine helpers       | Any non-critical draws             |

## Telemetry
- On by default; JSONL written under `output/.../logs/app.jsonl`.
- True toggle: `RunAPI.run(..., telemetry_on=False)` produces no events and no files.

**Related tests**
- `tests/smoke/test_runapi_determinism.py`
- `tests/telemetry/test_schema_contract.py`
- `tests/telemetry/test_solver_pipeline_block.py`

**See also**  
[Pipeline](pipeline.md) · [Ciphers](ciphers.md) · [Optimisers](optimisers.md) · [Telemetry](telemetry.md)

[<- Home](../README.md) · [Next -> Pipeline](pipeline.md)

