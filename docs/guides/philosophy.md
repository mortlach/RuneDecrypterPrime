# Philosophy and design principles

The governing principles are in
`docs/release_contracts/v1/RDP_CORE_DESIGN_PRINCIPLES.md`.

For users, those principles mean one typed route for each task, explicit
configuration and clear failures instead of silent reinterpretation. Normal
code imports `from rdp import api` and uses `api.run`, `api.encrypt` or
`api.decrypt`.

For contributors, every capability has one owner. Public definitions live in
`src/rdp/api`; engine implementations live in their exact `src/rdp` domain
modules. New work must not introduce forwarding layers, aliases, parallel
request models or automatic fallbacks.

Determinism, requested-versus-effective state, stop reasons, oracle separation
and artefact status must remain observable. A simpler design is preferred when
it meets the same contract.
