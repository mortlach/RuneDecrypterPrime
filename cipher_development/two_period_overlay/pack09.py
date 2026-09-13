from __future__ import annotations
'IDE-friendly WP6 Pack 09 one-word d30 runner.'
import json
from pathlib import Path
from cipher_development.two_period_overlay.experiment_e import contract_preflight, planned_runtime, run_p13_p31_one_word_d30_panel
from cipher_development.two_period_overlay.config import MASTER_SEED
REPO_ROOT = Path(__file__).resolve().parents[2]

def run_experiment(*, mode: str, seed: int, output_root: Path) -> Path:
    if seed != MASTER_SEED:
        raise ValueError(f'Pack 09 uses its frozen deterministic seed {MASTER_SEED}')
    if not output_root.is_absolute():
        raise ValueError('Pack 09 requires an absolute external output root')
    root = output_root.resolve() / 'two_period_pack09'
    if root == REPO_ROOT or root.is_relative_to(REPO_ROOT):
        raise ValueError('Pack 09 output must stay outside the repository')
    if mode == 'smoke':
        destination = root / f'contract_smoke_seed{seed}.json'
        if destination.exists():
            raise FileExistsError(f'refusing to overwrite Pack 09 smoke evidence: {destination}')
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = {'experiment': 'two_period_pack09', 'mode': mode, 'seed': seed, 'asset_profile': 'ci_light', 'profiles': ['S2', 'F1'], 'contract_preflight': contract_preflight(REPO_ROOT), 'planned_runtime': planned_runtime()}
        destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
        return destination
    if mode == 'development':
        return run_p13_p31_one_word_d30_panel(REPO_ROOT, output_root=root)
    raise ValueError("mode must be 'smoke' or 'development'")
