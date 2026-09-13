from __future__ import annotations
'Retained Autokey study using the canonical robustness recipe unchanged.'
import json
import os
from pathlib import Path
from typing import Any
from tools.robustness import cipher_solver_campaign as campaign
FAMILY = 'autokey_beam'
ASSET_PROFILE = 'ci_light'

def trial_indices(mode: str, seed: int) -> tuple[int, ...]:
    if mode == 'smoke':
        return (int(seed) % campaign.config.FULL_TRIALS_PER_FAMILY,)
    if mode == 'development':
        raise ValueError('20-case Autokey qualification belongs in tools/robustness/cipher_solver_campaign.py')
    raise ValueError("mode must be 'smoke' or 'development'")

def _output_path(output_root: Path, mode: str, seed: int) -> Path:
    if not output_root.is_absolute():
        raise ValueError('Autokey requires an absolute external output root')
    root = output_root.resolve()
    if root == campaign.REPO_ROOT or root.is_relative_to(campaign.REPO_ROOT):
        raise ValueError('Autokey development output must stay outside the repository')
    return root / 'autokey' / f'{mode}_seed{seed}.jsonl'

def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    line = json.dumps(payload, sort_keys=True, allow_nan=False) + '\n'
    with path.open('a', encoding='utf-8', newline='\n') as handle:
        handle.write(line)
        handle.flush()
        try:
            os.fsync(handle.fileno())
        except OSError:
            pass

def run_experiment(*, mode: str, seed: int, output_root: Path) -> Path:
    recipe = campaign.resolved_recipe(FAMILY)
    output = _output_path(output_root, mode, seed)
    if output.exists():
        raise FileExistsError(f'refusing to overwrite Autokey evidence: {output}')
    output.parent.mkdir(parents=True, exist_ok=True)
    trials = trial_indices(mode, seed)
    print(f"canonical recipe: {recipe['recipe_id']}")
    print(f'trial count: {len(trials)}')
    for ordinal, trial_index in enumerate(trials, start=1):
        print(f'[autokey] {ordinal}/{len(trials)} trial_id={FAMILY}.{trial_index}', flush=True)
        record = campaign.run_trial(FAMILY, trial_index, mode='pilot')
        _append_jsonl(output, {'entry_seed': seed, 'recipe_id': recipe['recipe_id'], 'recipe_fingerprint': campaign.recipe_fingerprint(FAMILY), 'asset_profile': ASSET_PROFILE, 'campaign_record': record})
    return output
__all__ = ['ASSET_PROFILE', 'FAMILY', 'run_experiment', 'trial_indices']
