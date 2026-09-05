# RuneDecrypterPrime V1 implementation rules

These rules apply to work in this repository during the V1 API migration.

## Governing authority

Before changing V1 behaviour or public structure, read:

1. [`docs/release_contracts/v1/RDP_CORE_DESIGN_PRINCIPLES.md`](docs/release_contracts/v1/RDP_CORE_DESIGN_PRINCIPLES.md)
2. [`docs/release_contracts/v1/V1_AUTHORITY_AND_DECISIONS.md`](docs/release_contracts/v1/V1_AUTHORITY_AND_DECISIONS.md)
3. The contract evidence indexed by [`docs/release_contracts/v1/README.md`](docs/release_contracts/v1/README.md)

The accepted AN1 and AN2 decisions govern the V1 public API. Historical D0-D7
material supplies context but cannot override those decisions or the live source
for current implementation ownership.

## Implementation discipline

- Work stage by stage and keep every recorded stage coherent and green.
- Reuse and repair a suitable existing owner before creating another abstraction.
- Complete changes across owners, callers, tests, tutorials and documentation.
- Do not add compatibility shims, forwarding modules, aliases, parallel request
  models or automatic fallbacks for unreleased interfaces.
- Public consumers use `from rdp import api`. Internal consumers import the exact
  module that owns the implementation they need.
- Keep runtime implementation internals out of active normal-user tutorials.
- Do not broaden V1 scope or reorganise engine packages without explicit authority.
- Treat generated migrations as review inputs, not as patches to apply blindly.

## Repository hygiene

- Keep generated output, logs, caches, review packs, local configuration and
  benchmark results outside the repository.
- Do not add or inspect local language-model assets unless a separately approved
  stage explicitly requires it.
- Do not run long solver, benchmark or robustness campaigns without explicit
  approval and a documented run/monitoring plan.
- Use repo-relative paths in committed files and emitted user-facing artefacts.
- Do not push or perform destructive Git operations unless explicitly requested.

When a source contradiction prevents an approved contract from being implemented,
stop and report the exact conflict. Aesthetic alternatives and settled decisions
are not blockers.

## Documentation voice

Follow [the documentation style guide](docs/development/docs_style.md) for
reader-facing prose and tutorial comments. Use natural, direct explanations
in `mortlach`'s voice, with correct spelling and grammar. Explain RDP concepts
and useful choices where they first appear. Dry humour is optional; omit it
when unsure. Preserve technical meaning and the known-answer details of runs.
