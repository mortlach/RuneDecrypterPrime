# # # ============================================================
# # # rune_decrypter_prime/optimizers/hybrid_optimizer.py
# # # Hybrid orchestrator: Beam → GA → SA
# # # ============================================================
# -*- coding: utf-8 -*-
"""
Mono Substitution (29 runes) — HYBRID walkthrough (Beam → GA → SA)

What you’ll see
---------------
1) English → runes (single direction).
2) Random key → encrypt → ciphertext.
3) HYBRID optimiser runs: Beam warm-start (if available) → GA explore → SA polish.
4) We deliberately start from **noise** (no seeds) to show robustness.
5) A short, friendly report at the end.

You can tweak GA/SA knobs inside the Hybrid params.
"""
from __future__ import annotations
from typing import Tuple
import numpy as np

from rune_decrypter_prime.ui.api import by_name, cipher_instance, KeySpec, SolveSpec, run
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.tutorials.v1 import pretty
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext_english_string


def preview(s: str, n: int = 120) -> str:
    return s if len(s) <= n else s[:n] + "…"


def _invert_perm(pt_to_ct: np.ndarray) -> np.ndarray:
    inv = np.empty_like(pt_to_ct)
    inv[pt_to_ct] = np.arange(pt_to_ct.size, dtype=np.uint8)
    return inv


def _build_ciphertext(pt_en: str, *, direction: str = "rev", seed: int = 42):
    pt_idx, wli, _ = Runeglish.encode_english_to_runes(pt_en, direction=direction)
    rng = np.random.default_rng(seed)
    key_fwd = rng.permutation(29).astype(np.uint8)            # pt→ct
    ciph = cipher_instance(by_name.cipher("mono"))
    ct_idx = ciph.encrypt(plaintext=np.asarray(pt_idx, np.uint8), key=key_fwd)
    ct_runes = Runeglish.to_rune(ct_idx.tolist(), wli)
    key_inv = _invert_perm(key_fwd)                            # ct→pt
    return ct_runes, wli, key_fwd.tolist(), key_inv.tolist()


def main():
    direction = "rev"

    # 1) English → ciphertext
    pt_en = plaintext_english_string
    ct_runes, wli, _key_fwd, _key_inv = _build_ciphertext(pt_en, direction=direction, seed=42)

    # 2) Hybrid config (Beam → GA → SA), **start from noise**: no initial_keys here.
    #    NOTE: Hybrid expects nested dicts: ga={...}, sa={...}.
    hybrid = SolveSpec.hybrid(
        use_beam=True,
        beam_width=16,          # short beam so GA & SA get time
        ga=dict(                # GA explore (short)
            pop=120,
            gens=60,
            elite_frac=0.06,
            cx_frac=0.80,
            mut_prob=0.30,
            tournament_k=3,
            plateau_gens=12,
            stop_score=0.52,  # early success exit
        ),
        sa=dict(                # SA polish (short)
            iters=6000,
            T0=0.7,
            Tmin=1e-3,
            auto_cooling=True,
            cooling=0.998,
            elitism=True,       # keep best-so-far during SA
            reseed_interval=2000,
            rescue_drop_abs=0.02,
            rescue_drop_ratio=0.5,
            local_improve_on_accept=True,
            stop_score=0.52,  # early success exit
        ),
        # Common
        seed=123,
        verbose=True,
        log_interval=10,
        stop_score=0.52,
    )

    # 3) Run solver (no seeds passed → genuine noise start)
    sol = run.solve(
        text=ct_runes,
        cipher=by_name.cipher("mono"),
        key=KeySpec.permutation(len=29),
        solve=hybrid,
        device="cpu",
        scorer="rune",
        scorer_params=dict(
            objective="pct.logp.win10",
            char_weights={2: 0.3},
            wli_weights={2: 0.7},
            include_char=True,
            use_word_breaks=True,
            direction=direction,
        ),
        wli_data=wli,
        # initial_keys=None,
    )

    # 4) Report
    print("─" * 72)
    print("Mono Substitution — HYBRID (Beam → GA → SA)")
    print("Recovered plaintext:", preview(sol.plaintext))
    print("Score:", round(sol.score, 6))

    pretty.print_run_report(
        title="mono-hybrid",
        cipher="mono",
        key_idx=None,
        ct_idx=Runeglish.rune_to_pos(ct_runes.replace(" ","")),
        ct_rune=ct_runes,
        solution=sol,
        match_ok=None,
        app_version="tutorial-1.3",
        key_len=None,
        wli=wli,
        pt_rune_ref=pt_en,
        pt_idx_ref="",
    )


if __name__ == "__main__":
    main()


# # -*- coding: utf-8 -*-
# """
# Mono Substitution (29 runes) — HYBRID walkthrough (Beam → GA → SA)
#
# What you’ll see
# ---------------
# 1) English → runes (single direction).
# 2) Random key → encrypt → ciphertext.
# 3) HYBRID optimiser runs: Beam warm-start (if available) → GA explore → SA polish.
# 4) We deliberately **start from noise** (no seeds) to show robustness.
# 5) We finish with a short, friendly report.
#
# You can tweak GA/SA knobs through the Hybrid params.
# """
# from __future__ import annotations
# from typing import Tuple
# import numpy as np
#
# from rune_decrypter_prime.ui.api import by_name, cipher_instance, KeySpec, SolveSpec, run
# from rune_decrypter_prime.utils.runeglish import Runeglish
# from rune_decrypter_prime.tutorials.v1 import pretty
# from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext_english_string
#
#
# def preview(s: str, n: int = 120) -> str:
#     return s if len(s) <= n else s[:n] + "…"
#
#
# def _invert_perm(pt_to_ct: np.ndarray) -> np.ndarray:
#     inv = np.empty_like(pt_to_ct)
#     inv[pt_to_ct] = np.arange(pt_to_ct.size, dtype=np.uint8)
#     return inv
#
#
# def _build_ciphertext(pt_en: str, *, direction: str = "rev", seed: int = 42):
#     pt_idx, wli, _ = Runeglish.encode_english_to_runes(pt_en, direction=direction)
#     rng = np.random.default_rng(seed)
#     key_fwd = rng.permutation(29).astype(np.uint8)            # pt→ct
#     ciph = cipher_instance(by_name.cipher("mono"))
#     ct_idx = ciph.encrypt(plaintext=np.asarray(pt_idx, np.uint8), key=key_fwd)
#     ct_runes = Runeglish.to_rune(ct_idx.tolist(), wli)
#     key_inv = _invert_perm(key_fwd)                            # ct→pt
#     return ct_runes, wli, key_fwd.tolist(), key_inv.tolist()
#
#
# def main():
#     direction = "rev"
#
#     # 1) English → ciphertext
#     pt_en = plaintext_english_string
#     ct_runes, wli, _key_fwd, _key_inv = _build_ciphertext(pt_en, direction=direction, seed=42)
#
#     # 2) Hybrid config (no initial seeds -> starts from noise)
#     # 2) Hybrid config (Beam → GA → SA). We do NOT provide seeds here.
#     hybrid = SolveSpec.hybrid(
#         params=dict(
#             # NOTE: no initial_keys -> starts from noise
#
#             # Beam (if keyops supports partial scoring)
#             use_beam=True,
#             beam_width=64,
#
#             # GA knobs
#             pop_size=160,
#             generations=250,
#             elite_frac=0.06,
#             cx_frac=0.80,
#             mut_prob=0.30,
#             tournament_k=3,
#             plateau_gens=30,
#
#             # SA knobs
#             sa_init_temp=0.6,
#             sa_min_temp=1e-3,
#             sa_cooling=0.998,
#             sa_auto_cooling=True,
#             sa_iters=25000,
#
#             # Common
#             seed=123,  # for repeatable runs
#             verbose=True,
#             log_interval=20,
#             stop_score= 0.52
#         )
#     )
#
#     # 3) Run solver
#     sol = run.solve(
#         text=ct_runes,
#         cipher=by_name.cipher("mono"),
#         key=KeySpec.permutation(len=29),
#         solve=hybrid,
#         device="cpu",
#         scorer="rune",
#         scorer_params=dict(
#             objective="pct.logp.win10",
#             char_weights={2: 0.3},
#             wli_weights={2: 0.7},
#             include_char=True,
#             use_word_breaks=True,
#             direction=direction,
#         ),
#         wli_data=wli,
#     )
#
#     # 4) Report
#     print("─" * 72)
#     print("Mono Substitution — HYBRID (Beam → GA → SA)")
#     print("Recovered plaintext:", preview(sol.plaintext))
#     print("Score:", round(sol.score, 6))
#
#     pretty.print_run_report(
#         title="mono-hybrid",
#         cipher="mono",
#         key_idx=None,
#         ct_idx=[Runeglish.rune_to_pos(c) for c in ct_runes],
#         ct_rune=ct_runes,
#         solution=sol,
#         match_ok=None,
#         app_version="tutorial-1.2",
#         key_len=None,
#         wli=wli,
#         pt_rune_ref=pt_en,
#         pt_idx_ref="",
#     )
#
# if __name__ == "__main__":
#     main()
#
#
# # from __future__ import annotations
# # import time
# # import numpy as np
# #
# # from rune_decrypter_prime.optimizers.optimizer_base import OptimizerBase
# # from rune_decrypter_prime.optimizers.ga_optimizer import GAOptimizer
# # from rune_decrypter_prime.optimizers.sa_optimizer import SAOptimizer
# # from rune_decrypter_prime.optimizers.beam_optimizer import BeamSearchOptimizer
# # from rune_decrypter_prime.core.config import OptimizerConfig, Solution
# # from rune_decrypter_prime.core.telemetry_helpers import (
# #     TelemetrySpan, attach_telemetry_to_meta
# # )
# # from rune_decrypter_prime.utils.runeglish import Runeglish
# #
# #
# # class HybridOptimizer(OptimizerBase):
# #     """
# #     Hybrid pipeline (pure orchestration):
# #       (optional) Beam warm start → GA exploration → SA polish
# #
# #     No custom operators live here; we instantiate and call the real optimisers.
# #
# #     Params (OptimizerConfig.params)
# #     --------------------------------
# #     use_beam: bool = True
# #     beam_width: int = 64
# #     beam_stop_score: Optional[float] = None
# #
# #     # GA passthrough (same names as GAOptimizer)
# #     pop_size: int = 128
# #     generations: int = 150
# #     elite_frac: float = 0.05
# #     cx_frac: float = 0.8
# #     mut_prob: float = 0.25
# #     tournament_k: int = 3
# #     plateau_gens: int = 0
# #
# #     # SA passthrough (same names as SAOptimizer)
# #     sa_init_temp: float = 0.5
# #     sa_min_temp: float = 1e-3
# #     sa_cooling: float = 0.998
# #     sa_auto_cooling: bool = True
# #     sa_iters: int = 2000
# #
# #     # Common
# #     seed_keys: Optional[List[List[int]]] = None
# #     initial_keys: Optional[List[List[int]]] = None
# #     test_key: Optional[List[int]] = None
# #     stop_score: Optional[float] = None
# #     verbose: bool = False
# #     seed: Optional[int] = None
# #     """
# #
# #     # Optional engine hooks (kept for API symmetry)
# #     def set_interrupt_idx(self, idx): pass
# #     def set_interrupt_search_space(self, pool, max_count): pass
# #     def set_transposition_modes(self, modes): pass
# #
# #     def _decrypt_to_text(self, key_u8: np.ndarray) -> str:
# #         pt_idx = self.problem.cipher.decrypt(key=key_u8, ciphertext=self._ct)
# #         if isinstance(pt_idx, tuple):
# #             pt_idx = pt_idx[0]
# #         pt_idx = np.asarray(pt_idx, dtype=np.int64).ravel().tolist()
# #         return Runeglish.to_rune(pt_idx, self._wli)
# #
# #     def search(self) -> Solution:
# #         # Fast path
# #         fast = self._maybe_return_test_key_fastpath("hybrid")
# #         if fast is not None:
# #             return fast
# #
# #         seeds = [self.keyops.normalize(np.asarray(k, np.uint8))[:self.K] for k in self.seed_keys]
# #         params_for_span = {
# #             "use_beam": bool(self.get_param("use_beam", True)),
# #             "beam_width": int(self.get_param("beam_width", 64)),
# #             "K": int(self.K),
# #             "ga": {
# #                 "pop": int(self.get_param("pop_size", 128)),
# #                 "gens": int(self.get_param("generations", 150)),
# #                 "elite_frac": float(self.get_param("elite_frac", 0.05)),
# #                 "cx_frac": float(self.get_param("cx_frac", 0.8)),
# #                 "mut_prob": float(self.get_param("mut_prob", 0.25)),
# #             },
# #             "sa": {
# #                 "iters": int(self.get_param("sa_iters", 2000)),
# #                 "T0": float(self.get_param("sa_init_temp", 0.5)),
# #                 "Tmin": float(self.get_param("sa_min_temp", 1e-3)),
# #                 "cool": float(self.get_param("sa_cooling", 0.998)),
# #             },
# #         }
# #
# #         with TelemetrySpan(self.problem, "hybrid", params_for_span) as span:
# #             best_key = None
# #             best_score = -1e30
# #
# #             # Stage 1: Beam (optional)
# #             use_beam = bool(self.get_param("use_beam", True))
# #             can_beam = bool(getattr(getattr(self.keyops, "caps", None), "can_partial_score", False))
# #             if use_beam and can_beam:
# #                 t0 = time.perf_counter()
# #                 beam = BeamSearchOptimizer(problem=self.problem, opt_cfg=self.opt_cfg)
# #                 sol_b = beam.search()
# #                 dt = time.perf_counter() - t0
# #                 bkey = np.asarray(sol_b.key, np.uint8)
# #                 seeds.append(bkey)
# #                 best_key = bkey.copy()
# #                 best_score = float(sol_b.score)
# #                 span.progress(stage="beam", elapsed_sec=float(dt), best=float(best_score))
# #
# #                 if self.stop_score is not None and best_score >= self.stop_score:
# #                     span.end(best_score=float(best_score))
# #                     meta = {"optimizer": "hybrid", "stage": "beam", "interrupt_idx": []}
# #                     meta = attach_telemetry_to_meta(self.problem, meta)
# #                     return Solution(best_key.tolist(), self._decrypt_to_text(best_key), best_score, meta)
# #
# #             # Stage 2: GA (pass seeds via params to keep contracts)
# #             ga_params = dict(self.params)
# #             ga_params["initial_keys"] = [k.tolist() for k in seeds] if seeds else ga_params.get("initial_keys", [])
# #             ga_cfg = OptimizerConfig(name="ga", params=ga_params)
# #             t0 = time.perf_counter()
# #             ga = GAOptimizer(problem=self.problem, opt_cfg=ga_cfg)
# #             sol_g = ga.search()
# #             dt = time.perf_counter() - t0
# #             gkey = np.asarray(sol_g.key, np.uint8)
# #             gscore = float(sol_g.score)
# #             if gscore > best_score:
# #                 best_key, best_score = gkey.copy(), gscore
# #             span.progress(stage="ga", elapsed_sec=float(dt), best=float(best_score))
# #
# #             if self.stop_score is not None and best_score >= self.stop_score:
# #                 span.end(best_score=float(best_score))
# #                 meta = {"optimizer": "hybrid", "stage": "ga", "interrupt_idx": []}
# #                 meta = attach_telemetry_to_meta(self.problem, meta)
# #                 return Solution(best_key.tolist(), self._decrypt_to_text(best_key), best_score, meta)
# #
# #             # Stage 3: SA polish (seeded with GA best)
# #             sa_params = dict(self.params)
# #             sa_params["initial_keys"] = [best_key.tolist()]
# #             sa_cfg = OptimizerConfig(name="sa", params=sa_params)
# #             t0 = time.perf_counter()
# #             sa = SAOptimizer(problem=self.problem, opt_cfg=sa_cfg)
# #             sol_s = sa.search()
# #             dt = time.perf_counter() - t0
# #             skey = np.asarray(sol_s.key, np.uint8)
# #             sscore = float(sol_s.score)
# #             if sscore > best_score:
# #                 best_key, best_score = skey.copy(), sscore
# #             span.progress(stage="sa", elapsed_sec=float(dt), best=float(best_score))
# #
# #             span.end(best_score=float(best_score))
# #
# #         pt_str = self._decrypt_to_text(best_key)
# #         meta = {"optimizer": "hybrid", "interrupt_idx": []}
# #         meta = attach_telemetry_to_meta(self.problem, meta)
# #         return Solution(best_key.tolist(), pt_str, float(best_score), meta)
