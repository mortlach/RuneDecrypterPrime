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

## What V1 is about

V1 keeps the public surface small enough to test properly.

Included in V1:

- stable package install
- API wrappers for supported ciphers
- ScheduledStreamLookup tutorials and smoke tests
- Span-Hamming support
- scorer/report diagnostics
- deterministic tutorial runner
- Windows and Ubuntu full CI
- Windows and Ubuntu wheel CI

Not included in V1:

- production n-gram Hamming scoring
- large campaign assets as default install payload
- save/restore solving state
- broad experimental benchmark branches

## First-time user path

1. Install: [`setup/installation.md`](setup/installation.md)
2. Run tutorials: [`guides/quickstart.md`](guides/quickstart.md)
3. If something fails: [`guides/troubleshooting.md`](guides/troubleshooting.md)

## More detail

Architecture:

- [`architecture/engine_api.md`](architecture/engine_api.md)
- [`architecture/pipeline.md`](architecture/pipeline.md)
- [`architecture/ciphers.md`](architecture/ciphers.md)
- [`architecture/keyops.md`](architecture/keyops.md)
- [`architecture/optimisers.md`](architecture/optimisers.md)
- [`architecture/telemetry.md`](architecture/telemetry.md)
- [`architecture/data.md`](architecture/data.md)

Testing and traceability:

- [`tests/overview.md`](tests/overview.md)
- [`v1_traceability/README.md`](v1_traceability/README.md)

Build and packaging:

- [`setup/installation.md`](setup/installation.md)
- [`setup/building.md`](setup/building.md)
