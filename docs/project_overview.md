# Project aims and design principles

RDP makes cryptanalytic experiments easier to express, compare and repeat. Its
run model keeps the important parts of a cipher search explicit instead of
hiding them behind one solver call.

## The problem

A practical cipher experiment combines several different questions:

- what text is being solved
- which cipher family is being tested
- what is known about the key
- how the key space is searched
- what evidence ranks candidate plaintexts
- what prior information is allowed
- what counts as recovery
- what must repeat for the result to be trusted

When those choices are spread across scripts, globals and one-off helper code,
it becomes difficult to tell which change produced a result.

RDP gives them a common structure:

```text
problem input
-> cipher
-> key space
-> solver
-> scoring
-> RunResult
```

## One method from experiment to qualification

The same structure is used at different scales.

A short solving script, a cipher-development experiment and a qualification
campaign may use very different amounts of compute, but they still need to
answer the same questions:

```text
cipher hypothesis
key model
search
scoring evidence
prior information
evaluation
reproducibility
```

A promising idea can therefore move from a small comparison into focused
development, production code and wider qualification without being rewritten
into a different conceptual framework.

The machinery becomes more capable. The experiment should remain legible.

## RunSpec records the experiment

The public `RunSpec` records the durable choices for one run.

That includes the input, cipher, key space, solver and scoring configuration,
along with text direction, WLI policy, initial keys, interruptors, compute
device, telemetry and other explicit controls.

The result can then report both the candidate and the configuration that
produced it.

See [Defining a run](guides/anatomy_of_a_run.md) and
[RunSpec parameters](reference/parameters/run_spec.md).

## Determinism is part of the method

Reproducibility is not only a reporting concern.

Seeds, effective configuration, asset information and run metadata are part of
the execution model.

Exploratory work does not always require bit-for-bit replay. It does require
enough information to make controlled comparisons and to reconstruct an
important result later.

Tests and qualification runs may impose a stricter contract.

See [Repeating a run](guides/reproducibility.md).

## Known truth is separate from production search

Known plaintext and known keys are valuable for development and evaluation.

They are also easy to leak into candidate selection.

RDP keeps oracle and truth information separate from normal ranking, stopping
and tie-breaking. A known answer may classify the result after the run. If a
method intentionally uses truth during search, that is a different experiment
and should be described as such.

That distinction determines what a solver result can claim.

## Ownership and extension

Each major behaviour has one implementation owner.

Ciphers own the cipher relation. Key operations own the key model. Solvers own
search. Scoring owns ranking evidence. Data modules own source material.
Telemetry records execution behaviour.

The public API binds those pieces together without becoming a second
implementation. New behaviour stays with its owner: a cipher relation belongs
with ciphers, a search method with solvers, and a scoring signal with scoring.
This avoids parallel request models and compatibility layers where the existing
boundary is enough.

A first run need not configure every scoring lane, solver control, artifact type
or development tool. Defaults cover ordinary choices and are documented and
validated. More specialised features use the same `RunSpec` when the problem
needs them, including WLI-aware scoring, interruptor search, two-period crib
search, custom cipher maps and direct Liber Primus source routing.

A requested value is not silently replaced merely because another option is
available. If a requested scorer lane, device, asset or other capability cannot
run, that should be visible.

See [Architecture overview](architecture/overview.md),
[Defaults at a glance](reference/defaults.md) and
[Extending RDP](guides/extending_rdp.md).

## From solving to development

A typical path is:

```text
solving experiment
-> focused cipher development
-> production implementation
-> focused tests
-> robustness or qualification
```

At each stage, the cipher relation, key structure, search, scoring evidence,
prior information and claim being tested should remain visible.

`cipher_development/` is used for bounded scientific or diagnostic experiments.

Production implementations belong under `src/rdp/`.

Repeatable multi-family qualification belongs under `tools/robustness/`.

See [Development](development/README.md).

The public API, documentation, examples, data access, errors and reproducibility
information must stand on their own outside any one development environment.
V1 is a base for testing, sharing and extending cryptanalytic ideas, not a
frozen set of solver recipes. See [API reference](reference/README.md) for the
current public surface.
