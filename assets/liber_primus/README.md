# Liber primus assets

The active master is `liber-primus__transcription--master-v2.txt`. Its `.part001`
companion contains identical bytes for the release asset installer. The previous
`liber-primus__transcription--master.txt` and its part remain historical references.
There is one default loader and one parser for both encodings.

Edit the master as UTF-8 text, keeping the existing delimiter legend, `/` line
markers, `%` page markers and real newlines. The additions are:

- `[red]...[/red]` records red runes, literal digits and punctuation. A span may
  cross `/` and real newlines. Untagged content has no new colour assertion.
- `[dot_N]` records a visible group of N dots; N is a positive decimal integer.
  Optional underscore-separated alphanumeric shape labels distinguish variants,
  for example `[dot_3_L]` and `[dot_3_R]`.
- Literal numerals and the original punctuation keep their existing encoding.
  Marks on either side of a line break remain separate in the text.

The existing ciphertext/WLI helpers ignore colour tags, treat each dot group as
punctuation, and collapse adjacent punctuation to one word boundary. No empty
words are created. Colour, line and page changes do not themselves end a word.
Rune-only extraction excludes numerals; a numeral does not imply a separator.
Raw annotations remain available in `LPTranscript.raw`; typed colour/punctuation
queries are not introduced by this change. Nested, unclosed or unknown tags fail
with a source location.

Canonical LP pages remain 0–57 (main-transcript page IDs 15–72). Existing API
coordinates still describe parsed glyphs/words, not tag characters. Global word
IDs can shift when punctuation or numeral boundaries are corrected. In this
edition LP37's removed separator joins rune lengths 2 and 3 into 5; all page
ciphertexts and all nine solved-source ciphertext/WLI pairs are unchanged.

After editing, synchronise the companion part and update the single
`liber_primus.main_transcript` row in `assets_manifest_v1.json` (size, SHA-256 and
asset_version), plus the identity assertions in the LP tests. Git attributes
preserve CRLF for both new asset files so their manifest hashes are stable.
Access source material through the public LP helpers so source identity and word
alignment accompany ciphertext.

See [installation and asset profiles](../../docs/setup/installation.md).
