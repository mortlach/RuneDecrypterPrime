from __future__ import annotations
import numpy as np
import pytest
from rdp.ciphers.interruptors import InterruptorManager
from rdp.ciphers.transposition import TranspositionManager
pytestmark = pytest.mark.tier_a

def _roundtrip_with_perm(ct: np.ndarray, interrupt_idx: list[int], perm: np.ndarray) -> np.ndarray:
    mgr = InterruptorManager()
    core, info = mgr.remove_from(ct, possible_idx=interrupt_idx)
    trans = TranspositionManager(text_mode='perm', text_perm=perm)
    permuted = trans.apply_text(core)
    restored_core = trans.undo_text(permuted)
    return mgr.insert_into(restored_core, info)

def test_interruptor_remove_insert_roundtrip():
    ct = np.array([5, 6, 7, 8, 9, 10, 11], dtype=np.uint8)
    interrupt_idx = [0, 3, 6]
    mgr = InterruptorManager()
    core, info = mgr.remove_from(ct, possible_idx=interrupt_idx)
    restored = mgr.insert_into(core, info)
    assert np.array_equal(restored, ct)
    assert np.all(np.diff(info.idx) >= 0)
    assert info.idx.min() >= 0
    assert info.idx.max() <= core.size

def test_interruptor_remove_then_text_permutation_then_inverse_roundtrip():
    ct = np.arange(10, dtype=np.uint8)
    interrupt_idx = [1, 4, 7]
    mgr = InterruptorManager()
    core, info = mgr.remove_from(ct, possible_idx=interrupt_idx)
    perm = np.array(list(reversed(range(core.size))), dtype=np.int64)
    trans = TranspositionManager(text_mode='perm', text_perm=perm)
    permuted = trans.apply_text(core)
    restored_core = trans.undo_text(permuted)
    restored = mgr.insert_into(restored_core, info)
    assert np.array_equal(restored, ct)

def test_interruptor_permutation():
    ct = np.arange(8, dtype=np.uint8)
    interrupt_idx = [2, 5]
    mgr = InterruptorManager()
    core, _info = mgr.remove_from(ct, possible_idx=interrupt_idx)
    perm = np.array(list(range(core.size)), dtype=np.int64)
    out = _roundtrip_with_perm(ct, interrupt_idx, perm)
    assert np.array_equal(out, ct)
