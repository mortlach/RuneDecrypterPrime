# Add a solver

A solver chooses which candidate keys to try next.

It should reuse the existing cipher, KeyOps, candidate-evaluation and scoring
boundaries rather than introduce another way to represent the problem.

Read [Solver mechanics](../architecture/solver_mechanics.md) first.

## 1. Define the search algorithm

State:

```text
what state the solver keeps
how it proposes the next candidate
what KeyOps capabilities it requires
what budget controls it exposes
how it stops
what deterministic seed behaviour it promises
```

If the difference is only a new budget or option for an existing solver, extend
that solver rather than adding a family.

## 2. Use SolverBase and the shared problem

Generic production solvers live under:

```text
src/rdp/solvers/
```

They receive the materialised problem, supplied RNG, optional initial keys,
stopping controls and progress hooks.

Candidate keys should be evaluated through the shared scoring/evaluation helper.

Do not call a private scorer or duplicate cipher handling inside the solver.

See [Candidate evaluation](../architecture/candidate_evaluation.md).

## 3. Use KeyOps capabilities

A solver should not ask:

```text
is this a permutation key?
```

It should ask whether the selected KeyOps supports the operation it needs.

Typical capabilities include:

```text
random
neighbor
mutate
recombine
make_population
batch_neighbors
expand_position
```

See [Key models and search operations](../architecture/key_model_and_search.md).

## 4. Use the supplied RNG

All random choices use the RNG supplied by the engine.

Creating a fresh RNG inside the solver breaks the run's reproducibility
contract.

## 5. Report progress and stopping

Use the shared progress and telemetry path.

Return the common solution/result structure and a truthful stop reason.

A normal budget stop is not an assertion of recovery.

## 6. Connect the runtime implementation

The runtime engine has an internal solver identity and implementation table.

Adding a runtime class is separate from adding a public `SolverSpec` family.

## 7. Add the public binding only when intended

A public solver family needs:

- `SolverKind`
- typed `SolverSpec` construction and validation
- public-to-runtime parameter translation
- stop/report conversion
- contract tests
- parameter documentation
- an example when it teaches a genuinely new workflow

The public and internal solver enums are deliberately separate.

## 8. Test it

Focused tests should cover:

- fixed-seed repeatability
- required KeyOps capabilities
- valid candidate evaluation
- initial keys
- stopping conditions
- tied-score behaviour where relevant
- work counters and telemetry
- failure on incompatible configuration

Broader qualification belongs under the robustness tooling, not the tutorial
suite.
