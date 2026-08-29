from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
import pytest
from rune_decrypter_prime.scoring.span_hamming.lm_assets_v2 import SpanHammingLmAssetsV2

pytestmark = pytest.mark.tier_a


def _write_asset(root: Path, payload: dict) -> Path:
    fp = root / "lm_asset.json"
    fp.write_text(json.dumps(payload), encoding="utf-8")
    return fp


def _base_payload() -> dict:
    return {
        "asset_kind": "span_hamming_nose_lm_assets",
        "profile_vector_length": 2,
        "profile_length_bins": [3, 4],
        "profile_vector_measures": ["span_raw_by_len"],
        "real_generator": "REAL",
        "profile_tables": {
            "span_raw_by_len": {
                "ltr": {
                    "100": {
                        "references": {
                            "real_mean_profile": [1.0, 0.0],
                            "noise_mean_profile": [0.0, 1.0],
                            "real_count": 1,
                            "noise_count": 1,
                        },
                        "generators": {
                            "REAL": {
                                "ecdf": {
                                    "profile_margin_l1": {
                                        "quantile_grid": [0.1, 0.9],
                                        "breakpoints": [-2.0, 2.0],
                                    },
                                    "mean_bin_index": {
                                        "quantile_grid": [0.1, 0.9],
                                        "breakpoints": [0.0, 1.0],
                                    },
                                    "mean_bin_value": {
                                        "quantile_grid": [0.1, 0.9],
                                        "breakpoints": [3.0, 4.0],
                                    },
                                    "tail_mass_by_start_index": {
                                        "0": {
                                            "quantile_grid": [0.1, 0.9],
                                            "breakpoints": [1.0, 1.0],
                                        },
                                        "1": {
                                            "quantile_grid": [0.1, 0.9],
                                            "breakpoints": [0.0, 1.0],
                                        },
                                    },
                                }
                            }
                        },
                        "combined_noise": {
                            "ecdf": {
                                "profile_margin_l1": {
                                    "quantile_grid": [0.1, 0.9],
                                    "breakpoints": [-2.0, 2.0],
                                },
                                "mean_bin_index": {
                                    "quantile_grid": [0.1, 0.9],
                                    "breakpoints": [0.0, 1.0],
                                },
                                "mean_bin_value": {
                                    "quantile_grid": [0.1, 0.9],
                                    "breakpoints": [3.0, 4.0],
                                },
                                "tail_mass_by_start_index": {
                                    "0": {
                                        "quantile_grid": [0.1, 0.9],
                                        "breakpoints": [1.0, 1.0],
                                    },
                                    "1": {
                                        "quantile_grid": [0.1, 0.9],
                                        "breakpoints": [0.0, 1.0],
                                    },
                                },
                            }
                        },
                    }
                }
            }
        },
    }


@dataclass(frozen=True)
class _Stats:
    length_bins: tuple[int, ...]
    span_raw_by_len: tuple[float, ...]
    chars_covered_by_len: tuple[float, ...] = (0.0, 0.0)


def test_loader_rejects_missing_profile_length_bins(tmp_path: Path) -> None:
    payload = _base_payload()
    payload.pop("profile_length_bins", None)
    fp = _write_asset(tmp_path, payload)
    with pytest.raises(ValueError, match="profile_length_bins"):
        SpanHammingLmAssetsV2.load(fp)


def test_loader_rejects_vector_length_mismatch(tmp_path: Path) -> None:
    payload = _base_payload()
    payload["profile_vector_length"] = 3
    fp = _write_asset(tmp_path, payload)
    with pytest.raises(ValueError, match="profile_vector_length"):
        SpanHammingLmAssetsV2.load(fp)


def test_loader_monotonic_fixup_allows_duplicate_breakpoints(tmp_path: Path) -> None:
    payload = _base_payload()
    payload["profile_tables"]["span_raw_by_len"]["ltr"]["100"]["combined_noise"][
        "ecdf"
    ]["profile_margin_l1"]["breakpoints"] = [1.0, 1.0]
    fp = _write_asset(tmp_path, payload)
    assets = SpanHammingLmAssetsV2.load(fp)
    stats = _Stats(length_bins=(3, 4), span_raw_by_len=(0.5, 0.5))
    scored = assets.score_profile_margin_l1_in_bucket(
        stats=stats,
        direction="ltr",
        length_bucket=100,
        clamp_min=1e-06,
        clamp_max=1.0 - 1e-06,
    )
    assert 0.0 < scored.profile_margin_l1_pct_noise < 1.0


def test_score_profile_margin_l1_interpolation_tiny_asset(tmp_path: Path) -> None:
    payload = _base_payload()
    fp = _write_asset(tmp_path, payload)
    assets = SpanHammingLmAssetsV2.load(fp)
    stats = _Stats(length_bins=(3, 4), span_raw_by_len=(0.0, 1.0))
    scored = assets.score_profile_margin_l1_in_bucket(
        stats=stats,
        direction="ltr",
        length_bucket=100,
        clamp_min=1e-06,
        clamp_max=1.0 - 1e-06,
    )
    assert scored.profile_margin_l1_raw == pytest.approx(-2.0, abs=1e-12)
    assert scored.profile_margin_l1_pct_noise == pytest.approx(0.1, abs=1e-12)
    assert scored.mean_bin_index_raw == pytest.approx(1.0, abs=1e-12)
    assert scored.mean_bin_index_pct_noise == pytest.approx(0.9, abs=1e-12)
    assert scored.mean_bin_length_raw == pytest.approx(4.0, abs=1e-12)
    assert scored.mean_bin_length_pct_noise == pytest.approx(0.9, abs=1e-12)
    assert scored.tail_mass_raw == pytest.approx(1.0, abs=1e-12)
    assert scored.tail_mass_pct_noise == pytest.approx(0.1, abs=1e-12)


def test_score_profile_margin_l1_rejects_bins_mismatch(tmp_path: Path) -> None:
    payload = _base_payload()
    fp = _write_asset(tmp_path, payload)
    assets = SpanHammingLmAssetsV2.load(fp)
    stats = _Stats(length_bins=(5, 6), span_raw_by_len=(0.5, 0.5))
    with pytest.raises(ValueError, match="length_bins mismatch"):
        assets.score_profile_margin_l1_in_bucket(
            stats=stats,
            direction="ltr",
            length_bucket=100,
            clamp_min=1e-06,
            clamp_max=1.0 - 1e-06,
        )
