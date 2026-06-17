# Rune Decrypter Prime docs

Rune Decrypter Prime (RDP) is a deterministic lab for testing decryption methods
on a 29-rune alphabet.

The point of the project is not just to get a high score. It is to make each run
repeatable and explainable:

```text
ciphertext
  -> optional pipeline transform
  -> cipher and key schedule
  -> scorer
  -> solver/search loop
  -> report, telemetry, and tutorial/test result
```

## First-time user path

1. Install: [`setup/installation.md`](setup/installation.md)
2. Run tutorials: [`guides/quickstart.md`](guides/quickstart.md)
3. If something fails: [`guides/troubleshooting.md`](guides/troubleshooting.md)

## Normal user docs

- [`setup/installation.md`](setup/installation.md) - install and first checks
- [`guides/quickstart.md`](guides/quickstart.md) - first tutorial run
- [`guides/troubleshooting.md`](guides/troubleshooting.md) - common failures
- [`guides/outputs.md`](guides/outputs.md) - generated reports, logs, and telemetry

## Expert and integrator docs

Use this path if you are an expert client, reviewer, or someone building a GUI or
overlay on top of RDP:

- [`expert/README.md`](expert/README.md) - expert reading order
- [`expert/design_philosophy.md`](expert/design_philosophy.md) - goals and motivations
- [`expert/component_model.md`](expert/component_model.md) - component boundaries
- [`expert/gui_frontend_interfaces.md`](expert/gui_frontend_interfaces.md) - front-end integration guidance
- [`expert/gui_interface_contract.md`](expert/gui_interface_contract.md) - practical GUI input/output contract
- [`expert/stability_surface.md`](expert/stability_surface.md) - stable versus non-stable surfaces

## Contract evidence used by tests

The folder below is intentionally retained because contract tests read it as
repo-local V1 evidence:

- [`release_contracts/v1/README.md`](release_contracts/v1/README.md)

That folder is not the beginner path and should not be treated as prose-only docs
cleanup. It is a test-backed drift lock. Do not delete or move it unless the
contract tests are updated at the same time.

## Existing technical reference

Some technical reference pages still exist while the docs are being cleaned up:

- [`architecture/engine_api.md`](architecture/engine_api.md)
- [`architecture/pipeline.md`](architecture/pipeline.md)
- [`architecture/ciphers.md`](architecture/ciphers.md)
- [`architecture/keyops.md`](architecture/keyops.md)
- [`architecture/optimisers.md`](architecture/optimisers.md)
- [`architecture/telemetry.md`](architecture/telemetry.md)
- [`architecture/data.md`](architecture/data.md)

These are useful for advanced readers, but the intended expert landing page is
now [`expert/README.md`](expert/README.md).
