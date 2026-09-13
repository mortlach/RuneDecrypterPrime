# Cipher development

A new cipher or search idea does not have to start as a new RDP feature.

The quickest way to begin is the same as ordinary solving: pick a concrete
target, write the smallest experiment that tests the idea, and see what happens.
You can do a lot of useful work with a normal script using `from rdp import api`.

If the idea survives first contact with the data, then it may be worth turning
into something more systematic.

The wider extension model is described in
[Extending RDP](../guides/extending_rdp.md).

## Start with something you can run

For a new method, I normally want one small example before I want new framework
code.

That might be:

- one LP input and one parameter choice
- a solved section where the expected answer is known
- a small comparison between two versions of the same idea

Solved material is especially useful early on. If a search cannot recover a
known answer under a sensible setup, that is often more informative than a long
unsolved run.

The [Solved LP workbook](../../solving/solved_lp/README.md) and
[Liber Primus attempts](../../solving/attempts/README.md) give both sides of that
workflow.

## When the method becomes worth keeping

The more structured development practices in this repository came from trying
to keep complicated work understandable while RDP itself was changing.

While developing the Kaeding, periodic-columnar and overlapping two-period
work, I found a few things repeatedly useful:

- keep the exact input that produced an important result
- keep one known working case around while changing the implementation
- record the choices that materially affect the search
- make random searches repeatable when comparing versions
- change one thing at a time when that is practical
- keep the known answer for evaluation rather than accidentally feeding it into
  production ranking
- if a retained result changes, treat that as a reason to investigate rather
  than silently accepting the new answer

Once a method had become stable enough to keep, some experiments were pinned
more tightly: fixed recipes, seeds, budgets, or even a fixture dependency
closure. That was useful because it made drift visible.

Qualification came later. It answered a different question: not "can this method
work here?" but "how reliably does this recipe work across the cases we care
about?"

This is the background to the stricter-looking material under
`cipher_development/` and `tools/robustness/`. It grew out of the development
work rather than being where a new idea has to begin.

## Focused experiments in this repository

`cipher_development/` keeps a small number of investigations that were useful
enough to retain after the production behaviour had stabilised.

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

`smoke` is the small deterministic check. Longer development modes are retained
only where they still tell us something useful.

Current retained experiments include Autokey replay, the two-period Pack 09
fixture, and the staged periodic-columnar investigation.

## Where the work tends to end up

As an experiment matures, different parts naturally belong in different places:

- a one-off or community LP test can live under `solving/attempts/`
- focused development that is still answering a scientific or implementation
  question can live under `cipher_development/`
- production ciphers, scorers and solvers live under `src/rdp/`
- broader multi-case qualification lives under `tools/robustness/`

There is no need to move an experiment through every one of those locations.
They are places for different kinds of work, not a mandatory ladder.

See [Comparing solve experiments](../guides/working_a_solve.md) and
[Project aims and design principles](../project_overview.md).

## Evidence when it matters

For a small experiment, a visible script and input may be enough.

As the claim grows, more context becomes useful: seeds, budgets, starting
points, scoring, assets, and the distinction between information used during the
search and truth used afterwards to judge it.

Known plaintext and known keys are excellent development tools. The important
thing is to know whether they helped choose the result or only checked it after
the run.

Generated output stays outside maintained source.

For replay, see [Repeating a run](../guides/reproducibility.md).

For execution evidence, see [Telemetry](../guides/telemetry.md).

## Turning a method into an RDP feature

If an experiment becomes useful beyond the original script, then it may be time
to implement it as maintained behaviour.

A new cipher usually means:

1. make sure the cipher relation itself is understood
2. implement the production owner under `src/rdp/ciphers/`
3. add the public `CipherSpec` and compatible `KeySpec` route when the interface
   is ready
4. add focused tests that prove the maintained behaviour

See [Add a cipher](../howto/add_cipher.md).

The public constructors are listed in
[Cipher parameters](../reference/parameters/ciphers.md) and
[Key parameters](../reference/parameters/keys.md).
