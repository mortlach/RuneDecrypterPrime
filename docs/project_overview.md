# Project aims and design principles

RDP exists to make cryptanalytic experiments easier to express, compare and
repeat.

The project grew from Liber Primus solving work into a general run model for
cipher search. The aim is not to hide cryptanalysis behind one solver call. It
is to keep the important parts of the problem explicit.

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

The model is small.

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

RDP therefore keeps oracle and truth information separate from normal ranking,
stopping and tie-breaking. A known answer may classify the result after the run.
If a method intentionally uses truth during search, that is a different
experiment and should be described as such.

That distinction determines what a solver result can claim.

## One owner for each capability

Each major behaviour has one implementation owner.

Ciphers own the cipher relation. Key operations own the key model. Solvers own
search. Scoring owns ranking evidence. Data modules own source material.
Telemetry records execution behaviour.

The public API binds those pieces together without becoming a second
implementation of them.

Extension stays with the owner of the behaviour rather than creating a parallel
runtime path.

See [Architecture overview](architecture/overview.md).

## Defaults are explicit

RDP uses defaults where there is a clear general choice.

Those defaults are documented and validated. A caller can override them where
the problem requires something different.

A requested value is not silently replaced merely because another option is
available. If a requested scorer lane, device, asset or other capability cannot
run, that should be visible.

See [Defaults at a glance](reference/defaults.md).

## Advanced features stay optional

A first run does not require knowledge of every scoring lane, solver control,
artifact type or development tool.

More specialised features are available when the problem needs them:

- multiple solver families
- WLI-aware scoring
- interruptor search
- Hamming and span-Hamming scoring
- two-period crib search
- custom experimental cipher maps
- direct Liber Primus source routing
- telemetry and run artifacts

The main run model does not change when these features are added.

## Extensibility without another framework

A new cipher belongs with the cipher implementation.

A new search method should become a solver.

A new scoring signal should become part of scoring.

A new source should become part of the data layer.

The project avoids speculative abstraction layers, duplicate request models and
compatibility wrappers where the existing ownership model is enough.

See [Extending RDP](guides/extending_rdp.md).

## From solving to development

A typical path is:

```text
solving experiment
-> focused cipher development
-> production implementation
-> focused tests
-> robustness or qualification
```

At each stage, the same things should remain visible: cipher relation, key
structure, search, scoring evidence, prior information and the claim being
tested.

`cipher_development/` is used for bounded scientific or diagnostic experiments.

Production implementations belong under `src/rdp/`.

Repeatable multi-family qualification belongs under `tools/robustness/`.

See [Development](development/README.md).

## Community use

V1 is intended to stand outside the development environment that produced it.

The public API, documentation, examples, data access, errors and reproducibility
information therefore need to be understandable without knowing the project's
internal history.

The aim is a stable base for testing, sharing and extending cryptanalytic ideas,
not a frozen set of solver recipes.

For the current public surface, see [API reference](reference/README.md).

A short account of the project's earlier generations is kept in
[Project origins](project_origins.md).
