"""Word-structured n-gram Hamming coherence helpers."""

from rune_decrypter_prime.scoring.ngram_hamming.reference import (
    PhraseEntry,
    PhraseHit,
    PhraseProfile,
    ReferenceScanResult,
    parse_flat_token_ids,
    parse_positive_int_ids,
    validate_candidate_tokens,
    parse_word_token_ids,
    scan_chunk_reference,
)
from rune_decrypter_prime.scoring.ngram_hamming.fast_backend import (
    fast_ngram_hamming_available,
    scan_chunk_fast,
)

__all__ = [
    "PhraseEntry",
    "PhraseHit",
    "PhraseProfile",
    "ReferenceScanResult",
    "parse_flat_token_ids",
    "parse_positive_int_ids",
    "validate_candidate_tokens",
    "parse_word_token_ids",
    "scan_chunk_reference",
    "fast_ngram_hamming_available",
    "scan_chunk_fast",
]
