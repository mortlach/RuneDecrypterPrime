# Two-period crib solver — V1 contract

The public CPU-only solver targets the additive two-period Vigenere shape over
the 29-rune alphabet. Both periods belong to `CipherSpec`; the compatible repeating
key space and every concrete key contain `first_period + second_period` values.

```python
from rdp import api

first_period = 13
second_period = 31
cipher = api.CipherSpec.two_period_vigenere(
    first_period=first_period,
    second_period=second_period,
    alphabet_size=29,
)
key_space = api.KeySpec.repeating(length=first_period + second_period)
solver = api.SolverSpec.two_period_cribs(
    fixed_cribs=(("uncomfortable", 188),),
    candidate_words=("dormouse",),
    starts=96,
    seed=2026,
)
request = api.RunSpec(
    problem_input=api.RuneIndexInput(indices=(0, 1, 2, 3)),
    cipher=cipher,
    key_space=key_space,
    solver=solver,
    text_direction=api.TextDirection.LEFT_TO_RIGHT,
)
result = api.run(request)
```

Run construction validates the derived key length before solve-time binding.
A conflicting `KeySpec` is rejected rather than reinterpreted.

Known-key preparation uses the same binding:

```python
key: api.ConcreteKey = tuple(
    index % 29 for index in range(first_period + second_period)
)
ciphertext = api.encrypt((0, 1, 2, 3), cipher=cipher, key=key)
plaintext = api.decrypt(ciphertext, cipher=cipher, key=key)
```

The concrete layout is the first periodic stream followed by the second. The
public values are semantic rune shifts in `0..28`; lists, arrays and legacy
offsets are not accepted.

Interruptor ciphertext preparation remains a tutorial/test fixture concern.
The public API exposes typed interruptor configuration for solving, not an
interruptor-specific encryption operation.

Every crib must describe a complete word according to the supplied WLI. Fixed
cribs are authoritative known placements. Candidate words are encoded and
placed automatically at every matching complete-word span; impossible or
incompatible placements remain visible as rejection evidence.

The flattened key uses canonical A-then-B layout. An omitted seed has the
deterministic effective value `0`. Search is the retained S2 scout, B1 bridge,
and F1 judge with three coordinate sweeps, followed by static F1 ranking over
the complete deduplicated scout, bridge, and judge union.

Typed `InterruptorConfig` values use the normal V1 structural interruptor
contract. Selected positions are removed before the core cipher runs and are
reinserted unchanged afterwards. Exact positions therefore produce one
structural branch. A candidate pool with equal minimum and maximum counts
produces deterministic structural hypotheses because each choice changes the
compacted core positions used by the crib equations.

For a non-interruptor crib rune, periodic A/B indices use its compacted core
position rather than its absolute full-text position. A crib rune on an
interruptor must equal the unchanged ciphertext rune and adds no key equation.

`search_strategy="auto"` exhaustively resolves structural hypotheses while the
combination count is within `bruteforce_max`. The specialised route does not
silently switch strategies when that cap is exceeded: it raises a clear error
so the caller can narrow the pool/count range, raise the cap, or explicitly
request brute force. `search_strategy="keyops"` is not supported by this
constraint route in V1.

The route returns the normal `RunResult` and `SolverReport`. The report records
the requested interruptor configuration, structural-hypothesis count, and
winning positions. Unsupported solver inputs fail clearly; they are not
silently reinterpreted.
