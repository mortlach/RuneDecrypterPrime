rdp package
===========

`src/rdp` is a thin convenience shim so new users can simply do:

```python
from rdp import api
```

It re-exports everything from `rune_decrypter_prime` and exposes the public `api`
module directly. No business logic lives here; keep it import-only so the alias
stays fast and side-effect free. If you add new top-level symbols to the main
package and want them reachable through `rdp`, re-export them in `__init__.py`.
