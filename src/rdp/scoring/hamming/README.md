# Dictionary-distance scoring

Hamming support measures differences from dictionary words. Its Python adapter and native implementation are kept together here.

## Where to look

- [backend.py](backend.py) — Load and call the native Hamming implementation.
- [loader.py](loader.py) — Load length-grouped raw wordlists.
- [dictionary_assets.py](dictionary_assets.py) — Resolve the configured dictionary policy.
- [anneal.py](anneal.py) — Compute the scheduled Hamming weight.
- [Hamming.cpp](Hamming.cpp) — Native distance implementation.
- [bindings.cpp](bindings.cpp) — Python bindings.
- [setup_hamming.py](setup_hamming.py) — Build the extension.

## Choices and extension

Hamming weight, maximum distance and dictionary policy affect which matches contribute. Direction and available wordlists must match the run. Check the requested lane status before interpreting its contribution.

Continue with the [guide](../../../../docs/guides/hamming_scorer.md) or the [package map](../../README.md).
