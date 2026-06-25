from __future__ import annotations

"""Periodic columnar simple P7 col-then-sub pretty-print tutorial."""

import sys
from pathlib import Path
from typing import Sequence

_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import numpy as np

from rune_decrypter_prime.api import Direction, KeySpec, NormalizedInput, RunSpec, SolverSpec, by_name, cipher_instance, print_rdp_result, run
from rune_decrypter_prime.core.config.scoring import ScoringConfig
from rune_decrypter_prime.core.types import ScorerImpl
from rune_decrypter_prime.data.cipher_tests.plaintext import long_plaintext_string
from rune_decrypter_prime.keyops.periodic_structured_matrix_ops import PeriodicStructuredMatrixKeyOps
from rune_decrypter_prime.scoring.language_model.language_model_prime import LanguageModelPrime
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils import tutorial_pretty as pretty
from rune_decrypter_prime.utils.tutorial_output import print_tutorial_debug_preview
from rune_decrypter_prime.utils.seed_utils_periodic_columnar import SeedPlan, generate_seed_keys_periodic_columnar
from rune_decrypter_prime.utils.tutorial_utils import oracle_stop_score, print_stop_summary

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ALPHABET = 29
PERIOD = 7
COLUMNS = 7
ORDER = "col_then_sub"
TUTORIAL_SEED = 12345
CIPHERTEXT_SEED = 54321
USE_SEEDS = True
SEED_KEYS = 128
SEED_STARTS = 48
SEED_REFINE_STEPS = 600
SEED_TEMP_START = 0.40
SEED_TEMP_END = 0.04
STAGE1_STEPS = 20000
STAGE1_RESTARTS = 10
STAGE1_INNER_BATCH = 192
STAGE1_SLIP_EVERY = 60
STAGE1_SLIP_BLOCKS = 1
STAGE1_COL_EVERY = 1
STAGE1_COL_BATCH = 512
STAGE1_STALL_ROUNDS = 260
STAGE1_STALL_SLIP_LIMIT = 4
STAGE1_SLIP_SWAPS = 50
STAGE2_STEPS = 18000
STAGE2_RESTARTS = 8
STAGE2_INNER_BATCH = 192
STAGE2_SLIP_EVERY = 60
STAGE2_SLIP_BLOCKS = 1
STAGE2_COL_EVERY = 1
STAGE2_COL_BATCH = 512
STAGE2_STALL_ROUNDS = 260
STAGE2_STALL_SLIP_LIMIT = 4
STAGE2_SLIP_SWAPS = 50
MIN_MATCH_RATIO = 1.0


def _preview(text: str, n: int = 160) -> str:
    return text if len(text) <= n else text[:n] + "..."


def _match_ratio(solution, pt_idx: Sequence[int]) -> float:
    guess = getattr(solution, "plaintext_idx", None)
    if guess is None:
        return 0.0
    a = np.asarray(guess, dtype=np.int64).reshape(-1)
    b = np.asarray(pt_idx, dtype=np.int64).reshape(-1)
    n = min(a.size, b.size)
    return float(np.mean(a[:n] == b[:n])) if n > 0 else 0.0


def main() -> None:
    pretty.print_rdp_identity()
    pretty.print_initialising()
    pretty.print_tutorial_contract(
        name='Periodic columnar simple P7 col-then-sub',
        cipher='periodic columnar',
        solver='hybrid',
        direction='rtl',
        expected_result='exact solve',
        uses_reference_stop_score=True,
    )
    encoding_dir = Direction.RTL
    pt_idx, wli, pt_runes = Runeglish.encode_english_to_runes(long_plaintext_string, direction=encoding_dir.value)
    pt_arr = np.asarray(pt_idx, dtype=np.uint8)

    print("Periodic columnar simple problem")
    print(f"encoding direction: {encoding_dir.value}")
    print(f"period={PERIOD}, columns={COLUMNS}, order={ORDER}")
    print("stages: raw char34 seed generation -> char-only Kaeding -> full scorer Kaeding")
    print("Plaintext preview:", _preview(pt_runes))

    cipher_spec = by_name.cipher("periodic_columnar", period=PERIOD, alphabet_size=ALPHABET, columns=COLUMNS, order=ORDER)
    key_spec = KeySpec.periodic_columnar(period=PERIOD, alphabet_size=ALPHABET, columns=COLUMNS)
    cipher = cipher_instance(cipher_spec)

    rng_key = np.random.default_rng(CIPHERTEXT_SEED)
    keyops = PeriodicStructuredMatrixKeyOps(period=PERIOD, A=ALPHABET, columns=COLUMNS)
    true_key = keyops.random(rng_key).astype(np.uint8, copy=False)
    ct_idx = cipher.encrypt_single(plaintext=pt_arr, key=true_key)
    ct_idx_list = [int(v) for v in ct_idx.tolist()]
    ct_runes = Runeglish.to_rune(ct_idx_list, wli)

    print("Ciphertext preview:", _preview(ct_runes))
    print_tutorial_debug_preview(label="plaintext", idx=pt_idx, wli=wli, direction=encoding_dir)
    print_tutorial_debug_preview(label="ciphertext", idx=ct_idx_list, wli=wli, direction=encoding_dir)

    lm = LanguageModelPrime(lm_root=None, smoothing=None, oov_policy=None, include_char=True)

    def score_pt_char34(pt: np.ndarray) -> float:
        seq = np.asarray(pt, dtype=np.uint8).reshape(-1).tolist()
        length = len(seq)
        if length <= 0:
            return float("-inf")
        s3 = lm.score([seq], None, direction=encoding_dir.value, se="nose", n=3, model="char")[0].logprob_sum / max(1, length - 3 + 1)
        s4 = lm.score([seq], None, direction=encoding_dir.value, se="nose", n=4, model="char")[0].logprob_sum / max(1, length - 4 + 1)
        return float(0.5 * s3 + 0.5 * s4)

    def score_key_char34(full_key: Sequence[int]) -> float:
        k = np.asarray(full_key, dtype=np.uint8).reshape(-1)
        pt_guess = cipher.decrypt_single(ciphertext=ct_idx, key=k)
        return score_pt_char34(pt_guess)

    oracle_char34 = score_pt_char34(pt_arr)
    true_key_char34 = score_key_char34(true_key.tolist())
    print(f"Seed oracle (char34): {oracle_char34:.6f} | true_key_score: {true_key_char34:.6f}")

    seed_keys = None
    if USE_SEEDS:
        seed_cfg = ScoringConfig(
            encoding_dir=encoding_dir,
            include_char=True,
            use_word_breaks=False,
            char_weights={3: 0.5, 4: 0.5},
            wli_weights={},
            impl=ScorerImpl.NUMPY,
        )
        seed_plan = SeedPlan(
            n_starts=SEED_STARTS,
            refine_steps=SEED_REFINE_STEPS,
            temp_start=SEED_TEMP_START,
            temp_end=SEED_TEMP_END,
        )
        seed_keys = generate_seed_keys_periodic_columnar(
            ct_idx,
            period=PERIOD,
            columns=COLUMNS,
            order=ORDER,
            direction=encoding_dir,
            seed=TUTORIAL_SEED,
            scoring_cfg=seed_cfg,
            n_keys=SEED_KEYS,
            plan=seed_plan,
            refine=True,
        )
        seed_scores = [score_key_char34(k) for k in seed_keys]
        seed_scores_sorted = sorted(seed_scores, reverse=True)
        print(f"Seed pool: {len(seed_keys)} keys")
        print(
            "Seed score summary (char34): "
            f"max={seed_scores_sorted[0]:.6f} "
            f"median={float(np.median(seed_scores)):.6f} "
            f"(oracle={oracle_char34:.6f}, gap={oracle_char34 - seed_scores_sorted[0]:.6f})"
        )

    scorer_stage1 = dict(
        objective="pct.logp.win10",
        include_char=True,
        use_word_breaks=False,
        char_weights={3: 0.5, 4: 0.5},
        wli_weights={},
        encoding_dir=encoding_dir,
    )
    stop1 = oracle_stop_score(pt_idx, wli, scorer_stage1, device="cpu", encoding_dir=encoding_dir, margin=0.02, min_score=0.45, fallback=0.50)
    print_stop_summary("PeriodicColumnar simple P7 (Stage 1: char-only)", stop1)

    solver1 = SolverSpec.kaeding(
        steps=STAGE1_STEPS,
        restarts=STAGE1_RESTARTS,
        inner_batch=STAGE1_INNER_BATCH,
        slip_every=STAGE1_SLIP_EVERY,
        slip_blocks=STAGE1_SLIP_BLOCKS,
        col_every=STAGE1_COL_EVERY,
        col_batch=STAGE1_COL_BATCH,
        block_schedule="round_robin",
        stop_score=stop1.stop_score,
        progress_pct=2,
        print_progress=True,
        progress_preview_chars=120,
        seed=TUTORIAL_SEED,
        slip_policy="stall",
        stall_rounds=STAGE1_STALL_ROUNDS,
        stall_slip_limit=STAGE1_STALL_SLIP_LIMIT,
        slip_swaps=STAGE1_SLIP_SWAPS,
        stall_stop_on_limit=False,
    )
    stage1 = run(
        text=ct_idx_list,
        cipher=cipher_spec,
        key=key_spec,
        solver=solver1,
        scorer_params=scorer_stage1,
        wli_data=wli,
        encoding_dir=encoding_dir,
        telemetry_on=True,
        return_solver_report=True,
        **({} if seed_keys is None else {"initial_keys": seed_keys}),
    )
    print(f"[Stage 1] best_score={float(stage1.solution.score):.6f}")

    best_key1 = getattr(stage1.solution, "key_idx", None)
    warm_keys = []
    if best_key1 is not None:
        warm_keys.append(list(best_key1))
    if seed_keys:
        warm_keys.extend(seed_keys[: min(48, len(seed_keys))])

    scorer_stage2 = dict(
        objective="pct.logp.win10",
        include_char=True,
        use_word_breaks=True,
        char_weights={3: 0.3, 4: 0.7},
        wli_weights={3: 0.4, 4: 0.6},
        encoding_dir=encoding_dir,
    )
    display_scorer_params = {
        "objective": "pct.logp.win10",
        "include_char": True,
        "use_word_breaks": True,
        "encoding_dir": encoding_dir.value,
        "char_order_3_weight": 0.3,
        "char_order_4_weight": 0.7,
        "wli_order_3_weight": 0.4,
        "wli_order_4_weight": 0.6,
    }
    stop2 = oracle_stop_score(pt_idx, wli, scorer_stage2, device="cpu", encoding_dir=encoding_dir, margin=0.02, min_score=0.50, fallback=0.55)
    print_stop_summary("PeriodicColumnar simple P7 (Stage 2: full scorer)", stop2)

    solver2 = SolverSpec.kaeding(
        steps=STAGE2_STEPS,
        restarts=STAGE2_RESTARTS,
        inner_batch=STAGE2_INNER_BATCH,
        slip_every=STAGE2_SLIP_EVERY,
        slip_blocks=STAGE2_SLIP_BLOCKS,
        col_every=STAGE2_COL_EVERY,
        col_batch=STAGE2_COL_BATCH,
        block_schedule="round_robin",
        stop_score=stop2.stop_score,
        progress_pct=2,
        print_progress=True,
        progress_preview_chars=120,
        seed=TUTORIAL_SEED,
        slip_policy="stall",
        stall_rounds=STAGE2_STALL_ROUNDS,
        stall_slip_limit=STAGE2_STALL_SLIP_LIMIT,
        slip_swaps=STAGE2_SLIP_SWAPS,
        stall_stop_on_limit=False,
    )
    result = run(
        text=ct_idx_list,
        cipher=cipher_spec,
        key=key_spec,
        solver=solver2,
        scorer_params=scorer_stage2,
        wli_data=wli,
        encoding_dir=encoding_dir,
        telemetry_on=True,
        return_solver_report=True,
        **({} if not warm_keys else {"initial_keys": warm_keys}),
    )

    ratio = _match_ratio(result.solution, pt_idx)
    recovered = getattr(result.solution, "plaintext_rune", "") or getattr(result.solution, "plaintext_str", "")
    print("Recovered preview:", _preview(str(recovered)))
    if ratio < 0.999:
        raise RuntimeError(f"Solve failed: match_ratio={ratio:.4f}")

    display_spec = RunSpec(
        problem_input=NormalizedInput(ct_idx=ct_idx_list, wli=wli),
        cipher=cipher_spec,
        key=key_spec,
        solver=solver2,
        scorer="rune",
        scorer_params=display_scorer_params,
        encoding_dir=encoding_dir,
        telemetry_on=True,
    )
    pretty.print_summary_spacer()
    print_rdp_result(
        result,
        spec=display_spec,
        reference_idx=pt_idx,
        tutorial_entry={
            "path": "Tutorial_PeriodicColumnar_Simple_P7_ColThenSub.py",
            "title": "Periodic columnar simple P7 col-then-sub pretty-print variant",
            "gate": "optional_lm3_pretty_print",
            "acceptance_kind": "exact",
            "min_match_ratio": MIN_MATCH_RATIO,
            "uses_oracle_stop_score": True,
        },
    )
    print(f"True key length: {int(len(true_key))}")


if __name__ == "__main__":
    main()
