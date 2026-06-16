# Welcome Pilgrim

Source label:

```text
red_rune.welcome_pilgrim
```

Primary recipe:

```text
recipe.welcome_pilgrim.vigenere_interruptors
```

Status:

```text
source catalogue entry exists
exact master-transcript locator pending verification
runner not implemented yet
```

Goal:

RDP should reproduce this solved LP text as a Vigenere-with-interruptors real
solve. The intended user-facing setup should eventually be no more complex than:

```text
source_label = red_rune.welcome_pilgrim
period       = <verified period>
max_iter     = <chosen search budget>
```

The source label must remain method-free. Vigenere/interrupter information
belongs in the recipe and runner, not in the LP source label.
