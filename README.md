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
docs/                       user, expert, and contract-evidence docs
assets/                     small V1 asset baseline
output/                     generated logs and test/tutorial output
```

`output/` is local runtime output and should not be committed.

## User docs

- [`docs/README.md`](docs/README.md) - docs map and reading order
- [`docs/setup/installation.md`](docs/setup/installation.md) - simple install and tutorial run
- [`docs/guides/quickstart.md`](docs/guides/quickstart.md) - first tutorial run
- [`docs/guides/troubleshooting.md`](docs/guides/troubleshooting.md) - common failures

## Expert and integration docs

- [`docs/expert/README.md`](docs/expert/README.md) - expert reading order
- [`docs/expert/design_philosophy.md`](docs/expert/design_philosophy.md) - goals and motivations
- [`docs/expert/component_model.md`](docs/expert/component_model.md) - component boundaries
- [`docs/expert/gui_frontend_interfaces.md`](docs/expert/gui_frontend_interfaces.md) - GUI/front-end guidance
- [`docs/expert/gui_interface_contract.md`](docs/expert/gui_interface_contract.md) - practical GUI contract
- [`docs/expert/stability_surface.md`](docs/expert/stability_surface.md) - stable versus non-stable surfaces

## Contract evidence used by tests

The release-contract folder is not the beginner docs path. It is retained because
contract tests read it as repo-local evidence to stop V1 drift:

- [`docs/release_contracts/v1/README.md`](docs/release_contracts/v1/README.md)

Do not delete or move that folder without updating the corresponding contract
tests.

## Developer notes

Python 3.11+ is the supported target for V1.

The public V1 boundary is intentionally narrow. Experimental n-gram Hamming
campaign work, large benchmark runs, and save/restore solver state are not part
of the V1 production surface.
