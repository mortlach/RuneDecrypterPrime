from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Iterable, Sequence
import numpy as np
from rune_decrypter_prime.scoring.span_hamming import SpanCalibratedAssets, SpanHammingBackend, SpanHammingLmAssetsV2
from rune_decrypter_prime.scoring.span_hamming.ecdf_interp import clamp_pct, energy_to_pct, pct_to_energy

@dataclass(frozen=True)
class SpanHammingBenchmarkRuntimeConfig:
    objective_family: str = 'pct'
    coverage_min: float = 0.0
    quality_min: float = 0.0
    span_pct_min: float | None = None
    char_pct_min: float | None = None
    combine_mode: str = 'min'
    weight_span: float = 1.0
    weight_char: float = 0.0
    use_char_channel: bool = False
    gate_fail_policy: str = 'score_floor'
    gate_score_floor: float | None = None
    lm_weight: float = 0.0
    lm_weight_margin: float = 1.0
    lm_weight_mean_bin_index: float = 1.0
    lm_weight_mean_bin_length: float = 1.0
    lm_weight_tail_mass: float = 1.0
    lm_profile_source: str = 'span_raw_by_len'
    lm_tail_start_index: int = 5

@dataclass(frozen=True)
class ScoreResult:
    text_length: int
    length_bucket: int
    span_raw: float
    span_coverage: float
    span_quality: float
    span_pct: float
    span_energy: float
    combined_pct: float
    combined_energy: float
    char_pct: float | None
    char_score: float | None
    lm_enabled: bool
    lm_profile_margin_l1_raw: float | None
    lm_profile_margin_l1_pct_noise: float | None
    lm_mean_bin_index_raw: float | None
    lm_mean_bin_index_pct_noise: float | None
    lm_mean_bin_length_raw: float | None
    lm_mean_bin_length_pct_noise: float | None
    lm_tail_mass_raw: float | None
    lm_tail_mass_pct_noise: float | None
    lm_profile_pct: float | None
    lm_profile_energy: float | None
    gate_failed: bool
    gate_reasons: tuple[str, ...]
    lm_applied_to_score: bool
    pre_gate_total_pct: float
    pre_gate_total_energy: float
    runtime_total_pct: float
    runtime_total_energy: float
    final_pct: float
    final_energy: float
    final_score: float

    def asdict(self) -> dict:
        return asdict(self)

def make_random_text(length: int, alphabet_size: int, rng: np.random.Generator) -> np.ndarray:
    return np.asarray(rng.integers(0, int(alphabet_size), size=int(length)), dtype=np.uint8)

def corrupt_with_random(base_text: Sequence[int], corruption_rate: float, alphabet_size: int, rng: np.random.Generator) -> np.ndarray:
    src = np.asarray(base_text, dtype=np.uint8).copy()
    rate = float(corruption_rate)
    if rate <= 0.0:
        return src
    if rate >= 1.0:
        return make_random_text(src.size, alphabet_size, rng)
    n_flip = int(round(rate * src.size))
    if n_flip <= 0:
        return src
    positions = np.asarray(rng.choice(src.size, size=n_flip, replace=False), dtype=np.int64)
    repl = np.asarray(rng.integers(0, int(alphabet_size), size=n_flip), dtype=np.uint8)
    same = repl == src[positions]
    if bool(np.any(same)):
        repl[same] = (repl[same] + 1) % int(alphabet_size)
    src[positions] = repl
    return src

def make_repeated_motif(length: int, motif: Sequence[int]) -> np.ndarray:
    motif_arr = np.asarray(list(motif), dtype=np.uint8)
    reps = int(np.ceil(int(length) / max(1, int(motif_arr.size))))
    return np.tile(motif_arr, reps)[:int(length)].astype(np.uint8, copy=False)

def make_fragment_soup(corpus: Sequence[int], length: int, rng: np.random.Generator, *, chunk_lengths: Sequence[int]) -> np.ndarray:
    src = np.asarray(corpus, dtype=np.uint8)
    out: list[np.ndarray] = []
    total = 0
    choices = tuple((int(v) for v in chunk_lengths if int(v) > 0))
    if not choices:
        raise ValueError('chunk_lengths must contain positive integers')
    while total < int(length):
        chunk_len = int(choices[int(rng.integers(0, len(choices)))])
        start_max = max(1, src.size - chunk_len + 1)
        start = int(rng.integers(0, start_max))
        chunk = src[start:start + chunk_len]
        out.append(chunk)
        total += int(chunk.size)
    return np.concatenate(out)[:int(length)].astype(np.uint8, copy=False)

def make_block_shuffle(base_text: Sequence[int], rng: np.random.Generator, *, block_size: int) -> np.ndarray:
    src = np.asarray(base_text, dtype=np.uint8)
    bsz = int(block_size)
    if bsz <= 0:
        raise ValueError('block_size must be > 0')
    blocks = [src[i:i + bsz].copy() for i in range(0, src.size, bsz)]
    order = np.asarray(rng.permutation(len(blocks)), dtype=np.int64)
    return np.concatenate([blocks[int(i)] for i in order]).astype(np.uint8, copy=False)

def summarize_numeric(values: Iterable[float]) -> dict[str, float]:
    arr = np.asarray(list(values), dtype=np.float64)
    if arr.size == 0:
        return {'n': 0.0, 'mean': 0.0, 'std': 0.0, 'min': 0.0, 'p05': 0.0, 'median': 0.0, 'p95': 0.0, 'max': 0.0}
    return {'n': float(arr.size), 'mean': float(np.mean(arr)), 'std': float(np.std(arr, ddof=0)), 'min': float(np.min(arr)), 'p05': float(np.quantile(arr, 0.05)), 'median': float(np.quantile(arr, 0.5)), 'p95': float(np.quantile(arr, 0.95)), 'max': float(np.max(arr))}

def _combine_pct(*, span_pct: float, char_pct: float | None, combine_mode: str, weight_span: float, weight_char: float, clamp_min: float, clamp_max: float) -> tuple[float, float]:
    if char_pct is None:
        combined_pct = float(span_pct)
    elif str(combine_mode) == 'min':
        combined_pct = float(min(float(span_pct), float(char_pct)))
    else:
        w_span = float(weight_span)
        w_char = float(weight_char)
        w_total = float(w_span + w_char)
        if w_total <= 0.0:
            raise ValueError('weighted_sum combine requires positive total weight (weight_span + weight_char)')
        combined_pct = float((w_span * float(span_pct) + w_char * float(char_pct)) / w_total)
    combined_pct = float(clamp_pct(combined_pct, float(clamp_min), float(clamp_max)))
    return (combined_pct, float(pct_to_energy(combined_pct)))

def _gate_reasons(*, span_coverage: float, span_quality: float, span_pct: float, char_pct: float | None, cfg: SpanHammingBenchmarkRuntimeConfig) -> list[str]:
    reasons: list[str] = []
    if float(span_coverage) < float(cfg.coverage_min):
        reasons.append('coverage_below_min')
    if float(span_quality) < float(cfg.quality_min):
        reasons.append('quality_below_min')
    if cfg.span_pct_min is not None and float(span_pct) < float(cfg.span_pct_min):
        reasons.append('span_pct_below_min')
    if cfg.use_char_channel and cfg.char_pct_min is not None:
        if char_pct is None or float(char_pct) < float(cfg.char_pct_min):
            reasons.append('char_pct_below_min')
    return reasons

def _default_gate_score_floor(*, objective_family: str, clamp_min: float) -> float:
    fam = str(objective_family).strip().lower()
    if fam == 'energy':
        return float(pct_to_energy(float(clamp_min)))
    return float(clamp_min)

def _weighted_mean_energy(items: Sequence[tuple[float, float]]) -> float:
    active = [(float(weight), float(energy)) for weight, energy in items if float(weight) > 0.0]
    if not active:
        return 0.0
    total_weight = float(sum((weight for weight, _energy in active)))
    if total_weight <= 0.0:
        return 0.0
    return float(sum((weight * energy for weight, energy in active)) / total_weight)

def score_text_with_assets(text: Sequence[int], *, backend: SpanHammingBackend, span_assets: SpanCalibratedAssets, lm_assets: SpanHammingLmAssetsV2 | None=None, direction: str='ltr', clamp_min: float=1e-06, clamp_max: float=1.0 - 1e-06, runtime_config: SpanHammingBenchmarkRuntimeConfig | None=None) -> ScoreResult:
    cfg = runtime_config or SpanHammingBenchmarkRuntimeConfig()
    text_arr = np.asarray(text, dtype=np.uint8)
    stats = backend.score(text_arr.tolist())
    bucket = span_assets.select_bucket(direction, int(text_arr.size))
    span_score = span_assets.score_span_raw_in_bucket(direction=direction, length_bucket=int(bucket), span_raw=float(stats.span_raw), clamp_min=float(clamp_min), clamp_max=float(clamp_max))
    char_pct = None
    char_score = None
    combined_pct, combined_energy = _combine_pct(span_pct=float(span_score.span_pct), char_pct=char_pct, combine_mode=str(cfg.combine_mode), weight_span=float(cfg.weight_span), weight_char=float(cfg.weight_char), clamp_min=float(clamp_min), clamp_max=float(clamp_max))
    profile_energy = 0.0
    lm_margin_raw = None
    lm_pct_noise = None
    lm_mean_index_raw = None
    lm_mean_index_pct = None
    lm_mean_length_raw = None
    lm_mean_length_pct = None
    lm_tail_mass_raw = None
    lm_tail_mass_pct = None
    lm_profile_pct = None
    lm_energy = None
    if lm_assets is not None:
        lm_score = lm_assets.score_profile_margin_l1_in_bucket(stats=stats, direction=direction, length_bucket=int(bucket), clamp_min=float(clamp_min), clamp_max=float(clamp_max), profile_source=str(cfg.lm_profile_source), tail_start_index=int(cfg.lm_tail_start_index))
        lm_margin_raw = float(lm_score.profile_margin_l1_raw)
        lm_pct_noise = float(lm_score.profile_margin_l1_pct_noise)
        lm_mean_index_raw = float(lm_score.mean_bin_index_raw)
        lm_mean_index_pct = float(lm_score.mean_bin_index_pct_noise)
        lm_mean_length_raw = float(lm_score.mean_bin_length_raw)
        lm_mean_length_pct = float(lm_score.mean_bin_length_pct_noise)
        lm_tail_mass_raw = float(lm_score.tail_mass_raw)
        lm_tail_mass_pct = float(lm_score.tail_mass_pct_noise)
        profile_energy = _weighted_mean_energy(((float(cfg.lm_weight_margin), float(lm_score.profile_margin_l1_energy)), (float(cfg.lm_weight_mean_bin_index), float(lm_score.mean_bin_index_energy)), (float(cfg.lm_weight_mean_bin_length), float(lm_score.mean_bin_length_energy)), (float(cfg.lm_weight_tail_mass), float(lm_score.tail_mass_energy))))
        lm_energy = float(profile_energy)
        lm_profile_pct = float(clamp_pct(energy_to_pct(profile_energy), float(clamp_min), float(clamp_max)))
    gate_reasons = tuple(_gate_reasons(span_coverage=float(stats.coverage), span_quality=float(stats.quality), span_pct=float(span_score.span_pct), char_pct=char_pct, cfg=cfg))
    gate_failed = bool(gate_reasons)
    lm_applied_to_score = bool(lm_assets is not None and (not gate_failed))
    pre_gate_total_energy = float(combined_energy + float(cfg.lm_weight) * float(profile_energy))
    pre_gate_total_pct = float(clamp_pct(energy_to_pct(pre_gate_total_energy), float(clamp_min), float(clamp_max)))
    runtime_total_energy = float(pre_gate_total_energy if lm_applied_to_score else combined_energy)
    runtime_total_pct = float(clamp_pct(energy_to_pct(runtime_total_energy), float(clamp_min), float(clamp_max)))
    gate_score_floor = float(cfg.gate_score_floor if cfg.gate_score_floor is not None else _default_gate_score_floor(objective_family=str(cfg.objective_family), clamp_min=float(clamp_min)))
    objective_family = str(cfg.objective_family).strip().lower()
    gate_fail_policy = str(cfg.gate_fail_policy).strip().lower()
    if gate_failed:
        if gate_fail_policy == 'char_only' and char_score is not None:
            final_score = float(char_score)
        else:
            final_score = float(gate_score_floor)
    else:
        final_score = float(runtime_total_energy if objective_family == 'energy' else runtime_total_pct)
    if gate_failed:
        if gate_fail_policy == 'char_only' and char_pct is not None and (char_score is not None):
            final_pct = float(clamp_pct(float(char_pct), float(clamp_min), float(clamp_max)))
            final_energy = float(pct_to_energy(final_pct))
        elif objective_family == 'energy':
            final_energy = float(final_score)
            final_pct = float(clamp_pct(energy_to_pct(final_energy), float(clamp_min), float(clamp_max)))
        else:
            final_pct = float(clamp_pct(final_score, float(clamp_min), float(clamp_max)))
            final_energy = float(pct_to_energy(final_pct))
    else:
        final_pct = float(runtime_total_pct)
        final_energy = float(runtime_total_energy)
    return ScoreResult(text_length=int(text_arr.size), length_bucket=int(bucket), span_raw=float(stats.span_raw), span_coverage=float(stats.coverage), span_quality=float(stats.quality), span_pct=float(span_score.span_pct), span_energy=float(span_score.span_energy), combined_pct=float(combined_pct), combined_energy=float(combined_energy), char_pct=char_pct, char_score=char_score, lm_enabled=bool(lm_assets is not None), lm_profile_margin_l1_raw=lm_margin_raw, lm_profile_margin_l1_pct_noise=lm_pct_noise, lm_mean_bin_index_raw=lm_mean_index_raw, lm_mean_bin_index_pct_noise=lm_mean_index_pct, lm_mean_bin_length_raw=lm_mean_length_raw, lm_mean_bin_length_pct_noise=lm_mean_length_pct, lm_tail_mass_raw=lm_tail_mass_raw, lm_tail_mass_pct_noise=lm_tail_mass_pct, lm_profile_pct=lm_profile_pct, lm_profile_energy=None if lm_energy is None else float(lm_energy), gate_failed=bool(gate_failed), gate_reasons=tuple((str(v) for v in gate_reasons)), lm_applied_to_score=bool(lm_applied_to_score), pre_gate_total_pct=float(pre_gate_total_pct), pre_gate_total_energy=float(pre_gate_total_energy), runtime_total_pct=float(runtime_total_pct), runtime_total_energy=float(runtime_total_energy), final_pct=float(final_pct), final_energy=float(final_energy), final_score=float(final_score))
__all__ = ['SpanHammingBenchmarkRuntimeConfig', 'ScoreResult', 'corrupt_with_random', 'make_block_shuffle', 'make_fragment_soup', 'make_random_text', 'make_repeated_motif', 'score_text_with_assets', 'summarize_numeric']
