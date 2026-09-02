from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

from rdp.scoring.span_hamming.types import (
    SpanHammingConfig,
    SpanHammingStats,
    SpanInterval,
)


Wordlist = Dict[int, List[List[int]]]


def _load_fast_extension():
    try:
        return import_module("rdp.scoring.span_hamming._span_hamming_fast")
    except Exception:  # pragma: no cover - optional extension import
        return None


def fast_span_hamming_available() -> bool:
    return _load_fast_extension() is not None


class FastSpanHammingBackend:
    """
    Optional C++ span-Hamming backend.

    This is a parity/probe backend for report-only calibration. It intentionally
    mirrors SpanHammingBackend's public score output and does not replace the
    production Python backend.
    """

    def __init__(
        self,
        config: SpanHammingConfig | None = None,
        *,
        wordlists: Wordlist | None = None,
        wordlist_dir: str | Path | None = None,
        require_selected: bool = True,
        return_raw_intervals: bool = False,
    ) -> None:
        extension = _load_fast_extension()
        if extension is None:
            raise ImportError(
                "rdp.scoring.span_hamming._span_hamming_fast is not built; "
                "run src/rdp/scoring/span_hamming/setup_span_hamming_fast.py"
            )

        self.config = config or SpanHammingConfig()
        self.length_bins: Tuple[int, ...] = tuple(range(self.config.len_min, self.config.len_max + 1))
        self.return_raw_intervals = bool(return_raw_intervals)

        if wordlists is None:
            # Lazy import keeps the optional fast backend importable in reduced
            # test/review bundles where package data assets are not present.
            from rdp.scoring.hamming.loader import load_raw1grams_wordlists

            loaded_ltr, _ = load_raw1grams_wordlists(
                wordlist_dir,
                build_rtl=False,
                require_selected=require_selected,
            )
            wordlists = loaded_ltr

        normalized = self._normalize_wordlists(wordlists)
        self._backend = extension.FastSpanHamming()
        for length in self.length_bins:
            words = normalized.get(length, tuple())
            if words:
                self._backend.update_words_index(int(length), [list(word) for word in words], int(self.config.max_hd))

    def _normalize_wordlists(self, wordlists: Wordlist | None) -> Dict[int, Tuple[Tuple[int, ...], ...]]:
        normalized: Dict[int, Tuple[Tuple[int, ...], ...]] = {}
        if not wordlists:
            return normalized
        for length in self.length_bins:
            words_for_length = wordlists.get(length, [])
            deduped = sorted(
                {
                    tuple(int(token) for token in word)
                    for word in words_for_length
                    if len(word) == length
                }
            )
            if deduped:
                normalized[length] = tuple(deduped)
        return normalized

    def score(self, text_idx: Sequence[int] | Iterable[int]) -> SpanHammingStats:
        payload = self.score_payload(text_idx)

        return SpanHammingStats(
            span_raw=float(payload["span_raw"]),
            coverage=float(payload["coverage"]),
            quality=float(payload["quality"]),
            n_chars=int(payload["n_chars"]),
            chars_covered=int(payload["chars_covered"]),
            n_intervals_selected=int(payload["n_intervals_selected"]),
            length_bins=tuple(int(value) for value in payload["length_bins"]),
            span_raw_by_len=tuple(float(value) for value in payload["span_raw_by_len"]),
            coverage_by_len=tuple(float(value) for value in payload["coverage_by_len"]),
            quality_by_len=tuple(float(value) for value in payload["quality_by_len"]),
            selected_intervals_by_len=tuple(int(value) for value in payload["selected_intervals_by_len"]),
            chars_covered_by_len=tuple(int(value) for value in payload["chars_covered_by_len"]),
            n_windows_total=int(payload["n_windows_total"]),
            n_windows_scored=int(payload["n_windows_scored"]),
            n_candidates_considered=int(payload["n_candidates_considered"]),
            n_candidates_pruned_cap=int(payload["n_candidates_pruned_cap"]),
            selected_intervals=tuple(_interval_from_payload(row) for row in payload["selected_intervals"]),
        )

    def score_payload(self, text_idx: Sequence[int] | Iterable[int]) -> dict[str, object]:
        """Return the raw extension payload, including raw intervals when enabled."""
        if isinstance(text_idx, tuple):
            text = list(text_idx)
        elif isinstance(text_idx, list):
            text = text_idx
        else:
            text = [int(token) for token in text_idx]

        return dict(self._backend.score(
            text,
            int(self.config.len_min),
            int(self.config.len_max),
            int(self.config.max_hd),
            int(self.config.start_stride),
            int(self.config.max_windows_total),
            int(self.config.max_candidates_per_window),
            int(self.config.max_intervals_considered_per_start),
            float(self.config.min_quality_threshold),
            bool(self.config.debug_return_intervals),
            bool(self.return_raw_intervals),
        ))


    def fingerprint_raw_hamming_counts(
        self,
        text_idx: Sequence[int] | Iterable[int],
        *,
        include_offset_rows: bool = False,
        include_match_dump: bool = False,
        max_candidates_per_window: int = 0,
    ) -> dict[str, object]:
        """Return raw length-by-HD fingerprint counts from the fast backend.

        This is an analysis-only mode. It is separate from ``score`` and uses
        HD bins ``0..length-1``. For this fingerprint method only,
        ``max_candidates_per_window=0`` means no candidate cap.
        """
        if max_candidates_per_window < 0:
            raise ValueError("max_candidates_per_window must be >= 0 for fingerprint mode")

        if isinstance(text_idx, tuple):
            text = list(text_idx)
        elif isinstance(text_idx, list):
            text = text_idx
        else:
            text = [int(token) for token in text_idx]

        payload = dict(self._backend.fingerprint_raw_hamming_counts(
            text,
            int(self.config.len_min),
            int(self.config.len_max),
            int(self.config.start_stride),
            int(self.config.max_windows_total),
            int(max_candidates_per_window),
            bool(include_offset_rows),
            bool(include_match_dump),
        ))
        payload["fingerprint_detail_level"] = (
            "match_dump" if include_match_dump else "offset_histogram" if include_offset_rows else "chunk_histogram"
        )
        payload["cap"] = int(max_candidates_per_window)
        payload["is_uncapped"] = int(max_candidates_per_window) == 0
        return payload

def _interval_from_payload(row: object) -> SpanInterval:
    data = dict(row)  # pybind dict or normal mapping
    return SpanInterval(
        start=int(data["start"]),
        end=int(data["end"]),
        length=int(data["length"]),
        distance=int(data["distance"]),
        quality=float(data["quality"]),
        weight=float(data["weight"]),
    )
