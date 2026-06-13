rdp package
===========

Purpose
-------
`src/rdp` is the lightweight alias package that makes our API feel friendly in
tutorials and sample code. It lets a newcomer start with:

```python
from rdp import api
```

instead of remembering the longer `rune_decrypter_prime` path.

What it exports
---------------
- Re-exports *everything* from `rune_decrypter_prime.__all__`.
- Binds `api` explicitly so `from rdp import api` always works, even if the root
  package changes its export list later.

Maintenance tips
----------------
- Keep this module import-only; no business logic or heavy imports belong here.
- When new public symbols are added to the main package, mirror them here if you
  expect end users to rely on `rdp.*`.
- Avoid relative imports from other `src/rdp/*` files—`__init__.py` should stay
  tiny so imports remain snappy for notebooks and IDE consoles.
