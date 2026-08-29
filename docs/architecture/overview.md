# RuneDecrypterPrime architecture overview

RDP uses one typed public boundary over existing engine owners:

```text
from rdp import api
        |
        v
immutable RunSpec -> validation/materialisation -> engine
                  -> cipher + key operations + solver + scorer
                  -> immutable RunResult and reports
```

Public definitions live in `src/rdp/api`. Ciphers, solvers, scoring, key
operations, telemetry, data and native extensions remain in their exact
`src/rune_decrypter_prime` modules. There is no forwarding public package or
generic internal facade.

## Public layer

The public root provides `api.run`, `api.encrypt` and `api.decrypt`. Normal code
uses typed inputs, specs, configs and enums. Serialized parsers are secondary
boundaries, not a source of loose runtime dictionaries.

## Engine layer

The engine materialises a validated request, constructs the compatible cipher
and key operations, resolves scorer capabilities, runs the selected solver and
normalizes the outcome into public reports. Algorithms do not own public API
shape.

## Key contracts

- every state and behaviour has one canonical owner;
- concrete public keys are semantic `tuple[int, ...]` values;
- invalid or conflicting configuration fails before execution;
- requested scorer lanes run, block clearly or report an authorised fallback;
- diagnostic and oracle data do not silently affect ranking;
- requested and effective state, stop reason and artefact status are observable;
- seeded work is reproducible within the documented backend/asset contract.

See `docs/release_contracts/v1/RDP_CORE_DESIGN_PRINCIPLES.md` for the governing
design rules and `docs/guides/api_deep.md` for a typed example.
