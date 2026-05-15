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
]
