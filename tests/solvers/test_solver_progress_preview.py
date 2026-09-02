from __future__ import annotations
import numpy as np
import pytest
from rdp.solvers.solver_base import SolverBase
from rdp.core.types import SolverName, KEY_DTYPE, Device, Direction
pytestmark = pytest.mark.tier_a

class _DummyKeyOps:

    def __init__(self, length: int):
        self.caps = type('Caps', (), {'length': length, 'ops': set()})()
        self.dtype = KEY_DTYPE

    def normalize(self, row):
        return np.asarray(row, dtype=KEY_DTYPE)

class _DummyCipher:

    def decrypt(self, ciphertext, key):
        return np.asarray(ciphertext, dtype=np.uint8)

class _DummyProblem:

    def __init__(self):
        self.ciphertext = np.array([0, 1, 2, 3, 4, 5], dtype=np.uint8)
        self.cipher = _DummyCipher()
        self.keyops = _DummyKeyOps(length=self.ciphertext.size)
        self.wli_data = None
        self.telemetry = type('Tel', (), {'tokens_processed': 42, 'decrypt_time_s': 0.01, 'score_time_s': 0.02, 'candidates_evaluated': 7})()
        self.c_cfg = type('Cfg', (), {'device': Device.CPU, 'encoding_dir': Direction.RTL})()

class _PreviewSolver(SolverBase):

    def __init__(self, progress_callback=None):
        super().__init__(_DummyProblem(), optimizer_name=SolverName.GA, params={'print_progress': True, 'progress_pct': 50, 'progress_preview_chars': 12}, rng=np.random.default_rng(0), seed_keys=None, stop_score=None, verbose=True, log_interval=1, progress_callback=progress_callback)

    def _score_batch(self, keys: np.ndarray) -> np.ndarray:
        return np.zeros(keys.shape[0], dtype=np.float32)

    def _evaluate_keys(self, keys: np.ndarray) -> np.ndarray:
        return self._score_batch(keys)

def test_progress_preview_prints_text_snippet(capfd: pytest.CaptureFixture[str]) -> None:
    solver = _PreviewSolver()
    best_key = np.arange(solver.K, dtype=np.uint8)
    solver._progress_pct(current_step=1, total_steps=2, best_score=0.42, evals=10, preview_key=best_key)
    out = capfd.readouterr().out
    assert '[ga' in out, f'console progress missing GA prefix: {out!r}'
    assert 'text="' in out, f'plaintext preview missing from console output: {out!r}'


def test_progress_callback_is_runtime_state_and_still_receives_progress() -> None:
    received = []
    solver = _PreviewSolver(lambda payload, key: received.append((payload, key)))
    best_key = np.arange(solver.K, dtype=np.uint8)

    solver._progress_pct(
        current_step=1,
        total_steps=2,
        best_score=0.42,
        evals=10,
        preview_key=best_key,
    )

    assert len(received) == 1
    payload, key = received[0]
    assert payload['best_score'] == pytest.approx(0.42)
    assert key == best_key.astype(int).tolist()
    assert not hasattr(solver.problem.telemetry, 'progress_callback')
