# Build key operations

Key operations define how a solver moves through a valid key space.

For a new cipher, define what the key means first. Then define how a solver can
change it without breaking that meaning.

For the architecture first, read
[Key models and search operations](../architecture/key_model_and_search.md).

## 1. Define the semantic key

Write down the concrete key layout before writing mutation code.

Examples:

```text
repeating vector:       [k0, k1, ... kN]
permutation:            permutation of 0..N-1
periodic substitution:  P permutation blocks of alphabet size A
periodic columnar:      P substitution blocks + one column permutation
```

State the invariants and concrete length.

The public `KeySpec` should describe this semantic space when the family is
public.

## 2. Choose an existing KeyOps family if it fits

Current runtime families are:

```text
vector
permutation
matrix
composite
```

Do not create a new family because one cipher has a new name.

Use the existing family when the valid key structure and solver moves are
already represented correctly.

## 3. Implement the basic verbs

A KeyOps implementation must provide:

```text
random
normalize
mutate
caps.length
```

The base contract can also expose:

```text
neighbor
recombine
make_population
batch_neighbors
local_improve
expand_position
```

The implementation advertises supported operations through its capabilities.

Solvers use those capabilities rather than branching on key type.

## 4. Preserve invariants

For a vector key, values remain inside the configured numeric domain.

For a permutation key, every mutation and recombination must still produce a
permutation.

For a structured periodic key, each permutation block and optional column tail
must remain valid.

For a composite interruptor key, both the core key and interruptor segment must
remain valid.

A mutation that routinely creates invalid keys is the wrong operation for that
key model.

## 5. Give the solver appropriate moves

Correctness is necessary but not enough.

A good move set has:

- local moves for refinement
- enough coverage to reach the intended search space
- deterministic behaviour under the supplied RNG
- batch forms where they materially improve search/scoring throughput

Beam benefits from meaningful `expand_position` or `batch_neighbors`.

GA benefits from `make_population`, `recombine` and `mutate`.

SA benefits from a local `neighbor`.

See [Solver mechanics](../architecture/solver_mechanics.md).

## 6. Register only when a new family is genuinely needed

Runtime KeyOps construction uses the existing family registry.

Adding a new family means adding a real new key-operation contract, not merely
another alias.

Registration should be strict and explicit. Existing families should not be
silently replaced by import order.

## 7. Bind the public key model

For a public cipher family, update the cipher/key compatibility rules and
concrete-key validation so `KeySpec` and the runtime KeyOps agree.

The public request should remain the source of truth. Runtime hints are derived
from it.

See [Cipher runtime and registration](../architecture/cipher_runtime_and_registration.md).

## 8. Test it

Focused tests include:

- `random()` always produces valid keys
- `normalize()` is deterministic and preserves the required shape
- `mutate()` preserves invariants
- `neighbor()` and `recombine()` preserve invariants when implemented
- fixed seeds reproduce the same generated candidates
- the intended solver can search the key family
- invalid concrete keys fail clearly

For production cipher work, continue with [Add a cipher](add_cipher.md).
