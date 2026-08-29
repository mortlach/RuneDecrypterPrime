"""GPU smoke tests for the Stage-2 pipeline."""
from __future__ import annotations
import pytest
from rune_decrypter_prime.core.types import Device
from tests._helpers.runner import run_vigenere_roundtrip_baseline
torch = pytest.importorskip('torch', reason='Torch backend required for CUDA smoke test')
pytestmark = [pytest.mark.tier_a, pytest.mark.cuda]

@pytest.mark.skipif(not torch.cuda.is_available(), reason='CUDA device not available')
def test_stage2_solver_runs_on_cuda_and_emits_cuda_telemetry():
    """Ensure the Stage-2 solver stack runs end-to-end on CUDA and reports the device."""
    _, _, meta = run_vigenere_roundtrip_baseline(device=Device.CUDA, seed=12345, beam_width=4, preview=32, logging_over={'print_progress': False}, use_test_key=False)
    telemetry = meta.get('telemetry', {})
    run_block = telemetry.get('run', {})
    assert str(run_block.get('device')).startswith('cuda')
    scorer = telemetry.get('scorer', {})
    assert str(scorer.get('device')).startswith('cuda')
    progress_events = telemetry.get('solver_progress', [])
    assert progress_events, 'Expected solver_progress events on CUDA run'
