from __future__ import annotations
from rdp import api
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
import pytest
from rune_decrypter_prime.core.config.logging_config import (
    init_logging,
    get_run_dir,
)
from rune_decrypter_prime.data.cipher_tests.baseline_registry import BASELINE


def _init_session_logging() -> Path:
    """
    Initialize logging once per pytest session using the public dataclass API,
    then return the resolved run_dir.
    """
    cfg = api.LoggingConfig(
        run_category="tests",
        label="pytest",
        write_event_log=True,
        verbose=False,
        show_progress=False,
    )
    run_dir = init_logging(cfg)
    return run_dir


def _ensure_test_artifacts_base(run_dir: Path) -> Path:
    """
    tests write to: output/tests/<run_id>/artifacts/tests/<sanitized node>/
    (No env vars; fully derived from config + run_dir.)
    """
    base = (run_dir / "artifacts" / "tests").resolve()
    base.mkdir(parents=True, exist_ok=True)
    return base


def pytest_sessionstart(session: pytest.Session) -> None:
    run_dir = _init_session_logging()
    _ensure_test_artifacts_base(run_dir)


def _sanitize(nodeid: str) -> str:
    return "".join((ch if ch.isalnum() or ch in "._-/" else "-" for ch in nodeid))[:200]


@pytest.fixture
def test_out_dir(request) -> Path:
    base = get_run_dir() / "artifacts" / "tests"
    base.mkdir(parents=True, exist_ok=True)
    p = (base / _sanitize(request.node.nodeid)).resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


@pytest.fixture(autouse=True)
def seed_rng():
    """
    Deterministic seeds across python.random, numpy, and torch (incl. CUDA).
    Source of truth: BASELINE['seed'] (no env overrides).
    """
    import numpy as np

    seed = int(BASELINE.get("seed", 12345))
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except Exception:
        pass


@pytest.fixture(scope="session")
def device_matrix():
    """
    Available devices for this test run.

    Rules:
    - CPU is always considered available for Tier-A.
    - CUDA is included iff torch with a CUDA device is available.
    - If BASELINE["devices"] is present, intersect with the physically available set,
      but never remove CPU for Tier-A.
    """
    available = {"cpu"}
    try:
        import torch
    except Exception:
        torch = None
    if torch and torch.cuda.is_available():
        available.add("cuda")
    want = set(BASELINE.get("devices") or [])
    if want:
        wanted_plus_cpu = {"cpu"} | want & {"cuda"}
        return sorted(available & wanted_plus_cpu)
    return sorted(available)


@pytest.fixture(scope="session")
def small_problem_cfg():
    """
    Tiny knobs for Tier A speed (<5s CPU). Derived from BASELINE and clamped.
    Returned dict intentionally contains both nested and flat keys to satisfy
    existing tests.
    """
    base = dict(BASELINE.get("budgets", {}))
    beam = dict(base.get("beam", {}))
    bw = int(beam.get("beam_width", 8))
    beam["beam_width"] = min(bw, 8)
    return {
        "seed": int(BASELINE.get("seed", 12345)),
        "preview": 64,
        "beam": beam,
        "beam_width": beam["beam_width"],
        "population": int(base.get("ga", {}).get("population", 16)),
        "generations": int(base.get("ga", {}).get("generations", 8)),
        "batch_size": 32,
        "patience": 2,
    }
