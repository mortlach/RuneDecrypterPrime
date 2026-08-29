RDP V1 public API
=================

This package owns the canonical public definitions. Normal consumers use:

    from rdp import api

Root operations are `api.run`, `api.encrypt` and `api.decrypt`. `RunSpec`,
`RunResult`, typed configuration/specification classes, public enums and errors
are exposed at the root. Advanced, display, Liber Primus and experimental
capabilities live in their named subnamespaces.

Ordinary code uses typed constructors. Name/dictionary parsers are reserved for
serialized or dynamically loaded configuration. There is no public runtime
cipher object, execution class, generic transform, forwarding package or
automatic internal fallback.

Engine implementations remain under `rune_decrypter_prime` and are imported by
their exact internal consumers, not re-exported as another public surface.
