from __future__ import annotations
from rdp import api
import numpy as np
import pytest
from rune_decrypter_prime.ciphers.vigenere_cipher import RuneVigenereCipher
from rdp.core.config.cipher import CipherConfig
from rdp.core.problem.runtime import DecryptionProblem
from rdp.core.types import KEY_DTYPE, Direction
import rdp.data.liber_primus as lp
from rdp.data.runeglish import Runeglish
pytestmark = pytest.mark.tier_a
SOURCE_LABEL = 'welcome_pilgrim'
KEY_TEXT = 'DIVINITY'
VIGENERE_KEY = (23, 10, 1, 10, 9, 10, 16, 26)
INTERRUPTOR_POSITIONS = (48, 74, 84, 132, 159, 160, 250, 421, 443, 465, 514)

class ZeroScorer:

    def batch_score(self, pts, wli=None):
        return np.zeros((len(pts),), dtype=np.float64)

def test_welcome_pilgrim_known_key_and_interruptors_plaintext_smoke() -> None:
    """Load Welcome Pilgrim from the LP catalogue and decode one fixed attempt."""
    payload = lp.payload_from_label(SOURCE_LABEL)
    ciphertext = np.asarray(list(payload.ct_idx), dtype=np.uint8)
    wli = [list(pair) for pair in payload.wli]
    zero_pool = [index for index, value in enumerate(ciphertext.tolist()) if int(value) == 0]
    assert len(VIGENERE_KEY) == len(KEY_TEXT)
    assert set(INTERRUPTOR_POSITIONS).issubset(set(zero_pool))
    cipher_config = CipherConfig(ciphertext=ciphertext, wli_data=wli, key_length=len(VIGENERE_KEY), device='cpu', encoding_dir=Direction.RTL, name='vigenere', interruptors_cfg=api.InterruptorConfig.exact(list(INTERRUPTOR_POSITIONS)))
    cipher = RuneVigenereCipher(cipher_config)
    problem = DecryptionProblem(cipher=cipher, scorer=ZeroScorer(), c_cfg=cipher_config, s_cfg=api.ScoringConfig())
    key = np.asarray(VIGENERE_KEY, dtype=KEY_DTYPE)
    plaintext_idx = problem.resolve_plaintext(key)
    assert plaintext_idx is not None
    plaintext = [int(value) for value in plaintext_idx.tolist()]
    plaintext_latin = Runeglish.to_rune_latin(plaintext, wli)
    plaintext_runes = Runeglish.to_rune(plaintext, wli)
    plaintext_runes_ascii = plaintext_runes.encode('unicode_escape').decode('ascii')
    print('\nLP_WELCOME_PILGRIM_KNOWN_KEY_SMOKE_BEGIN')
    print('source_label:', SOURCE_LABEL)
    print('resolved_source_label:', payload.metadata['source_label'])
    print('key_text:', KEY_TEXT)
    print('vigenere_key:', list(VIGENERE_KEY))
    print('zero_pool_size:', len(zero_pool))
    print('interruptor_positions:', list(INTERRUPTOR_POSITIONS))
    print('plaintext_latin:')
    print(plaintext_latin)
    print('plaintext_runes_unicode_escape:')
    print(plaintext_runes_ascii)
    print('LP_WELCOME_PILGRIM_KNOWN_KEY_SMOKE_END')
    assert len(plaintext) == len(ciphertext)
    assert plaintext_latin.startswith('WELCOME WELCOME PILGRIM')
    assert 'COMMAND YOUR OWN SELF' in plaintext_latin
    assert plaintext_latin.strip()
    assert plaintext_runes.strip()
    for position in INTERRUPTOR_POSITIONS:
        assert plaintext[position] == int(ciphertext[position])
