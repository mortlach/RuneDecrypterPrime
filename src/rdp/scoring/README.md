# Scoring

Scoring converts candidate plaintext into ranking evidence.

The normal scorer combines configured character and WLI language-model evidence,
then applies the selected objective. Optional Hamming, span-Hamming, hard-crib
and word-n-gram facilities have separate capability contracts.

The scoring backend changes execution, not the meaning of the requested
evidence.

See [Scoring and language models](../../../docs/architecture/scoring_and_language_models.md)
and [Scoring](../../../docs/guides/scoring.md).
