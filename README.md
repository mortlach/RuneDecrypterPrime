# Rune Decrypter Prime

Rune Decrypter Prime (RDP) is a deterministic cryptanalysis toolkit for a
29-rune alphabet.

The project is built around small, testable parts: ciphers, key schedules,
scorers, solvers, tutorial runs, and reports. The aim is to make decryption
experiments repeatable rather than mysterious.

This branch is the V1 pre-release surface. It focuses on:

- a clean Python install path
- ScheduledStreamLookup cipher support
- Span-Hamming support
- deterministic tutorials
- traceable solver/scorer reports
- Windows and Ubuntu CI proof
- wheel builds with native extension import checks

## Start here

For most users:

1. Install: [`docs/setup/installation.md`](docs/setup/installation.md)
2. Run the V1 tutorials: [`docs/guides/quickstart.md`](docs/guides/quickstart.md)
3. Read the project overview: [`docs/README.md`](docs/README.md)

The shortest install check is:

```text
python install.py
```

On Windows, this wrapper is also available:

```text
install.bat
```

## Common paths

```text
src/rune_decrypter_prime/   package source
tutorials/v1/               V1 tutorial scripts and tutorial runner
tests/                      pytest test suite
docs/                       user, setup, architecture, and test notes
assets/                     small V1 asset baseline
output/                     generated logs and test/tutorial output
```

`output/` is local runtime output and should not be committed.

## Main docs

- [`docs/README.md`](docs/README.md) - project overview and architecture links
- [`docs/setup/installation.md`](docs/setup/installation.md) - simple install, tutorial run, and expert test commands
- [`docs/setup/building.md`](docs/setup/building.md) - wheel/native build notes
- [`docs/guides/quickstart.md`](docs/guides/quickstart.md) - first tutorial run
- [`docs/guides/troubleshooting.md`](docs/guides/troubleshooting.md) - common failures
- [`docs/tests/overview.md`](docs/tests/overview.md) - test-suite overview
- [`docs/release_contracts/v1/README.md`](docs/release_contracts/v1/README.md) - required V1 release-contract data

## Developer notes

Python 3.11+ is the supported target for V1.

The public V1 boundary is intentionally narrow. Experimental n-gram Hamming
campaign work, large benchmark runs, and save/restore solver state are not part
of the V1 production surface.
