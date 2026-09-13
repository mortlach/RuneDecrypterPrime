# Torch lookup helpers

Low-level tensor operations used by the Torch scorer.

## Where to look

- [packing.py](packing.py) — Pack character and WLI n-grams into lookup keys.
- [hash.py](hash.py) — Hash keys and validate lookup tensor inputs.
- [probe.py](probe.py) — Probe score lookup tables.

## Choices and extension

These are implementation helpers, not independent user-selectable scorers. Choose the supported Torch backend through scoring configuration. When changing a helper, preserve integer representation and lookup agreement with the reference path.

Continue with the [guide](../../../../docs/setup/scorer_backend_selection.md) or the [package map](../../README.md).
