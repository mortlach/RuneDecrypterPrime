from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple
import json
import numpy as np
import pytest
from rune_decrypter_prime.scoring.language_model.paths import default_lm_root, load_index, expand_pattern

@dataclass(frozen=True)
class MissingAsset:
    kind: str
    model: str
    mode: str
    pos: str
    n: int
    stat: str | None = None
    path: Path | None = None

def require_full_lm_assets(root: Path | None=None, *, models: Tuple[str, ...]=('char', 'wli'), modes: Tuple[str, ...]=('ltr', 'rtl'), poses: Tuple[str, ...]=('nose', 'wise'), ns: Tuple[int, ...]=(1, 2, 3, 4), ecdf_stats: Tuple[str, ...]=('logp', 'zsum', 'madsum')) -> Tuple[Path, object]:
    """Return (lm_root, index) if the *full* asset set is present; otherwise pytest.skip()."""
    lm_root = (root or default_lm_root()).resolve()
    if not lm_root.exists():
        pytest.skip(f'LM root not found: {lm_root}')
    try:
        idx = load_index(lm_root)
    except Exception as exc:
        pytest.skip(f'LM index.json not readable under {lm_root}: {exc}')
    missing: List[MissingAsset] = []
    for model in models:
        model_cfg = idx.models.get(model)
        if not model_cfg:
            missing.append(MissingAsset(kind='index', model=model, mode='*', pos='*', n=-1, path=None))
            continue
        joint_pat = model_cfg.get('joint_pattern')
        ecdf_pat = model_cfg.get('ecdf_pattern')
        if not joint_pat or not ecdf_pat:
            missing.append(MissingAsset(kind='index', model=model, mode='*', pos='*', n=-1, path=None))
            continue
        for mode in modes:
            for pos in poses:
                for n in ns:
                    joint_fp = expand_pattern(lm_root, joint_pat, mode=mode, pos=pos, n=n)
                    if not joint_fp.exists():
                        missing.append(MissingAsset(kind='joint', model=model, mode=mode, pos=pos, n=n, path=joint_fp))
                    for st in ecdf_stats:
                        ecdf_fp = expand_pattern(lm_root, ecdf_pat, mode=mode, pos=pos, n=n, stat=st)
                        if not ecdf_fp.exists():
                            missing.append(MissingAsset(kind='ecdf', model=model, mode=mode, pos=pos, n=n, stat=st, path=ecdf_fp))
                        else:
                            try:
                                arr = np.load(ecdf_fp, allow_pickle=True)
                                if 'meta_json' not in arr:
                                    missing.append(MissingAsset(kind='ecdf_meta', model=model, mode=mode, pos=pos, n=n, stat=st, path=ecdf_fp))
                                    continue
                                raw_meta = arr['meta_json']
                                if isinstance(raw_meta, np.ndarray):
                                    if raw_meta.shape == ():
                                        raw_meta = raw_meta.item()
                                    elif raw_meta.size == 1:
                                        raw_meta = raw_meta.reshape(()).item()
                                if isinstance(raw_meta, bytes):
                                    meta_json = raw_meta.decode('utf-8')
                                elif isinstance(raw_meta, str):
                                    meta_json = raw_meta
                                else:
                                    meta_json = ''
                                if not meta_json:
                                    missing.append(MissingAsset(kind='ecdf_meta', model=model, mode=mode, pos=pos, n=n, stat=st, path=ecdf_fp))
                                    continue
                                _ = json.loads(meta_json)
                                grid = np.asarray(arr.get('grid'))
                                q = np.asarray(arr.get('q'))
                                if grid.dtype != np.float64 or q.dtype != np.float64:
                                    missing.append(MissingAsset(kind='ecdf_invalid', model=model, mode=mode, pos=pos, n=n, stat=st, path=ecdf_fp))
                                    continue
                                if grid.ndim != 1 or q.ndim != 1 or grid.size != q.size:
                                    missing.append(MissingAsset(kind='ecdf_invalid', model=model, mode=mode, pos=pos, n=n, stat=st, path=ecdf_fp))
                                    continue
                                if grid.size > 1 and (not bool(np.all(np.diff(grid) > 0.0))):
                                    missing.append(MissingAsset(kind='ecdf_invalid', model=model, mode=mode, pos=pos, n=n, stat=st, path=ecdf_fp))
                                    continue
                                if q.size > 1 and (not bool(np.all(np.diff(q) > 0.0))):
                                    missing.append(MissingAsset(kind='ecdf_invalid', model=model, mode=mode, pos=pos, n=n, stat=st, path=ecdf_fp))
                                    continue
                                if q.size:
                                    q0 = float(q[0])
                                    q1 = float(q[-1])
                                    if not 0.0 <= q0 < q1 <= 1.0:
                                        missing.append(MissingAsset(kind='ecdf_invalid', model=model, mode=mode, pos=pos, n=n, stat=st, path=ecdf_fp))
                                        continue
                            except Exception:
                                missing.append(MissingAsset(kind='ecdf_meta', model=model, mode=mode, pos=pos, n=n, stat=st, path=ecdf_fp))
    if missing:
        examples = missing[:12]
        lines = [f'LM asset set incomplete under {lm_root}. Missing examples:']
        for m in examples:
            if m.kind in ('joint', 'ecdf', 'ecdf_meta', 'ecdf_invalid'):
                lines.append(f'  - {m.kind}: {m.model}/{m.mode}/{m.pos}/n{m.n}' + (f'/{m.stat}' if m.stat else '') + (f'  ({m.path})' if m.path else ''))
            else:
                lines.append(f'  - {m.kind}: {m.model}')
        if len(missing) > len(examples):
            lines.append(f'  ... and {len(missing) - len(examples)} more')
        pytest.skip('\n'.join(lines))
    return (lm_root, idx)
