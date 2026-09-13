# Rune and source data

This package converts stored source material into the representations used by
RDP and resolves packaged data assets.

## Main owners

- `runeglish.py` converts Latin/runes and constructs word-location information
- `asset_paths.py` resolves source and installed-package assets
- `liber_primus/` owns LP transcription, source identities, routes and payloads
- `wordlists/` owns retained word-list loaders used by specialist scoring and
  diagnostic work

Normal callers use the public input types and `api.liber_primus`.

The internal Runeglish converter is implementation/support code rather than
another public input API.

See [Ciphertext input](../../../docs/guides/ciphertext_input.md),
[Word-length information](../../../docs/guides/word_length_information.md) and
[Liber Primus data](../../../docs/reference/liber_primus.md).
