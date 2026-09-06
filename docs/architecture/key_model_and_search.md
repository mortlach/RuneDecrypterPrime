# Key models and search operations

A key space has two related roles in RDP.

At the public API it states which keys are valid.

At runtime it selects the operations a solver can use to move through that
space.

## Public key model

A public run uses `KeySpec`:

```python
key_space = api.KeySpec.repeating(
    length=7,
)
```

A repeating key is a fixed vector of rune values. A permutation key is an
ordering. A periodic-substitution key contains one permutation block per period
position.

The cipher and key space are validated together before execution.

Current bindings include:

| Cipher | Key model |
| --- | --- |
| Vigenere | repeating |
| Autokey | repeating |
| columnar | permutation |
| substitution | permutation |
| periodic substitution | structured periodic |
| periodic columnar | structured periodic + column permutation |
| rail fence | scalar |

See [Keys and key spaces](../guides/keyops.md).

## Runtime KeyOps

Solvers do not carry separate mutation code for every key type.

The runtime constructs a KeyOps implementation for the selected key model.
The common operation vocabulary includes:

```text
random
normalize
mutate
neighbor
recombine
make_population
batch_neighbors
expand_position
local_improve
```

`random`, `normalize` and `mutate` are the basic contract. Other operations are
capabilities used when present.

## Current families

| Family | Typical use | Invariant |
| --- | --- | --- |
| vector | repeating keys, stream keys, scalar-like search, experimental maps | values remain in the configured domain |
| permutation | columnar and substitution keys | each value appears exactly once |
| matrix | periodic substitution and periodic columnar | each structured permutation block remains valid |
| composite | core key plus searched interruptor positions | core key and interruptor constraints both remain valid |

Interruptor search wraps the core key with the positions being searched.

See [Interruptors](../guides/interruptors.md).

## Mutation depends on key structure

A vector mutation can change one value by a small wrapped step.

A permutation mutation swaps or cycles positions. Arbitrary replacement would
break the permutation.

A structured periodic key preserves every substitution block separately, plus
the column permutation where one exists.

The solver asks for a move. KeyOps defines the valid move for that key family.

## Solver use

Beam search prefers `expand_position`, then `batch_neighbors`, then `mutate`
when those capabilities are available.

GA uses population generation, recombination and mutation.

SA uses neighbours, with mutation as the fallback.

See [Solver mechanics](solver_mechanics.md).

## Designing a key model

A key representation needs a valid storage form and search operations that fit
the space.

The operations should preserve invariants, make sensible local moves, cover the
intended space and support batching where the solver benefits from it.

A new cipher and its key model are therefore designed together.

## Public KeySpec and runtime KeyOps

Callers use `KeySpec`. Runtime KeyOps classes remain internal.

The runtime binding selects KeyOps from the accepted cipher/key-space pair.

Contributor work starts at [Build key operations](../howto/build_keyops.md).

## Repeating-range note

`KeySpec.repeating_range(...)` exists in the typed spec layer, but the current
V1 Vigenere and Autokey bindings require fixed `repeating` keys.

Do not use `repeating_range` for a V1 solve until a variable-length runtime
binding exists.

See [KeySpec parameters](../reference/parameters/keys.md).
