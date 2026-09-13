# Quickstart

For an uninstalled checkout or interactive Python, see [Using RDP](using_rdp.md).

Start with the known-key tutorial:

```text
python -m tutorials.v1.getting_started.01_known_key
```

The key is supplied, so this first example isolates the cipher path. The next
example removes the key and introduces a search:

```text
python -m tutorials.v1.getting_started.02_first_search
```

A normal search brings together six things:

```text
ciphertext
-> cipher
-> key space
-> solver
-> scoring
-> result
```

For example:

```python
from rdp import api

PLAINTEXT: api.RuneIndices = (
    2, 18, 4, 18, 7, 24, 15, 24, 16, 24, 17, 20, 18, 15,
    18, 16, 3, 1, 16, 1, 9, 23, 18, 4, 24, 16, 4, 18, 18,
)
SECRET_KEY: api.ConcreteKey = (7,)

cipher = api.CipherSpec.rail_fence(
    minimum_rails=2,
    maximum_rails=8,
)
ciphertext = api.encrypt(PLAINTEXT, cipher=cipher, key=SECRET_KEY)

request = api.RunSpec(
    problem_input=api.RuneInput(value=ciphertext),
    cipher=cipher,
    key_space=api.KeySpec.scalar(
        minimum=2,
        maximum=8,
    ),
    solver=api.SolverSpec.beam_search(
        width=8,
        rounds=None,
        seed=7,
    ),
    scoring=api.ScoringConfig(
        character_lane_enabled=True,
        wli_lane_enabled=False,
        character_order_weights={1: 0.2, 2: 0.8},
        wli_order_weights={},
    ),
    text_direction=api.TextDirection.LTR,
)

result = api.run(request)

assert result.key == SECRET_KEY
assert result.plaintext_indices == PLAINTEXT
print(result.plaintext_runes)
```

Each part states one assumption about the problem. In this example the rail
count is unknown, beam search explores the allowed range, character scoring is
used without WLI, and the text direction is set explicitly.

The library default text direction is `LTR`, which is also the direction used
by this example. Set `RTL` explicitly when the input or experiment requires it.
The longer names remain available as aliases when they read better in a
particular context.

Before using a new ciphertext, the three useful pieces are:

- [Ciphertext input](ciphertext_input.md)
- [Word-length information](word_length_information.md)
- [Text direction](text_direction.md)

The next step is [Defining a run](anatomy_of_a_run.md). The broader solving
workflow is covered in [Comparing solve experiments](working_a_solve.md).
