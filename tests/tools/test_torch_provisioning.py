import json
import subprocess
import pytest
from tools import torch_runtime as runtime


def test_compatible_wheel_selection_and_old_driver_blocks(monkeypatch):
    monkeypatch.setattr(runtime.platform, 'machine', lambda: 'AMD64')
    gpu = dict(name='fixture', driver='596.08', capability='8.6')
    assert runtime.select_wheel([gpu], 'Windows') == 'cu126'
    assert runtime.select_wheel([{**gpu, 'capability': '12.0'}], 'Windows') == 'cu130'
    with pytest.raises(RuntimeError, match='driver'):
        runtime.select_wheel([{**gpu, 'driver': '520.00'}], 'Windows')


def test_missing_gpu_is_explicit_and_required_gpu_blocks(monkeypatch):
    monkeypatch.setattr(runtime, 'probe_cuda', lambda: subprocess.CompletedProcess([], 1, '', 'no torch'))
    monkeypatch.setattr(runtime, 'detect_gpus', lambda: [])
    def no_install(*args):
        pytest.fail('must not install without a detected GPU')
    assert runtime.provision_torch(no_install)['status'] == 'not_selected'
    with pytest.raises(RuntimeError, match='requires'):
        runtime.provision_torch(no_install, required=True)


def test_existing_verified_cuda_is_reused(monkeypatch):
    monkeypatch.setattr(runtime, 'probe_cuda', lambda: subprocess.CompletedProcess(
        [], 0, json.dumps({'status': 'verified'}), ''))
    def no_install(*args):
        pytest.fail('must reuse verified runtime')
    assert runtime.provision_torch(no_install)['action'] == 'reused'


def test_cpu_wheel_replaced_and_verification_required(monkeypatch):
    results = iter([subprocess.CompletedProcess([], 1, '', 'CPU-only'),
                    subprocess.CompletedProcess([], 0, '{"status":"verified"}', '')])
    monkeypatch.setattr(runtime, 'probe_cuda', lambda: next(results))
    monkeypatch.setattr(runtime, 'detect_gpus', lambda: [dict(capability='8.6', driver='596.08')])
    monkeypatch.setattr(runtime, 'select_wheel', lambda _: 'cu126')
    commands = []
    result = runtime.provision_torch(lambda label, args: commands.append((label, args)), required=True)
    assert result['action'] == 'installed'
    assert f'torch=={runtime.TORCH_VERSION}+cu126' in commands[0][1]
    assert commands[1][0] == 'Verify CUDA arithmetic'
