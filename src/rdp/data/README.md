# Rune and source data access

This folder turns stored source material into the representations RDP uses and resolves asset locations for source checkouts and installed packages.

## Where to look

- [runeglish.py](runeglish.py) — Rune conversion and word-location helpers.
- [asset_paths.py](asset_paths.py) — Resolve source or packaged asset paths.
- [liber_primus/](liber_primus/) — LP transcription, source identities, routes and payloads.
- [wordlists/](wordlists/) — Short-word and crib dictionary loaders.

## Choices and extension

Normal examples use `api.RawTextInput`, `api.RuneIndexInput` or `api.liber_primus`. Known-key operations take rune indices. The internal Runeglish converter is used by repository fixtures; it is not an extra public constructor. Select text direction to match the source convention.

Continue with the [guide](../../../docs/guides/runes_and_text.md) or the [package map](../README.md).
