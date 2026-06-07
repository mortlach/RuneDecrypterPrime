from __future__ import annotations

"""
Reference utilities for strict O3/N3C anchored-region diagnostics.

This module is intentionally small, deterministic, and independent of the full
RDP repo. It is suitable for unit tests and for porting into the project scripts.

Scope:
- report-only diagnostics;
- FWD strict O3/N3C hit rows only;
- long-hit floor features;
- deterministic weighted non-overlap anchor selection;
- pairwise rule sweeps with Wilson intervals.
"""

from dataclasses import dataclass
import csv
import math
from pathlib import Path
from typing import Iterable, Mapping, Sequence, Any


REQUIRED_DIRECTION = "fwd"


@dataclass(frozen=True)
class HitRow:
    candidate_id: str
    trial_id: str
    direction: str
    hd: int
    phrase_length: int
    start: int
    end: int
    phrase_row_id: str = ""
    word_shape_id: str = ""
    phrase_count: float | None = None
    o4_confirmed: bool = False

    @property
    def span_len(self) -> int:
        return max(0, self.end - self.start)


@dataclass(frozen=True)
class AnchorRegion:
    candidate_id: str
    trial_id: str
    start: int
    end: int
    hd: int
    phrase_length: int
    weight: float
    phrase_row_id: str
    word_shape_id: str
    o4_confirmed: bool = False


@dataclass(frozen=True)
class CandidateAnchorSummary:
    candidate_id: str
    trial_id: str
    selected_region_count: int
    selected_weight_sum: float
    selected_coverage_tokens: int
    longest_selected_phrase_len: int
    longest_hd0_phrase_len: int
    longest_hd1_phrase_len: int
    longest_hd2_phrase_len: int
    min_hd_at_len_ge_10: int | None
    min_hd_at_len_ge_12: int | None
    min_hd_at_len_ge_15: int | None
    min_hd_at_len_ge_18: int | None
    min_hd_at_len_ge_20: int | None
    rarest_hd0_count_len_ge_10: float | None
    rarest_hd0_count_len_ge_12: float | None


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "y", "o4", "confirmed"}


def _first_present(row: Mapping[str, Any], names: Sequence[str], default: Any = "") -> Any:
    for name in names:
        if name in row and row[name] not in (None, ""):
            return row[name]
    return default


def hit_from_csv_row(row: Mapping[str, Any]) -> HitRow:
    """Parse a hit row using tolerant column aliases.

    The production script should replace/lock these aliases once the exact CSV
    schema is known. The tolerant parser is kept here so the smoke fixture is
    easy to run and so missing columns fail with clear field names.
    """
    candidate_id = str(_first_present(row, ("candidate_id", "candidate", "candidate_key")))
    trial_id = str(_first_present(row, ("trial_id", "trial", "pair_group", "semantic_id"), ""))
    direction = str(_first_present(row, ("direction", "dir"), REQUIRED_DIRECTION)).lower()
    hd = int(_first_present(row, ("hd", "total_hd", "total_phrase_hd", "phrase_hd")))
    phrase_length = int(
        _first_present(row, ("phrase_length", "phrase_token_length", "len", "length", "token_length"))
    )
    start = int(_first_present(row, ("start", "hit_start", "candidate_start", "span_start", "offset")))
    end_value = _first_present(row, ("end", "hit_end", "candidate_end", "span_end"), "")
    end = int(end_value) if end_value != "" else start + phrase_length
    phrase_count_raw = _first_present(row, ("phrase_count", "sum_count", "row_count", "frequency"), "")
    phrase_count = float(phrase_count_raw) if phrase_count_raw != "" else None
    return HitRow(
        candidate_id=candidate_id,
        trial_id=trial_id,
        direction=direction,
        hd=hd,
        phrase_length=phrase_length,
        start=start,
        end=end,
        phrase_row_id=str(_first_present(row, ("phrase_row_id", "row_id", "phrase_id"), "")),
        word_shape_id=str(_first_present(row, ("word_shape_id", "shape_id", "shape"), "")),
        phrase_count=phrase_count,
        o4_confirmed=parse_bool(_first_present(row, ("o4_confirmed", "o4_overlap", "o4_flag"), "")),
    )


def read_hit_rows_csv(path: Path) -> list[HitRow]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        return [hit_from_csv_row(row) for row in reader]


def require_fwd_hit(hit: HitRow) -> None:
    if hit.direction != REQUIRED_DIRECTION:
        raise ValueError(
            f"strict O3 anchor diagnostics require direction={REQUIRED_DIRECTION!r}; "
            f"got {hit.direction!r} for candidate={hit.candidate_id!r}"
        )


def filter_hits(
    hits: Iterable[HitRow],
    *,
    max_hd: int,
    min_phrase_length: int,
    require_fwd: bool = True,
) -> list[HitRow]:
    out: list[HitRow] = []
    for hit in hits:
        if require_fwd:
            require_fwd_hit(hit)
        if hit.hd <= max_hd and hit.phrase_length >= min_phrase_length:
            out.append(hit)
    return out


def phrase_rarity_weight(hit: HitRow, *, total_phrase_rows: float = 1_000_000.0) -> float:
    """Simple monotone rarity proxy.

    Lower phrase_count gives higher weight. If phrase_count is missing, return a
    neutral value rather than fabricating evidence.
    """
    if hit.phrase_count is None or hit.phrase_count <= 0:
        return 1.0
    return math.log1p(max(1.0, total_phrase_rows) / max(1.0, float(hit.phrase_count)))


def anchor_weight(
    hit: HitRow,
    *,
    min_phrase_length: int,
    total_phrase_rows: float = 1_000_000.0,
    length_bonus_per_token: float = 0.15,
    exact_bonus: float = 2.0,
    hd1_support_bonus: float = 0.5,
    o4_confirmation_bonus: float = 4.0,
) -> float:
    rarity = phrase_rarity_weight(hit, total_phrase_rows=total_phrase_rows)
    length_bonus = max(0, hit.phrase_length - min_phrase_length) * length_bonus_per_token
    if hit.hd == 0:
        hd_bonus = exact_bonus
    elif hit.hd == 1:
        hd_bonus = hd1_support_bonus
    else:
        hd_bonus = 0.0
    o4_bonus = o4_confirmation_bonus if hit.o4_confirmed else 0.0
    return rarity + length_bonus + hd_bonus + o4_bonus


def dedupe_hits_by_span_keep_best(
    hits: Iterable[HitRow],
    *,
    min_phrase_length: int,
    total_phrase_rows: float = 1_000_000.0,
) -> list[AnchorRegion]:
    best_by_key: dict[tuple[str, str, int, int], AnchorRegion] = {}
    for hit in hits:
        weight = anchor_weight(hit, min_phrase_length=min_phrase_length, total_phrase_rows=total_phrase_rows)
        key = (hit.trial_id, hit.candidate_id, hit.start, hit.end)
        region = AnchorRegion(
            candidate_id=hit.candidate_id,
            trial_id=hit.trial_id,
            start=hit.start,
            end=hit.end,
            hd=hit.hd,
            phrase_length=hit.phrase_length,
            weight=weight,
            phrase_row_id=hit.phrase_row_id,
            word_shape_id=hit.word_shape_id,
            o4_confirmed=hit.o4_confirmed,
        )
        old = best_by_key.get(key)
        if old is None or _region_sort_key(region) > _region_sort_key(old):
            best_by_key[key] = region
    return sorted(best_by_key.values(), key=lambda r: (r.start, r.end, -r.weight, r.phrase_row_id))


def _region_sort_key(region: AnchorRegion) -> tuple[float, int, int, int, str]:
    return (region.weight, region.phrase_length, -region.hd, int(region.o4_confirmed), region.phrase_row_id)


def select_max_weight_nonoverlap(regions: Sequence[AnchorRegion], *, min_gap: int = 0) -> list[AnchorRegion]:
    """Weighted interval scheduling with deterministic tie-breaking."""
    ordered = sorted(regions, key=lambda r: (r.end, r.start, -r.weight, r.phrase_row_id))
    n = len(ordered)
    if n == 0:
        return []

    # p[i] = last interval index ending before ordered[i].start - min_gap.
    ends = [r.end for r in ordered]
    p: list[int] = []
    for i, region in enumerate(ordered):
        limit = region.start - min_gap
        lo, hi = 0, i - 1
        best = -1
        while lo <= hi:
            mid = (lo + hi) // 2
            if ends[mid] <= limit:
                best = mid
                lo = mid + 1
            else:
                hi = mid - 1
        p.append(best)

    dp = [0.0] * (n + 1)
    take = [False] * n
    for i in range(1, n + 1):
        region = ordered[i - 1]
        include = region.weight + dp[p[i - 1] + 1]
        exclude = dp[i - 1]
        if include > exclude + 1e-12:
            dp[i] = include
            take[i - 1] = True
        else:
            dp[i] = exclude
            take[i - 1] = False

    selected: list[AnchorRegion] = []
    i = n
    while i > 0:
        if take[i - 1] and ordered[i - 1].weight + dp[p[i - 1] + 1] >= dp[i - 1] - 1e-12:
            selected.append(ordered[i - 1])
            i = p[i - 1] + 1
        else:
            i -= 1
    selected.reverse()
    return selected


def min_hd_at_length(hits: Sequence[HitRow], threshold: int) -> int | None:
    values = [hit.hd for hit in hits if hit.phrase_length >= threshold]
    return min(values) if values else None


def longest_by_hd(hits: Sequence[HitRow], hd: int) -> int:
    values = [hit.phrase_length for hit in hits if hit.hd == hd]
    return max(values) if values else 0


def rarest_count(hits: Sequence[HitRow], *, hd: int, min_len: int) -> float | None:
    values = [hit.phrase_count for hit in hits if hit.hd == hd and hit.phrase_length >= min_len and hit.phrase_count is not None]
    return min(values) if values else None


def summarise_candidate(
    hits: Sequence[HitRow],
    *,
    candidate_id: str,
    trial_id: str,
    min_phrase_length: int = 10,
    max_hd: int = 0,
    min_gap: int = 0,
    total_phrase_rows: float = 1_000_000.0,
) -> tuple[CandidateAnchorSummary, list[AnchorRegion]]:
    filtered = filter_hits(hits, max_hd=max_hd, min_phrase_length=min_phrase_length, require_fwd=True)
    regions = dedupe_hits_by_span_keep_best(
        filtered,
        min_phrase_length=min_phrase_length,
        total_phrase_rows=total_phrase_rows,
    )
    selected = select_max_weight_nonoverlap(regions, min_gap=min_gap)
    coverage = sum(max(0, r.end - r.start) for r in selected)
    summary = CandidateAnchorSummary(
        candidate_id=candidate_id,
        trial_id=trial_id,
        selected_region_count=len(selected),
        selected_weight_sum=sum(r.weight for r in selected),
        selected_coverage_tokens=coverage,
        longest_selected_phrase_len=max((r.phrase_length for r in selected), default=0),
        longest_hd0_phrase_len=longest_by_hd(list(hits), 0),
        longest_hd1_phrase_len=longest_by_hd(list(hits), 1),
        longest_hd2_phrase_len=longest_by_hd(list(hits), 2),
        min_hd_at_len_ge_10=min_hd_at_length(list(hits), 10),
        min_hd_at_len_ge_12=min_hd_at_length(list(hits), 12),
        min_hd_at_len_ge_15=min_hd_at_length(list(hits), 15),
        min_hd_at_len_ge_18=min_hd_at_length(list(hits), 18),
        min_hd_at_len_ge_20=min_hd_at_length(list(hits), 20),
        rarest_hd0_count_len_ge_10=rarest_count(list(hits), hd=0, min_len=10),
        rarest_hd0_count_len_ge_12=rarest_count(list(hits), hd=0, min_len=12),
    )
    return summary, selected


def group_hits_by_candidate(hits: Iterable[HitRow]) -> dict[tuple[str, str], list[HitRow]]:
    grouped: dict[tuple[str, str], list[HitRow]] = {}
    for hit in hits:
        grouped.setdefault((hit.trial_id, hit.candidate_id), []).append(hit)
    return grouped


def wilson_interval(successes: int, n: int, *, z: float = 1.959963984540054) -> tuple[float, float]:
    if n <= 0:
        return (0.0, 1.0)
    phat = successes / n
    denom = 1.0 + z * z / n
    centre = (phat + z * z / (2 * n)) / denom
    half = z * math.sqrt((phat * (1 - phat) + z * z / (4 * n)) / n) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def compare_metric(a: float, b: float, *, margin: float) -> int:
    if a >= b + margin:
        return 1
    if b >= a + margin:
        return -1
    return 0


def pairwise_rule_summary(
    pair_rows: Iterable[Mapping[str, Any]],
    scores: Mapping[str, float],
    *,
    margin: float,
    correct_candidate_col: str = "correct_candidate_id",
    other_candidate_col: str = "other_candidate_id",
) -> dict[str, Any]:
    covered = agree = break_ = tie = 0
    for row in pair_rows:
        correct = str(row[correct_candidate_col])
        other = str(row[other_candidate_col])
        if correct not in scores or other not in scores:
            continue
        covered += 1
        cmp = compare_metric(scores[correct], scores[other], margin=margin)
        if cmp > 0:
            agree += 1
        elif cmp < 0:
            break_ += 1
        else:
            tie += 1
    low, high = wilson_interval(break_, covered) if covered else (0.0, 1.0)
    return {
        "margin": margin,
        "covered": covered,
        "agree": agree,
        "break": break_,
        "tie": tie,
        "break_rate": break_ / covered if covered else 0.0,
        "break_rate_wilson95_low": low,
        "break_rate_wilson95_high": high,
    }


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]], fieldnames: Sequence[str]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))
            count += 1
    return count
