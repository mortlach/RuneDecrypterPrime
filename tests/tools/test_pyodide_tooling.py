"""Fast native guards for the portable smoke recipes; WASM is tested by Node."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOLING = ROOT / 'tools/pyodide'
pytestmark = pytest.mark.tier_a


def test_version_pins_are_consumed_by_both_entry_points():
    pins = json.loads((TOOLING / 'versions.json').read_text())
    assert pins['python'] == '3.14.2'
    assert pins['pyodide'] == '314.0.6'
    assert pins['emscripten'] == '5.0.3'
    assert pins['node'] == '24.19.0'
    assert pins['wheel_tag'] == 'cp314-cp314-pyemscripten_2026_0_wasm32'
    for name in ('build_wheel.sh', 'run_smoke.mjs'):
        assert 'versions.json' in (TOOLING / name).read_text()
    assert b'\r' not in (TOOLING / 'build_wheel.sh').read_bytes()


@pytest.mark.parametrize('case', ['known_key', 'scoring', 'beam', 'ga', 'liber_primus'])
def test_permanent_smoke_recipe_on_native_cpu(case):
    from rdp import api
    spec = importlib.util.spec_from_file_location('rdp_wasm_smoke', TOOLING / 'smoke.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert not hasattr(module, 'SMOKE_RESULT'), 'Import must not execute the WASM smoke'
    module.api = api
    result = getattr(module, case)()
    assert result
