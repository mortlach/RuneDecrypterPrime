# Key operations

Key operations define how solvers generate and change valid candidate keys.

Ordinary callers choose a key space through `api.KeySpec`. The runtime binds that
semantic key model to one of the KeyOps families implemented here.

Current families include vector, permutation, structured matrix and composite
operations.

The common capability vocabulary is owned by `base_keyops.py`:

```text
random
normalize
mutate
neighbor
recombine
make_population
batch_neighbors
local_improve
expand_position
```

Solvers use these capabilities rather than branching on key type.

See [Key models and search operations](../../../docs/architecture/key_model_and_search.md)
and [Build key operations](../../../docs/howto/build_keyops.md).
