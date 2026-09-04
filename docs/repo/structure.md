# V1 repository structure

```text
src/
  rdp/
    __init__.py          # exposes the definition-owning api package
    api/                 # canonical V1 public definitions
    core/                # materialisation, configuration and engine
    ciphers/ keyops/     # cipher and concrete-key implementations
    solvers/ scoring/    # search and scoring implementations
    backends/            # optional backend and device selection
    data/ io/ telemetry/ # runtime resources, artifacts and observations
tests/                   # unit, contract, installation and type-check evidence
tutorials/v1/            # active V1 tutorials
docs/                    # active documentation and release contracts
v1_docs/                 # retained V1 reference material pending selective merge
```

Public consumers use `from rdp import api`. Internal consumers import the exact
implementation module they require. There is no forwarding public package,
compatibility alias namespace or generic internal facade.

The distribution installs only `rdp` and its intended subpackages. CI-light
runtime assets are staged under `rdp/data/assets`; complete language-model
assets remain explicit external inputs.

Generated output, caches, review packs, local configuration and large local
assets do not belong in the repository.
