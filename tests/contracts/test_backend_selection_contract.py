from __future__ import annotations
from pathlib import Path
import subprocess
import sys
import pytest
import rdp
from rdp.backends import device, xp

ROOT = Path(__file__).resolve().parents[2]


def _run_isolated(script: str) -> None:
    source_root = ROOT / "src"
    launch = f"import sys\nsys.path.insert(0, {str(source_root)!r})\n{script}"
    completed = subprocess.run(
        [sys.executable, "-I", "-B", "-c", launch],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_process_uses_current_worktree_source() -> None:
    source_package = (ROOT / "src" / "rdp").resolve()
    assert Path(rdp.__file__).resolve().parent == source_package
    assert Path(rdp.backends.__file__).resolve().parent == source_package / "backends"


def test_root_package_import_is_lazy() -> None:
    _run_isolated("""
import rdp
import sys
assert rdp.__all__ == ['api']
assert 'rdp.api' not in sys.modules
assert 'torch' not in sys.modules
assert 'cupy' not in sys.modules
""")


def test_backend_package_import_is_optional_dependency_lazy() -> None:
    _run_isolated("""
import builtins
import sys
real_import = builtins.__import__
attempted = []
def guarded_import(name, *args, **kwargs):
    if name.split('.', 1)[0] in {'torch', 'cupy'}:
        attempted.append(name)
        raise AssertionError(f'optional dependency imported eagerly: {name}')
    return real_import(name, *args, **kwargs)
builtins.__import__ = guarded_import
import rdp.backends
assert attempted == [], attempted
assert 'rdp.api' not in sys.modules
assert 'torch' not in sys.modules
assert 'cupy' not in sys.modules
assert 'rune_decrypter_prime.scoring.language_model._fastlm' not in sys.modules
assert 'rune_decrypter_prime.scoring.hamming._hamming' not in sys.modules
assert 'rune_decrypter_prime.scoring.span_hamming._span_hamming_fast' not in sys.modules
""")


def test_root_api_is_an_honest_lazy_attribute() -> None:
    _run_isolated("""
import rdp
import sys
assert 'rdp.api' not in sys.modules
api = rdp.api
assert api.__name__ == 'rdp.api'
assert sys.modules['rdp.api'] is api
assert rdp.__all__ == ['api']
namespace = {}
exec('from rdp import *', namespace)
assert namespace['api'] is api
""")


def test_from_root_import_api_uses_canonical_module() -> None:
    _run_isolated("""
from rdp import api
assert api.__name__ == 'rdp.api'
""")


def test_device_cpu_request_uses_numpy_backend() -> None:
    selected_device, backend = device.get_device("cpu")
    assert selected_device == "cpu"
    assert backend.backend == "numpy"


def test_device_cuda_preference_tries_exact_order(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts: list[str] = []
    cupy_backend = object()

    def select_backend(name: str):
        attempts.append(name)
        if name == "torch":
            raise RuntimeError("unavailable")
        return "cuda", cupy_backend

    monkeypatch.setattr(device, "select_backend", select_backend)
    assert device.get_device("cuda", cuda_backend_preference="torch") == (
        "cuda",
        cupy_backend,
    )
    assert attempts == ["torch", "cupy"]

def test_explicit_cuda_request_does_not_silently_fallback_to_numpy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(xp, 'have_cupy', lambda: False)
    monkeypatch.setattr(xp, 'have_torch_cuda', lambda: False)
    with pytest.raises(RuntimeError, match='CUDA requested'):
        xp.select_backend('cuda')

def test_explicit_torch_request_does_not_fallback_to_numpy_when_torch_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(xp, '_torch', None)
    with pytest.raises(ImportError, match='torch not available'):
        xp.select_backend('torch')

def test_auto_request_may_fallback_to_numpy_when_optional_backends_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(xp, '_torch', None)
    monkeypatch.setattr(xp, '_cp', None)
    monkeypatch.setattr(xp, 'have_cupy', lambda: False)
    monkeypatch.setattr(xp, 'have_torch_cuda', lambda: False)
    device, backend = xp.select_backend('auto')
    assert device == 'cpu'
    assert backend.backend == 'numpy'
