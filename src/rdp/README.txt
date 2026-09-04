rdp package
===========

Purpose
-------
`src/rdp` is the sole installed Python package. Normal consumers start with:

```python
from rdp import api
```

What it exports
---------------
- The package root lazily binds only `api` through `__all__`.
- `rdp.api` owns the supported V1 facade and its four named subnamespaces.
- Engine code lives under exact `rdp.backends`, `rdp.core`, `rdp.ciphers`,
  `rdp.keyops`, `rdp.solvers`, `rdp.scoring`, `rdp.telemetry`, `rdp.data` and
  `rdp.io` owners.

Maintenance tips
----------------
- Keep the root initializer lightweight; importing `rdp` must not initialize
  the API, Torch, CuPy or native extensions.
- Public consumers use `from rdp import api`; contributor code imports the exact
  implementation module it needs.
- Do not add aliases, forwarding modules or duplicate implementation owners.
