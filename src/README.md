# Source folder

Project source code lives under `src/`.

- `src/rdp/api/` owns the canonical V1 public definitions.
- `src/rdp/__init__.py` exposes that package without wildcard forwarding.
- `src/rdp/` contains every engine implementation under its exact domain owner.

Public consumers use `from rdp import api`. Internal consumers import exact
`rdp.*` owners; there is no second package, compatibility layer or forwarding
namespace.
