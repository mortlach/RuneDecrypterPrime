# V1 repository structure

```text
src/
  rdp/
    __init__.py          # exposes the definition-owning api package
    api/                 # canonical V1 public definitions
  rune_decrypter_prime/  # engine implementations and exact internal owners
tests/                   # unit, contract, installation and type-check evidence
tutorials/v1/            # active V1 tutorials
docs/                    # active documentation and release contracts
v1_docs/                 # retained V1 reference material pending selective merge
```

Public consumers use `from rdp import api`. Internal consumers import the exact
implementation module they require. There is no forwarding public package,
compatibility alias namespace or generic internal facade.

The engine package retains ciphers, solvers, scoring, key operations, telemetry,
data and native-extension ownership until the separately governed AN4 work.

Generated output, caches, review packs, local configuration and large local
assets do not belong in the repository.
