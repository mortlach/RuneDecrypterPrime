# Cipher development

Ordinary solving asks whether an existing cipher, scorer and solver can explain
a piece of ciphertext.

Cipher development starts when the experiment itself needs to become part of
the project: a new cipher family, a new search operation, a scorer change, or a
repeatable workflow that needs stronger evidence than a one-off solve.

The wider extension model is described in
[Extending RDP](../guides/extending_rdp.md).

## Focused experiments

`cipher_development/` contains focused deterministic investigations.

The current runner is:

```text
python cipher_development/run_experiment.py
```

Its main choices are kept together in the script:

```python
EXPERIMENT = "autokey"
MODE = "smoke"
SEED = 20260822
OUTPUT_LOCATION = ...
```

`smoke` is the small deterministic check.

Longer development modes are used only for experiments that retain them.

Current retained experiments include Autokey replay, the two-period Pack 09
fixture, and the staged periodic-columnar investigation.

## Where each kind of work belongs

The project keeps three roles separate:

- `cipher_development/` for focused scientific or diagnostic experiments
- `src/rdp/` for production ciphers, scorers and solvers
- `tools/robustness/` for repeatable multi-case qualification

That follows the same structure as an ordinary solve.

The hypothesis, key model, search, scoring evidence and evaluation should remain
recognisable as the experiment grows.

See [Comparing solve experiments](../guides/working_a_solve.md) and
[Project aims and design principles](../project_overview.md).

## Evidence

Development experiments use explicit seeds and fixed recipes or profiles.

Known plaintext and known keys may be used to classify a completed benchmark
result. They do not belong in production candidate ranking or selection unless
the experiment is explicitly an oracle-guided method.

Generated output stays outside maintained source.

For the replay side, see
[Repeating a run](../guides/reproducibility.md).

For execution evidence, see [Telemetry](../guides/telemetry.md).

## Adding a cipher

A new cipher normally moves through three stages:

1. investigate the behaviour in a focused experiment
2. implement the production owner under `src/rdp/ciphers/`
3. add the typed public `CipherSpec` and compatible `KeySpec` route when the
   family is ready for the public API

See [Add a cipher](../howto/add_cipher.md).

The public constructors are listed in
[Cipher parameters](../reference/parameters/ciphers.md) and
[Key parameters](../reference/parameters/keys.md).
