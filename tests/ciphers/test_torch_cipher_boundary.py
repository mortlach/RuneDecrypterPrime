"""Host/device boundary coverage for cipher orchestration and runtime evaluation."""
from dataclasses import replace
import numpy as np
import pytest
from rdp import api
from rdp.backends.xp import to_numpy
from rdp.ciphers.ciphers_pipeline import CipherPipelineMixin
from rdp.ciphers.vigenere_cipher import RuneVigenereCipher
from rdp.ciphers.railfence_cipher import RailFenceCipher
from rdp.core.config.cipher import CipherConfig
from rdp.core.problem.instance import ProblemInstance
from rdp.core.problem.spec import ProblemSpec
from rdp.core.types import Device, KEY_DTYPE

torch = pytest.importorskip('torch')
pytestmark = pytest.mark.torch


@pytest.fixture(params=['cpu', 'cuda'])
def tensor_device(request):
    if request.param == 'cuda' and not torch.cuda.is_available():
        pytest.skip('CUDA not available')
    return request.param


@pytest.mark.parametrize('permuted', [False, True])
@pytest.mark.parametrize('interrupted', [False, True])
def test_vigenere_host_device_roundtrip_and_batch(tensor_device, permuted, interrupted):
    plaintext = (np.arange(24) % 29).astype(np.uint8)
    keys = np.array([[1, 2, 3], [4, 5, 6]], dtype=KEY_DTYPE)
    positions = np.array([2, 7], dtype=np.int64) if interrupted else None
    permutation = list(range(24))[::-1] if permuted else None
    cfg = CipherConfig(ciphertext=[], wli_data=[], name='vigenere', key_length=3, device=Device.CPU,
                       initial_text_permutation_indices=permutation)
    reference = RuneVigenereCipher(cfg)
    cipher = RuneVigenereCipher(replace(cfg, device=Device(tensor_device)))
    pt = torch.as_tensor(plaintext, device=tensor_device)
    key = torch.as_tensor(keys, device=tensor_device)
    idx = None if positions is None else torch.as_tensor(positions, device=tensor_device)
    expected = reference.encrypt(plaintext=plaintext, key=keys, interrupt_idx=positions)
    actual = cipher.encrypt(plaintext=pt, key=key, interrupt_idx=idx)
    assert isinstance(actual, np.ndarray) and actual.dtype == np.uint8
    np.testing.assert_array_equal(actual, expected)
    decoded = cipher.decrypt(ciphertext=torch.as_tensor(actual[0], device=tensor_device),
                             key=key[0], interrupt_idx=idx)
    np.testing.assert_array_equal(decoded[0], plaintext)
    assert cipher.decrypt(ciphertext=pt, key=key[:0], interrupt_idx=idx).shape == (0, 24)
    if tensor_device == 'cuda':
        assert cipher._backend == 'torch' and cipher._torch_device.type == 'cuda'


def test_host_conversion_preserves_values_and_guards(tensor_device):
    values = torch.arange(12, device=tensor_device).reshape(3, 4).T
    for convert in (CipherPipelineMixin._as_u8, CipherPipelineMixin._as_key_dtype):
        result = convert(values, 'fixture')
        assert result.flags.c_contiguous
        np.testing.assert_array_equal(result, values.cpu().numpy())
    floating = torch.tensor([1., 2.], device=tensor_device, requires_grad=True)
    np.testing.assert_array_equal(to_numpy(floating), [1., 2.])
    cipher = RuneVigenereCipher(CipherConfig(ciphertext=[], wli_data=[], name='vigenere', key_length=1))
    with pytest.raises(ValueError, match='key values'):
        cipher.decrypt(ciphertext=values[0], key=torch.tensor([-1], device=tensor_device))
    with pytest.raises(ValueError, match='1D'):
        cipher.decrypt(ciphertext=values[0], key=torch.tensor([1], device=tensor_device),
                       interrupt_idx=torch.tensor([[1]], device=tensor_device))


def test_base_cipher_accepts_device_inputs(tensor_device):
    cipher = RailFenceCipher(CipherConfig(ciphertext=[], wli_data=[], name='railfence', key_length=1))
    plaintext = torch.arange(16, dtype=torch.uint8, device=tensor_device)
    key = torch.tensor([3], device=tensor_device)
    encrypted = cipher.encrypt(plaintext=plaintext, key=key)
    decrypted = cipher.decrypt(ciphertext=torch.as_tensor(encrypted, device=tensor_device), key=key)
    np.testing.assert_array_equal(decrypted, plaintext.cpu().numpy())


def test_problem_evaluation_raw_scores_and_plaintext_resolution(tensor_device):
    plaintext = (np.arange(48) % 29).astype(np.uint8)
    keys = np.array([[1, 2, 3], [3, 2, 1]], dtype=KEY_DTYPE)
    cfg = CipherConfig(ciphertext=[], wli_data=[], name='vigenere', key_length=3, device=Device.CPU)
    ciphertext = RuneVigenereCipher(cfg).encrypt(plaintext=plaintext, key=keys[0])[0]
    cfg = replace(cfg, ciphertext=ciphertext.tolist())
    scoring = api.ScoringConfig(
        objective=api.advanced.ScoringObjective.average_log_probability(),
        character_lane_enabled=True, word_length_lane_enabled=False,
        character_order_weights={1: 1.0}, word_length_order_weights={},
        average_window_policy=api.advanced.AverageWindowPolicy.FULL_TEXT,
    )
    reference = ProblemInstance.materialise(ProblemSpec(text='', cipher_cfg=cfg, scorer_params=scoring)).problem
    problem = ProblemInstance.materialise(ProblemSpec(
        text='', cipher_cfg=replace(cfg, device=Device(tensor_device)), scorer_params=scoring)).problem
    device_keys = torch.as_tensor(keys, device=tensor_device)
    scores = problem.evaluate_keys(device_keys)
    primary, raw = problem.evaluate_keys_with_raw(device_keys, require_raw=True)
    assert isinstance(scores, np.ndarray) and scores.shape == (2,)
    np.testing.assert_allclose(scores, reference.evaluate_keys(keys), rtol=1e-5, atol=1e-6)
    np.testing.assert_allclose(primary, scores, rtol=1e-5, atol=1e-6)
    assert np.isfinite(raw).all()
    np.testing.assert_array_equal(problem.resolve_plaintext(device_keys[0]), plaintext)
    assert problem.telemetry['score_batch_fallback_scalar'] == 0
    assert problem.telemetry['score_batch_with_raw_fallback_scalar'] == 0
    if tensor_device == 'cuda':
        assert str(problem.scorer.device).startswith('cuda')
