# Welcome Pilgrim

Source label:

```text
welcome_pilgrim
red_rune.welcome_pilgrim
solved.welcome_pilgrim
```

Primary recipe:

```text
recipe.welcome_pilgrim.vigenere_interruptors
```

Status:

```text
source catalogue entry exists
payload_from_label loads real master-transcript ciphertext/WLI
current boundary granularity: full master transcript pages 1-2
first bounded solve tutorial exists
```

Tutorial:

```text
tutorials/v1/Tutorial_LP_Welcome_Pilgrim_Solve.py
```

Default tutorial assumptions:

```text
source_label      = welcome_pilgrim
cipher            = vigenere
period            = 7
interruptor_pool  = all ciphertext positions
max_interruptors  = 5
encoding_dir      = rtl
```

The solver is not given the canonical plaintext or the canonical key. The label
only supplies the real LP ciphertext and WLI from the master transcript.

Useful overrides:

```text
RDP_LP_WELCOME_MAX_INTERRUPTORS=5
RDP_LP_WELCOME_BEAM_WIDTH=64
RDP_LP_WELCOME_PLATEAU_ROUNDS=5
RDP_LP_WELCOME_DIRECTION=rtl
```

Goal:

RDP should reproduce this solved LP text as a Vigenere-with-interruptors real
solve. The intended user-facing setup should remain simple:

```text
source_label = welcome_pilgrim
period       = 7
max_interruptors = <chosen search budget>
```

The source label remains method-free. Vigenere/interrupter information belongs
in the recipe and runner, not in the LP source label.
