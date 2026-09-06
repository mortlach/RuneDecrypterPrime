# Extending RDP

RDP is designed so that a solving idea can grow without changing the way the
experiment is described.

The same parts remain visible:

```text
cipher hypothesis
key model
search
scoring evidence
prior information
evaluation
reproducibility
```

Most solving work should use the existing public components. New code is needed
when the experiment requires a new capability.

## The two common extension jobs

For cipher work, the two jobs that recur most often are:

**Add or register the cipher behaviour.** Define the transform, implement the
runtime owner, register its internal identity and add a typed public binding if
the family is intended for normal users.

**Define how its key is searched.** Choose an existing KeyOps family or implement
the key operations required to keep candidate keys valid while Beam, GA or SA
moves through the space.

See [Cipher runtime and registration](../architecture/cipher_runtime_and_registration.md)
and [Key models and search operations](../architecture/key_model_and_search.md).


## New cipher

A new cipher hypothesis often begins as a focused experiment.

Retained scientific or diagnostic work belongs in `cipher_development/`.

Once the behaviour is understood well enough to become part of RDP, the
production implementation belongs under:

```text
src/rdp/ciphers/
```

A supported public cipher then receives the matching `CipherSpec` and compatible
key-space behaviour.

See [Cipher development](../development/cipher_development.md) and
[Add a cipher](../howto/add_cipher.md).

## New key structure

Key structure belongs with key operations.

If the existing repeating, range, permutation, scalar or periodic key spaces are
not enough, define the semantic key shape and the operations required by the
solver before adding another public constructor.

The key model should describe the real search space rather than one solver's
private representation.

See [Keys and key spaces](keyops.md).

## New solver

A new search algorithm belongs under:

```text
src/rdp/solvers/
```

Its public configuration belongs in `SolverSpec`.

The solver consumes the existing cipher, key and scoring contracts rather than
creating another run model.

See [Add a solver](../howto/add_solver.md) and [Solvers](solvers.md).

## New scoring evidence

New ranking evidence belongs in the scoring system.

RDP already separates character and WLI language-model evidence and provides
specialist Hamming, span-Hamming and word-n-gram facilities.

A new scoring feature should have a clear role in ranking or reporting,
explicit configuration, and tests showing what information it is allowed to
use.

Truth used only for evaluation stays outside production ranking.

See [Scoring](scoring.md).

## Experimental cipher maps

A small two-input relation or lookup-table cipher can be tested through:

```python
api.experimental.define_cipher_map(...)
api.experimental.define_cipher_lookup(...)
```

These definitions still use the normal `RunSpec` path.

See [Experimental ciphers](../reference/experimental.md).

## Comparing implementations

Keep the problem and evaluation fixed when comparing implementations.

If the question is whether a scorer helps, keep the cipher, key space and solver
fixed.

If the question is whether a solver explores the same problem more effectively,
keep the problem and evaluation fixed.

If the question is whether a cipher hypothesis is plausible, avoid changing the
evaluation at the same time.

`cipher_development/` contains focused retained investigations.

`tools/robustness/` is used when a method needs a repeatable campaign across many
cases.

A smoke check asks whether the path still works.

A qualification campaign asks whether the method is reliable enough for the
claim being made.

## Public API changes

The public surface is small.

An internal capability does not automatically require a new public abstraction.

Prefer the smallest typed constructor or configuration field that exposes the
new behaviour.

Avoid aliases, forwarding wrappers and parallel request types unless they solve
a demonstrated problem.

## Tests and documentation

A supported extension includes:

- focused tests for the new behaviour
- validation of invalid or incompatible input
- a public example when the feature needs one
- documentation for every new public parameter and default
- wider qualification only when the claim requires it

See [Contributing](../../CONTRIBUTING.md).

## Preserve the method

Extension should add capability without obscuring ownership.

The cipher still owns the cipher relation.

The key model still owns the search space.

The solver still owns search.

Scoring still owns ranking evidence.

Evaluation stays separate from production search.

Reproducibility records what actually ran.

Those ownership boundaries stop an experimental feature becoming a second
framework inside the first one.

For the wider design, see
[Project aims and design principles](../project_overview.md).

## Adding a scoring lane

Reuse the capability vocabulary in `src/rdp/core/component_contracts.py`, the
request owner in `src/rdp/core/config/scoring.py`, and the report owners in
`src/rdp/scoring/scorer_lane_report.py` and
`src/rdp/scoring/scorer_report_builder.py`.

Decide whether the lane changes production ranking, provides report-only
measurements, or records capability availability. Requested lanes must run,
block clearly, or report an explicitly authorised fallback. Report-only
measurements must not change ranking, stopping, tie-breaks or candidate selection.

Cover request detection, unavailable assets/runtime, allowed fallback, JSON-safe
reports and the report-only boundary with focused tests. Keep truth data outside
production scoring.
