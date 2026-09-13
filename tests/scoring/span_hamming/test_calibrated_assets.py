from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pytest
from rdp.scoring.span_hamming.calibrated_assets import SpanCalibratedAssets
pytestmark = pytest.mark.tier_a

def _write_assets(root: Path) -> Path:
    assets = root / 'assets'
    ecdf_dir = assets / 'ecdf' / 'span_x'
    ecdf_dir.mkdir(parents=True, exist_ok=True)
    cal = {'version': 'v1', 'rows': [{'direction': 'ltr', 'length_bucket': 100, 'span_neg_ref': 0.2, 'span_denom': 0.5, 'span_valid': True, 'char4_neg_ref': -11.0, 'char4_denom': 1.0, 'char4_valid': True}, {'direction': 'ltr', 'length_bucket': 200, 'span_neg_ref': 0.3, 'span_denom': 0.6, 'span_valid': True, 'char4_neg_ref': -11.0, 'char4_denom': 1.0, 'char4_valid': True}]}
    (assets / 'combined_calibration.json').write_text(json.dumps(cal), encoding='utf-8')
    for lb in (100, 200):
        meta = {'model': 'span', 'stat': 'x_span', 'direction': 'ltr', 'length_bucket': lb}
        np.savez(ecdf_dir / f'ltr_bucket_{lb}.npz', grid=np.asarray([0.0, 1.0], dtype=np.float64), q=np.asarray([0.1, 0.9], dtype=np.float64), meta_json=np.array(json.dumps(meta), dtype=np.str_))
    return assets

def test_loader_selects_nearest_bucket_with_smaller_tie_break(tmp_path: Path) -> None:
    assets_dir = _write_assets(tmp_path)
    assets = SpanCalibratedAssets.load(assets_dir)
    assert assets.select_bucket('ltr', 150) == 100
    assert assets.select_bucket('ltr', 151) == 200
    assert assets.select_bucket('ltr', 149) == 100

def test_loader_scores_span_raw_with_clamp(tmp_path: Path) -> None:
    assets_dir = _write_assets(tmp_path)
    assets = SpanCalibratedAssets.load(assets_dir)
    scored = assets.score_span_raw(direction='ltr', text_length=150, span_raw=0.45, clamp_min=0.2, clamp_max=0.8)
    assert scored.length_bucket == 100
    assert scored.x_span == pytest.approx(0.5, abs=1e-12)
    assert scored.span_pct == pytest.approx(0.5, abs=1e-12)
    assert scored.span_energy == pytest.approx(-np.log1p(-0.5), abs=1e-12)
