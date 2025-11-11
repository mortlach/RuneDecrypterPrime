# Test Tiering & Determinism

- Fix a `seed` inside each test case.
- Prefer **evaluation budgets** to time budgets.
- Avoid external I/O or network; keep tests pure and deterministic.
- Use enums (`Direction`, `Device`) in the public surface.

**Pattern (PyCharm run configuration):**
- Create a Run/Debug config for `pytest` or simply run test files/folders from the IDE.
- Keep budgets tiny (e.g., GA generations=5) for smoke.

