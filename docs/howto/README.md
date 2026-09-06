# How-to guides

These pages are for changes to RDP itself.

For normal solving, start with [Defining a run](../guides/anatomy_of_a_run.md).

## Cipher work

[Add a cipher](add_cipher.md) covers the production route.

For exploratory work, see
[Cipher development](../development/cipher_development.md).

The public constructors are listed in
[Cipher parameters](../reference/parameters/ciphers.md) and
[Key parameters](../reference/parameters/keys.md).

## Key operations

[Build key operations](build_keyops.md) covers the runtime operations used by
solvers to search valid keys.

See [Keys and key spaces](../guides/keyops.md) for the public model and
[Key models and search operations](../architecture/key_model_and_search.md) for
the runtime binding.

## Solver work

[Add a solver](add_solver.md) covers a new search algorithm.

See [Solvers](../guides/solvers.md) and
[Solver mechanics](../architecture/solver_mechanics.md).

## Wider extension model

See [Extending RDP](../guides/extending_rdp.md) and
[Project aims and design principles](../project_overview.md).
