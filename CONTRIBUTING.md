# Contributing

RDP has one public Python entry point:

```python
from rdp import api
```

Public examples and callers should stay on that surface.

Contributors working inside the implementation should use the module that owns
the behaviour they need. A new capability should normally extend an existing
cipher, key, solver, scoring, data or reporting owner rather than create another
route around it.

The reasoning behind that structure is described in
[Project aims and design principles](docs/project_overview.md) and
[Extending RDP](docs/guides/extending_rdp.md).

## Working rules

- Reuse or repair an existing owner before adding another abstraction.
- Keep the public request model typed.
- Do not add compatibility aliases, forwarding modules, parallel request models
  or silent fallbacks without a demonstrated need.
- Preserve reproducibility. Use explicit seeds where randomness matters and
  record requested and effective behaviour.
- Keep truth and known-answer data out of production ranking, stopping,
  tie-breaks and candidate selection unless the method explicitly requires
  oracle guidance.
- Change the implementation, focused tests and relevant documentation together.
- Start with the smallest tests that exercise the behaviour being changed.
- Keep long robustness and qualification campaigns separate from routine checks.
- Keep generated output, logs, downloaded assets and review material outside the
  maintained source tree.

### Pack 09 fixture-manifest gate

The Pack 09 fixture manifest records SHA-256 content hashes, not Git commit
IDs. Before pushing, run:

```text
python tools/refresh_two_period_fixture_manifest.py
pytest -q tests/contracts/test_two_period_fixture_manifest.py
```

Whenever a retained file under `cipher_development/shared/` or
`cipher_development/two_period_overlay/` changes, including through formatting
or line-ending conversion, commit the refreshed
`docs/release_contracts/v1/two_period_fixture_manifest.json` in the same commit.
Review any dependency-closure change rather than accepting it mechanically.

These are mostly consequences of the same rule: make it possible to tell what
changed and what a result demonstrates.

## Where to start

For project structure:

- [Project overview](docs/project_overview.md)
- [Architecture overview](docs/architecture/overview.md)
- [Extending RDP](docs/guides/extending_rdp.md)
- [Development map](docs/development/README.md)

For specific work:

- [Add a cipher](docs/howto/add_cipher.md)
- [Add a solver](docs/howto/add_solver.md)
- [Build key operations](docs/howto/build_keyops.md)
- [Cipher development](docs/development/cipher_development.md)

For repository work:

- [Tests](tests/README.md)
- [Repository tools](tools/README.md)
- [Robustness campaigns](tools/robustness/README.md)

For the public surface:

- [API reference](docs/reference/README.md)
- [Parameter reference](docs/reference/parameters/README.md)
- [Tutorials and examples](docs/tutorials/README.md)

## Evidence and testing

A focused implementation test answers whether the changed behaviour works.

A smoke experiment answers whether a larger path still works end to end.

A robustness or qualification campaign answers a broader scientific or release
question across many cases.

Do not use a larger campaign where a focused test answers the question.

Likewise, do not use a small smoke result to support a claim that requires
multi-case evidence.

The distinction is part of the project method, not just test organisation.
