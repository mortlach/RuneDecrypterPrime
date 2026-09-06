# Quickstart

Start with the known-key tutorial:

```text
python -m tutorials.v1.getting_started.01_known_key
```

The key is supplied, so this first example isolates the cipher path. The next
example removes the key and introduces a search:

```text
python -m tutorials.v1.getting_started.02_first_search
```

A normal search brings together five things:

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

request = api.RunSpec(
    problem_input=api.RuneIndexInput(indices=ciphertext),
    cipher=api.CipherSpec.rail_fence(
        minimum_rails=2,
        maximum_rails=8,
    ),
    key_space=api.KeySpec.scalar(
        minimum=2,
        maximum=8,
    ),
    solver=api.SolverSpec.beam_search(
        width=8,
        rounds=0,
        seed=7,
    ),
    scoring=api.ScoringConfig(
        character_lane_enabled=True,
        word_length_lane_enabled=False,
        character_order_weights={1: 0.2, 2: 0.8},
        word_length_order_weights={},
    ),
    text_direction=api.TextDirection.LEFT_TO_RIGHT,
)

result = api.run(request)
```

Each part states one assumption about the problem. In this example the rail
count is unknown, beam search explores the allowed range, character scoring is
used without WLI, and the text direction is set explicitly.

The library default text direction is `RIGHT_TO_LEFT`. The example chooses
`LEFT_TO_RIGHT` because that is the problem being demonstrated.

Before using a new ciphertext, the three useful pieces are:

- [Ciphertext input](ciphertext_input.md)
- [Word-length information](word_length_information.md)
- [Text direction](text_direction.md)

The next step is [Defining a run](anatomy_of_a_run.md). The broader solving
workflow is covered in [Comparing solve experiments](working_a_solve.md).
