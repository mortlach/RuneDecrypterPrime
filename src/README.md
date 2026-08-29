# Source folder

Project source code lives under `src/`.

- `src/rdp/api/` owns the canonical V1 public definitions.
- `src/rdp/__init__.py` exposes that package without wildcard forwarding.
- `src/rune_decrypter_prime/` contains the existing engine implementations and
  exact internal owners.

Public consumers use `from rdp import api`. The engine package is not a second
public API, compatibility layer or forwarding namespace.
