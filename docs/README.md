# Rune Decrypter Prime documentation

RDP is a deterministic cryptanalysis toolkit: one typed public request goes in;
a result, stop status and reproducibility record come out. The documents are
arranged for technically capable readers who are new to RDP, not new to using a
computer.

## First route

Read these in order:

1. [`setup/installation.md`](setup/installation.md)
2. [`guides/quickstart.md`](guides/quickstart.md)
3. [`guides/runes_and_text.md`](guides/runes_and_text.md)
4. [`../tutorials/v1/README.md`](../tutorials/v1/README.md)
5. [`guides/outputs.md`](guides/outputs.md)
6. [`guides/troubleshooting.md`](guides/troubleshooting.md)

The first three runnable stops cover known-key operations, a small search and a
repeating-key search. Four further stops make repeatability, interruptors,
partial recovery and named Liber Primus sources concrete.

## Guides

- [`guides/pipeline.md`](guides/pipeline.md) — how a run moves through RDP.
- [`guides/scoring.md`](guides/scoring.md) — what scores mean and do not mean.
- [`guides/solvers.md`](guides/solvers.md) — choosing a supported search.
- [`guides/telemetry.md`](guides/telemetry.md) — progress and evidence.
- [`guides/liber_primus_typed_workflows.md`](guides/liber_primus_typed_workflows.md)
  — source-labelled LP work.
- [`guides/liber_primus_solved_sources.md`](guides/liber_primus_solved_sources.md)
  — known solved-source boundaries.

## Reference and extension work

- [`architecture/overview.md`](architecture/overview.md) — architecture map.
- [`expert/README.md`](expert/README.md) — integrator and reviewer route.
- [`howto/add_cipher.md`](howto/add_cipher.md) — add a cipher deliberately.
- [`howto/add_solver.md`](howto/add_solver.md) — add a solver deliberately.
- [`tests/overview.md`](tests/overview.md) — test layout.
- [`ROADMAP.md`](ROADMAP.md) — active follow-up work, including the deferred
  P7/C7 scientific campaign decision.

## Contract evidence

[`release_contracts/v1/`](release_contracts/v1/) is retained because tests use
it to stop the V1 contract drifting. It records why the surface looks as it
does. It is not required reading before the first run.
