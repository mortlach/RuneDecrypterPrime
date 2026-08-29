# RDP V1 core design principles

RDP must be both clean and simple. Prefer the smallest coherent end-to-end design
that satisfies demonstrated user and developer needs. Strong typing, explicit
ownership and strict validation must make the system easier to understand and
use, not create more layers.

## User-facing design

- Provide one ordinary route for each normal-user task.
- Make public inputs typed, discoverable and autocomplete-friendly.
- Use friendly defaults with strict validation.
- Reject invalid or conflicting input; never silently reinterpret, ignore or
  fall back from a requested value.
- Reveal advanced complexity only when an advanced feature is used.
- Keep internal machinery out of normal-user imports and tutorials.
- Keep requested and effective execution state explicit when they may differ.

## Ownership and implementation

- Give every piece of state and behaviour one canonical owner.
- Reuse an existing type, helper, registry or materialisation path when it fits.
- Introduce an abstraction only for a demonstrated requirement.
- Do not create a facade merely to hide unfinished migration.
- Do not create speculative extension frameworks.
- Do not maintain parallel public request, result or configuration models.
- Keep public operations thin over truthful validation and the existing runtime
  implementation; do not expose runtime machinery to avoid doing the binding.

## Migration and release hygiene

- Complete each migration across source, callers, tests, tutorials and
  documentation.
- Do not preserve unreleased accidental interfaces through shims, aliases,
  forwarding modules or compatibility layers.
- Delete obsolete material when its retained consumers have migrated and Git
  already preserves its history.
- Prefer exact internal owners over generic internal facades.
- Preserve deterministic behaviour and report any authorised fallback explicitly.
- Diagnostic-only and truth/oracle data must not silently affect production
  ranking or scoring.
- When two correct designs satisfy the contract, choose the one with fewer
  concepts and paths.
- Stop reviewing once sufficient evidence exists to implement safely.

Needless complexity is a defect. Clean architecture is not an invitation to add
layers.
