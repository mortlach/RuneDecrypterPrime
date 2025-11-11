# `utils/pretty.py`

> Purpose: convenience helpers for rendering solutions/logs in tutorials/tests. Collects small formatting utilities (list coercion, rune->latin conversion) plus `print_run_report`, which prints a one-page summary of a solved run.

## Notable Helpers
- `_as_dict`, `_to_list`, `_is_np_array`, `_nonempty` - internal coercion helpers used to make solution objects JSON/print-friendly.
- `_latin_from_runes_str(runes)` - best-effort transliteration for display.
- `_now_str()` - timestamp for reports.

## `print_run_report(solution, *, title=None, stream=None)`
Prints a formatted summary including score, direction, key, plaintext snippets, seed information, and telemetry pointers. Tutorials call this after `RunAPI.run` so Hands-on users can see the results quickly.

## Usage
```python
from rune_decrypter_prime.utils.pretty import print_run_report

sol = RunAPI.run(...)
print_run_report(sol, title="Vigenere GA")
```

## Tests
- Covered indirectly by tutorials/regressions. If `print_run_report` failed to render plaintext/keys, tutorial tests would fail due to missing output or exceptions.

