"""B1-B8 release-wheel smoke, executed in an isolated Pyodide filesystem.

Fixtures/parameters match the short native and WASM qualification cases.
Reference answers are used for fixture encryption and final assertions only.
"""
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import sys
import time
import traceback
from zipfile import ZipFile


def imports():
    global rdp, api
    import rdp
    from rdp import api
    assert sys.platform == 'emscripten' and __debug__
    package = Path(rdp.__file__).resolve().parent
    assert 'site-packages' in package.parts, package
    # Compare the installed package to the exact wheel handed to the launcher.
    with ZipFile(os.environ['RDP_SMOKE_WHEEL']) as wheel:
        for name in wheel.namelist():
            if name.startswith('rdp/') and not name.endswith('/'):
                assert (package.parent / name).read_bytes() == wheel.read(name), name
    return {'rdp_file': rdp.__file__, 'python': sys.version, 'platform': sys.platform}


def extensions():
    names = ('rdp.scoring.language_model._fastlm', 'rdp.scoring.hamming._hamming',
             'rdp.scoring.span_hamming._span_hamming_fast')
    paths = {name: importlib.import_module(name).__file__ for name in names}
    assert all(Path(path).read_bytes().startswith(b'\0asm') for path in paths.values())
    return paths


def package_data():
    from rdp.data import asset_paths
    package = Path(rdp.__file__).parent
    root = asset_paths.find_assets_root()
    assert root == (package / 'data/assets').resolve()
    manifest = json.loads((package / 'data/assets_manifest_ci_light_v1.json').read_text())
    expected = {row['final_relpath'] for row in manifest['installed_assets']}
    expected.add('language_model/lmp/index.json')
    assert {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()} == expected
    for row in manifest['installed_assets']:
        data = (root / row['final_relpath']).read_bytes()
        assert len(data) == row['size_bytes'] and hashlib.sha256(data).hexdigest() == row['sha256']
    assert json.loads((root / 'language_model/lmp/index.json').read_text())
    assert (package / 'data/liber_primus/solved_plaintext/welcome_pilgrim.txt').is_file()
    return {'manifest_assets': len(manifest['installed_assets']), 'asset_root': str(root)}


def known_key():
    plaintext, key = (0, 1, 2, 3, 4, 5), (3, 5)
    cipher = api.CipherSpec.vigenere()
    ciphertext = api.encrypt(plaintext, cipher=cipher, key=key)
    assert api.decrypt(ciphertext, cipher=cipher, key=key) == plaintext
    return {'exact_roundtrip': True}


def scoring():
    candidate = api.RuneInput('THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG')
    config = api.ScoringConfig(character_lane_enabled=True, wli_lane_enabled=False,
        character_order_weights={2: 1.0}, wli_order_weights={},
        backend=api.advanced.ScorerBackend.NUMPY)
    scalar = api.score(candidate, scoring=config)
    batch = api.score_many((candidate,), scoring=config)
    assert math.isfinite(scalar) and batch == (scalar,)
    assert scalar == 0.24252399428430918
    return {'scalar': scalar, 'batch': batch, 'objective': config.objective.to_dict()}


def solve(spec, key, plaintext):
    assert spec.initial_keys is None and spec.solver.parameters.get('target_score') is None
    result = api.run(spec)
    assert isinstance(result, api.RunResult)
    assert result.key == key and result.plaintext_indices == tuple(plaintext)
    assert result.solver_report.effective_seed == spec.solver.seed
    assert result.solver_report.evaluations > 0
    assert result.score == result.scorer_report.score and math.isfinite(result.score)
    assert not any((result.oracle.used_for_scoring, result.oracle.used_for_ranking,
                    result.oracle.used_for_stop))
    return {'key': result.key, 'runes_recovered': len(plaintext), 'score': result.score,
            'seed': result.solver_report.effective_seed,
            'evaluations': result.solver_report.evaluations,
            'stop_reason': result.status.stop_reason.value}


def beam():
    # tutorials/v1/getting_started/02_first_search.py
    plaintext = (2, 18, 4, 18, 7, 24, 15, 24, 16, 24, 17, 20, 18, 15,
                 18, 16, 3, 1, 16, 1, 9, 23, 18, 4, 24, 16, 4, 18, 18)
    key = (7,)
    cipher = api.CipherSpec.rail_fence(minimum_rails=2, maximum_rails=8)
    spec = api.RunSpec(
        problem_input=api.RuneInput(api.encrypt(plaintext, cipher=cipher, key=key)),
        cipher=cipher, key_space=api.KeySpec.scalar(minimum=2, maximum=8),
        solver=api.SolverSpec.beam_search(width=8, rounds=None, seed=7),
        scoring=api.ScoringConfig(character_lane_enabled=True, wli_lane_enabled=False,
            character_order_weights={1: 0.2, 2: 0.8}, wli_order_weights={}),
        text_direction=api.TextDirection.LTR)
    return solve(spec, key, plaintext)


def ga():
    # Random branch of tests/solvers/test_permutation_optimizers.py; no answer seed.
    from rdp.data.runeglish import Runeglish
    plaintext, wli, _ = Runeglish.encode_english_to_runes(
        'columnar permutation solvers must stay bijective', direction=api.TextDirection.LTR)
    plaintext = tuple(int(v) for v in plaintext)
    key = (2, 0, 3, 1)
    cipher = api.CipherSpec.columnar(columns=4, alphabet_size=29)
    spec = api.RunSpec(
        problem_input=api.RuneInput(api.encrypt(plaintext, cipher=cipher, key=key),
                                    word_length_information=wli),
        cipher=cipher, key_space=api.KeySpec.permutation(length=4),
        solver=api.SolverSpec.genetic_algorithm(population_size=32, generations=24,
            elite_fraction=0.15, mutation_probability=0.25, seed=9001),
        scoring=api.ScoringConfig(), telemetry_enabled=False, text_direction=api.TextDirection.LTR)
    return solve(spec, key, plaintext)


def liber_primus():
    reference = api.liber_primus.source('welcome_pilgrim')
    source = api.liber_primus.load_source('welcome_pilgrim')
    plaintext = api.liber_primus.load_plaintext('welcome_pilgrim')
    assert reference.ref['label'] == source.metadata['source_label'] == plaintext.source_label
    assert plaintext.source_label == 'red_rune.welcome_pilgrim'
    assert len(source.indices) == len(source.word_length_information) == 515
    assert len(plaintext.indices) == len(plaintext.word_length_information) == 515
    assert plaintext.metadata['word_count'] == 124 and plaintext.runes and plaintext.rune_latin
    assert plaintext == api.liber_primus.load_plaintext('solved.welcome_pilgrim')
    assert all(0 <= p < length for p, length in source.word_length_information)
    return {'label': plaintext.source_label, 'runes': 515, 'words': 124}


def main():
    result = {'status': 'PASS', 'checks': {}}
    started = time.perf_counter()
    cases = (imports, extensions, package_data, known_key, scoring, beam, ga, liber_primus)
    for number, function in enumerate(cases, 1):
        start = time.perf_counter()
        try:
            detail = function()
            assert not any(n == 'torch' or n.startswith('torch.') for n in sys.modules)
            row = {'status': 'PASS', 'detail': detail}
        except Exception:
            row = {'status': 'FAIL', 'error': traceback.format_exc()}
            result['status'] = 'FAIL'
        row['seconds'] = time.perf_counter() - start
        result['checks'][f'B{number}'] = row
        print(f'B{number} {function.__name__}: {row["status"]} ({row["seconds"]:.3f}s)', flush=True)
        if row['status'] == 'FAIL':
            print(row['error'], flush=True)
            break
    result['seconds'] = time.perf_counter() - started
    return result


if __name__ == '__main__':
    SMOKE_RESULT = main()
    SMOKE_JSON = json.dumps(SMOKE_RESULT, ensure_ascii=False)
    if SMOKE_RESULT['status'] != 'PASS':
        raise RuntimeError('WASM smoke failed; see B1-B8 results')
