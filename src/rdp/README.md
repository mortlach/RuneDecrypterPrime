# RDP package

RDP brings a cipher, a candidate key space, a search method and scoring evidence together in one repeatable run. This is the installed Python package. Start at the public API, then follow the domain that answers your question.

## Where to look

- [api/](api/) — Public requests, known-key operations and results.
- [ciphers/](ciphers/) — Transform text using a supplied key.
- [keyops/](keyops/) — Generate and change valid candidate keys.
- [solvers/](solvers/) — Explore those candidates.
- [scoring/](scoring/) — Rank decrypted candidates using configured evidence.
- [core/](core/) — Bind the components and execute the run.
- [data/](data/) — Rune conversion, named LP sources and asset paths.
- [backends/](backends/) — Array and device support.
- [telemetry/](telemetry/) — Structured progress and execution metadata.
- [io/](io/) — Log files, artifact paths and random streams.

## Choices and extension

Normal callers use `from rdp import api`. Choose a cipher and compatible key space before selecting a solver; each domain below explains the choices it owns. Internal module paths are contributor interfaces, not additional public entry points.

Continue with the [guide](../../docs/guides/anatomy_of_a_run.md).
