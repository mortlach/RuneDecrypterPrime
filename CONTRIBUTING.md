# Contributing

RDP has one public Python entry point:

```python
from rdp import api
```

Public examples and callers should stay on that surface. Contributors working
inside the implementation should import the module that actually owns the
behaviour they need.

## Working rules

- Reuse or repair an existing owner before adding another abstraction.
- Keep the public request model typed. Do not add compatibility aliases,
  forwarding modules, parallel request models or silent fallbacks.
- Preserve reproducibility. Use the supplied RNG and explicit seeds where
  randomness matters, and report requested versus effective behaviour.
- Keep truth and known-answer data out of production ranking, stopping,
  tie-breaks and candidate selection unless a documented oracle mode explicitly
  says otherwise.
- Change the implementation, focused tests and relevant documentation together.
- Start with the smallest tests that exercise the behaviour you changed. Long
  robustness and qualification campaigns are separate work, not routine checks.
- Keep generated output, logs, downloaded assets and review material outside the
  maintained source tree.

## Where to start

- [`docs/architecture/`](docs/architecture/) explains how the runtime pieces fit
  together.
- [`docs/howto/`](docs/howto/) contains task-focused extension guides.
- [`src/rdp/README.md`](src/rdp/README.md) maps the installed package and its
  implementation owners.
- [`tests/README.md`](tests/README.md) explains how to choose focused tests.
- [`tools/README.md`](tools/README.md) describes repository utilities and
  validation tools.

For changes to the supported V1 surface, also check the test-backed contract
evidence under [`docs/release_contracts/v1/`](docs/release_contracts/v1/).
