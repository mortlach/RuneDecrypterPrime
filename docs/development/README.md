# Development

This section is for work that goes beyond configuring an ordinary solve.

The main route is:

```text
solving question
-> focused experiment
-> production implementation
-> focused tests
-> wider robustness or qualification when needed
```

The same cipher, key, search, scoring and evaluation boundaries used by the
public API should remain visible during development.

See [Project aims and design principles](../project_overview.md) for the
reasoning behind that model, and [Architecture](../architecture/README.md)
for the implementation view.

## Cipher development

[Cipher development](cipher_development.md) explains the retained
`cipher_development/` workspace and where focused investigations belong.

For a new production cipher, continue with
[Add a cipher](../howto/add_cipher.md).

## AI-assisted development

AI coding tools are already part of RDP's development workflow, and they can be
useful for reading the API, building a first experiment, expanding tests or
checking code and documentation against each other.

The useful boundary is not who typed the code. The input, code and result should
still be inspectable and independently verifiable.

See [AI-assisted development](ai_assisted_workflow.md) for the practical workflow
that has worked well on RDP.

## Solvers and key operations

New search behaviour belongs with the solver implementation and public
`SolverSpec` when it becomes supported.

See [Add a solver](../howto/add_solver.md).

New key structure or mutation behaviour belongs with key operations.

See [Build key operations](../howto/build_keyops.md).

## Runtime and installation work

- [CUDA setup](cuda_installation.md)
- [Output locations](output_locations.md)
- [Installation](../setup/installation.md)
- [Install validation](../setup/install_validation.md)

## Release validation

The [full-proof workflow](../../.github/workflows/rdp_v1_full_proof.yml) is the
executable release authority. It runs automatically on pushes to `main` and
supports manual `workflow_dispatch`. Before publication, select the frozen
candidate ref and verify the run's checked-out commit matches the intended SHA.

Full proof installs `full_v1` assets and runs the unchanged
[canonical validator](../../tools/run_validation.py): 53 jobs, including the
production P7/C7 example. It also runs the separate `FULL_ASSET_EXAMPLES` tutorial
group and native-wheel and Pyodide checks. All required jobs and the final proof
summary must pass; uploaded evidence must identify the same source SHA.
The workflow records native and WebAssembly artifact checksums.

Hosted CPU proof does not qualify CUDA. Any CUDA release claim needs separate
machine-specific evidence. Ordinary push/PR CI stays on the cheap
[CI-light selection](../setup/install_validation.md#normal-ci); use full proof
for a release candidate, not as a routine documentation check.

## Public behaviour

A public change is not complete when only the implementation works.

The related public constructor or configuration, tests, examples, defaults and
documentation need to describe the same behaviour.

Use the [API reference](../reference/README.md) and
[Parameter reference](../reference/parameters/README.md) to check that surface.

## Understand the runtime before extending it

The advanced architecture pages follow the main extension boundaries:

- [Key models and search operations](../architecture/key_model_and_search.md)
- [Cipher runtime and registration](../architecture/cipher_runtime_and_registration.md)
- [Solver mechanics](../architecture/solver_mechanics.md)
- [Candidate evaluation](../architecture/candidate_evaluation.md)
- [Scoring and language models](../architecture/scoring_and_language_models.md)

For most new cipher work, start with the first two.

