# Two-period crib solver — V1 contract

The public V1 solver targets the additive two-period
`scheduled_stream_lookup` shape over the 29-rune alphabet. It is CPU-only.

```python
from rdp import api

cipher, key = api.by_name.cipher_with_key(
    "two_period_vigenere",
    period_a=13,
    period_b=31,
    alphabet_size=29,
    default_key=True,
)
solver = api.SolverSpec.two_period_cribs(
    fixed_cribs=(("uncomfortable", 188),),
    candidate_words=("dormouse",),
    starts=96,
    seed=101,
)
result = api.run(
    text=ciphertext,
    cipher=cipher,
    key=key,
    solver=solver,
    return_solver_report=True,
)
api.print_rdp_result(result)
```

Every crib must describe a complete word according to the supplied WLI. Fixed
cribs are authoritative known placements. Candidate words are encoded and
placed automatically at every matching complete-word span; impossible or
incompatible placements remain visible as rejection evidence.

The flattened key is canonical A-then-B order. An omitted seed has deterministic
effective value `0`. Search is the retained S2 scout, B1 bridge, F1 judge with
three coordinate sweeps, then static F1 ranking over the complete deduplicated
scout, bridge and judge union.

The route returns the normal `RunResult`, `Solution` and `SolverReport` and uses
the normal RDP display/printer surface. V1 does not silently accept scorer
parameters, interruptors, initial keys or text permutations on this specialised
route: unsupported options raise clear errors.
