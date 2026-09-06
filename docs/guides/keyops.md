# Keys and key spaces

A concrete key, a key space and key operations are three different things.

That distinction matters once a solver is involved.

## Concrete key

A concrete key is one actual candidate:

```python
key: api.ConcreteKey = (3, 1, 4)
```

When the key is already known:

```python
plaintext = api.decrypt(
    ciphertext,
    cipher=cipher,
    key=key,
)
```

No solver is needed.

See [Known-key encrypt and decrypt](../reference/known_key.md).

## Key space

When the key is unknown, `KeySpec` describes the allowed search space.

A fixed repeating key:

```python
key_space = api.KeySpec.repeating(
    length=7,
)
```

A permutation key:

```python
key_space = api.KeySpec.permutation(
    length=7,
)
```

A scalar range:

```python
key_space = api.KeySpec.scalar(
    minimum=2,
    maximum=8,
)
```

Structured periodic key spaces have their own constructors.

The complete public list is in
[KeySpec parameters](../reference/parameters/keys.md).

## Why key type changes the search

The solver needs ways to move from one valid key to another.

Those moves depend on the key structure.

A repeating vector can change one value while keeping the rest fixed.

A permutation cannot replace one element with an arbitrary value because that
would stop being a permutation. Its mutation must swap or reorder existing
elements.

A periodic-substitution key contains several permutation blocks, so mutation
has to preserve each block separately.

RDP handles this through runtime **KeyOps**.

The public caller chooses `KeySpec`. The runtime supplies the matching key
operations.

## Solver moves

KeyOps can provide operations such as:

```text
random
mutate
neighbor
recombine
make_population
batch_neighbors
expand_position
```

Beam search uses expansion or neighbours.

GA uses population generation, recombination and mutation.

SA follows neighbouring keys.

The solver therefore asks for a legal move without hard-coding the key type.

For the full mechanism, see
[Key models and search operations](../architecture/key_model_and_search.md).

## Starting keys

`RunSpec.initial_keys` supplies candidate keys to a solver that supports them:

```python
request = api.RunSpec(
    ...,
    initial_keys=(
        (1, 4, 9, 16, 25, 7, 20),
    ),
)
```

The runtime validates those keys against the same key model before search.

A warm-started solve demonstrates something different from finding the same
region without that starting information.

See [Comparing solve experiments](working_a_solve.md) and
[Repeating a run](reproducibility.md).

## Runnable examples

`tutorials/v1/getting_started/03_repeating_key_search.py` introduces a repeating
key search.

The first tutorial, `01_known_key.py`, shows the concrete-key path without a
solver.

See [Tutorials and examples](../tutorials/README.md).

## Extending key behaviour

Contributor work on a new key structure starts with the semantic layout and
invariants, then implements the operations the intended solvers need.

See [Build key operations](../howto/build_keyops.md).
