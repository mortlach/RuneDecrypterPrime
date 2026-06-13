from __future__ import annotations

import re
import pytest

import numpy as np

from rune_decrypter_prime.api import run, KeySpec, SolverSpec, by_name, cipher_instance, Direction
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils.seed_utils import make_seeds_from_freq
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext_english_string
from tests.tutorials._utils import plaintext_match_rate
from tests.scoring._helpers.lm_test_guard import require_full_lm_assets

pytestmark = pytest.mark.tier_a


@pytest.mark.parametrize("optimizer", ["sa", "ga"])
def test_tutorial_mono_runs(optimizer):
    """Check that SA/GA tutorials recover text above a minimum score."""
    require_full_lm_assets(models=("char", "wli"), modes=("rtl",), poses=("nose",), ns=(2,), ecdf_stats=("logp",))

    pt_en = plaintext_english_string
    pt_idx, wli, _ = Runeglish.encode_english_to_runes(pt_en, direction=Direction.RTL.value)

    mono = cipher_instance(by_name.cipher("mono"))
    rng = np.random.default_rng(12345)
    key_fwd = rng.permutation(29).astype(np.uint8)
    ct_idx = mono.encrypt(plaintext=np.asarray(pt_idx, np.uint8), key=key_fwd)
    ct_runes = Runeglish.to_rune(ct_idx.tolist(), wli)
    seeds = make_seeds_from_freq(
        ct_runes.replace(" ", ""),
        n_keys=120,
        swaps_per_key=2 if optimizer == "ga" else 1,
        seed=12345,
        direction=Direction.RTL.value,
    )

    if optimizer == "sa":
        solver = SolverSpec.sa(
            sa_iters=1200,
            sa_init_temp=0.8,
            sa_min_temp=1e-3,
            sa_cooling=0.998,
            sa_auto_cooling=True,
            sa_reseed_interval=0,
            sa_rescue_drop_abs=0.02,
            sa_rescue_drop_ratio=0.5,
            local_improve_on_accept=True,
            plateau_rounds=60,
            plateau_min_delta=1e-4,
            stop_score=0.555,
            progress_pct=1,
            seed=12345,
        )
    else:
        solver = SolverSpec.ga(
            pop_size=144,
            generations=160,
            stop_score=0.56,
            elite_frac=0.08,
            cx_frac=0.85,
            mut_prob=0.25,
            tournament_k=4,
            plateau_rounds=20,
            progress_pct=1,
            seed=12345,
        )

    sol = run(
        text=ct_runes,
        cipher=by_name.cipher("mono"),
        key=KeySpec.permutation(len=29),
        solver=solver,
        device="cpu",
        scorer="rune",
        scorer_params=dict(
            objective="pct.logp.win10",
            char_weights={2: 0.3},
            wli_weights={2: 0.7},
            include_char=True,
            use_word_breaks=True,
            encoding_dir=Direction.RTL,
        ),
        wli_data=wli,
        encoding_dir=Direction.RTL,
        initial_keys=seeds,
    )

    recovered_rune = getattr(sol, "plaintext_rune", None)
    if not recovered_rune:
        pt_arr = getattr(sol, "plaintext", [])
        recovered_rune = Runeglish.to_rune(pt_arr, wli)
    assert isinstance(recovered_rune, str)
    match_rate = plaintext_match_rate(sol.plaintext_idx, pt_idx)
    assert match_rate >= 0.9, f"{optimizer} tutorial must reach >=90% match (got {match_rate:.3f})"

    latin_text = None
    if hasattr(Runeglish, "runes_to_latin"):
        try:
            latin_text = Runeglish.rune_to_latin(recovered_rune)
        except Exception:
            latin_text = None

    target_text = latin_text if latin_text else recovered_rune
    rx = r"[A-Z]{3,}" if latin_text else r"[\u16A0-\u16FF]{3,}"
    assert re.search(rx, target_text), "Recovered plaintext looks too random"

