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
    interruptors=api.InterruptorConfig(
        mode="pool",
        pool=[190, 192, 194],
        min_count=2,
        max_count=2,
    ),
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

The route uses the normal V1 structural interruptor contract. Interruptor
symbols are fixed from the input: chosen positions are removed before the core
cipher runs and reinserted unchanged afterwards. `exact` interruptors therefore
produce one structural branch. A `pool` with `min_count`/`max_count` produces
deterministic structural hypotheses because each choice changes the compacted
core positions used by the crib equations.

For a non-interruptor crib rune, periodic A/B indices use its compacted core
position, not its absolute full-text position. A crib rune that lies on an
interruptor must equal the unchanged ciphertext rune and adds no key equation.

`search_strategy="auto"` exhaustively resolves structural hypotheses while the
total combination count is within `bruteforce_max`. This specialised route does
not silently switch to KeyOps when that cap is exceeded: it raises a clear error
so the caller can narrow the pool/count range, raise the cap, or explicitly
request `bruteforce`. `search_strategy="keyops"` is not supported by this
constraint route in V1.

The route returns the normal `RunResult`, `Solution` and `SolverReport` and uses
the normal RDP display/printer surface. The report records the requested
interruptor configuration, structural hypothesis count and winning positions.
V1 does not silently accept scorer parameters, initial keys or text permutations
on this specialised route: unsupported options raise clear errors.
