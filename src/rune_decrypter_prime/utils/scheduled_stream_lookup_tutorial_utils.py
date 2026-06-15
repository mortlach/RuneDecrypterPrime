from __future__ import annotations

from typing import Literal, Sequence

import numpy as np

from rune_decrypter_prime.api import Direction, KeySpec, SolverSpec, by_name, cipher_instance, run
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext_english_string
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils.tutorial_benchmark import TutorialRunKind, TutorialStopPolicy
from rune_decrypter_prime.utils.tutorial_reference import TutorialReference
from rune_decrypter_prime.utils.tutorial_report import print_tutorial_run_report
from rune_decrypter_prime.utils.tutorial_session_report import print_tutorial_session_report
from rune_decrypter_prime.utils.tutorial_utils import oracle_stop_score, print_stop_summary


ALPHABET_SIZE = 29
APP_VERSION = "tutorial-scheduled-stream-lookup-1.0"
TUTORIAL_SEED = 12345


def tutorial_plaintext(max_symbols: int = 520) -> str:
    return plaintext_english_string[:max_symbols]


def key_period13() -> list[int]:
    return [3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5, 8, 9]


def key_period31() -> list[int]:
    # Gauge choice for additive P13+P31 examples: first P31 entry is zero.
    return [0] + [((7 * i + 11) % ALPHABET_SIZE) for i in range(1, 31)]


def sample_sequence(length: int = 64) -> list[int]:
    return [((5 * i + 7) % ALPHABET_SIZE) for i in range(length)]


def concat_keys(*parts: Sequence[int]) -> list[int]:
    out: list[int] = []
    for part in parts:
        out.extend(int(v) for v in part)
    return out


def mask_from_segments(length: int, segments: Sequence[tuple[str, int, int | None]]) -> list[int]:
    """Readable A/B/AB segments -> integer mask."""
    labels = {"NONE": 0, "OFF": 0, "A": 1, "B": 2, "AB": 3, "A+B": 3, "B+A": 3}
    mask: list[int | None] = [None] * int(length)
    for label, start, end in segments:
        key = str(label).strip().upper().replace(" ", "")
        if key not in labels:
            raise ValueError("segment label must be A, B, AB, or NONE")
        stop = length if end is None else int(end)
        for i in range(int(start), stop):
            if not 0 <= i < length:
                raise ValueError(f"segment index out of range: {i}")
            if mask[i] is not None:
                raise ValueError(f"overlapping segment at index {i}")
            mask[i] = labels[key]
    if any(v is None for v in mask):
        raise ValueError("mask does not cover every plaintext position")
    return [int(v) for v in mask]


def encode_plaintext(direction: Direction = Direction.RTL):
    pt_idx, wli, pt_runes = Runeglish.encode_english_to_runes(
        tutorial_plaintext(),
        direction=direction.value,
    )
    return [int(v) for v in pt_idx], wli, pt_runes


def default_scorer_params(direction: Direction) -> dict:
    return dict(
        objective="pct.logp.win10",
        include_char=True,
        use_word_breaks=True,
        char_weights={2: 0.3},
        wli_weights={2: 0.7},
        encoding_dir=direction,
    )


def make_seeded_smoke_solver(
    pt_idx: Sequence[int],
    wli,
    scorer_params: dict,
    direction: Direction,
    *,
    label: str,
) -> SolverSpec:
    """Seeded pipeline-smoke solver. This is not ciphertext-only solving."""
    stop = oracle_stop_score(
        pt_idx,
        wli,
        scorer_params,
        device="cpu",
        encoding_dir=direction,
        margin=0.02,
        min_score=0.50,
        fallback=0.54,
    )
    print_stop_summary(label, stop)
    return SolverSpec.beam(
        beam_width=24,
        stop_score=stop.stop_score,
        plateau_rounds=6,
        plateau_min_delta=1e-4,
        max_children_per_parent=16,
        verbose=True,
        progress_pct=5,
        print_progress=True,
        seed=TUTORIAL_SEED,
    )


def make_real_solve_solver(
    *,
    stop_score: float = 0.56,
    beam_width: int = 72,
    plateau_rounds: int = 12,
    max_children_per_parent: int = 29,
    seed: int = 2026,
) -> SolverSpec:
    """Real key-recovery tutorial solver.

    Does not receive the true key as an initial key. The stop score is a fixed
    tutorial threshold for the short Alice sample used here.
    """
    print(f"[real solve] fixed stop_score={stop_score:.6f}; true key is not supplied")
    return SolverSpec.beam(
        beam_width=int(beam_width),
        stop_score=float(stop_score),
        plateau_rounds=int(plateau_rounds),
        plateau_min_delta=1e-4,
        max_children_per_parent=int(max_children_per_parent),
        verbose=True,
        progress_pct=5,
        print_progress=True,
        seed=int(seed),
    )


def build_ciphertext(
    *,
    cipher_name: str,
    cipher_kwargs: dict,
    key_values: Sequence[int],
    expected_key_len: int,
    direction: Direction,
):
    pt_idx, wli, pt_runes = encode_plaintext(direction)
    pt_arr = np.asarray(pt_idx, dtype=int)

    cipher_spec, default_key = by_name.cipher_with_key(cipher_name, default_key=True, **cipher_kwargs)
    key_spec = default_key if default_key is not None else KeySpec.repeat(len=expected_key_len)

    actual_key_len = int(key_spec.params.get("len", 0))
    if actual_key_len != expected_key_len:
        raise AssertionError(f"expected key length {expected_key_len}, got {key_spec.params}")

    cipher_obj = cipher_instance(cipher_spec)
    key_arr = np.asarray(list(key_values), dtype=int)
    ct_idx = cipher_obj.encrypt_single(plaintext=pt_arr, key=key_arr)
    ct_idx_list = [int(v) for v in ct_idx]
    ct_runes = Runeglish.to_rune(ct_idx_list, wli)
    return cipher_spec, key_spec, pt_idx, wli, pt_runes, ct_idx_list, ct_runes, key_arr, cipher_obj


def _as_int_list(x) -> list[int] | None:
    if isinstance(x, (list, tuple, np.ndarray)):
        return [int(v) for v in x]
    return None


def _split_run_result(result):
    """Return ``(solution, solver_report)`` for either Solution or RunResult."""
    return getattr(result, "solution", result), getattr(result, "solver_report", None)


def two_period_additive_equivalent(
    found: Sequence[int] | None,
    expected: Sequence[int],
    *,
    period_a: int,
    period_b: int,
    alphabet_size: int = ALPHABET_SIZE,
) -> bool:
    """Check additive overlay gauge equivalence.

    For pure additive overlay, A+c and B-c gives the same combined stream.
    This checks equivalence rather than requiring the exact arbitrary split.
    """
    if found is None:
        return False
    found_l = [int(v) % alphabet_size for v in found]
    expected_l = [int(v) % alphabet_size for v in expected]
    if len(found_l) != period_a + period_b or len(expected_l) != period_a + period_b:
        return False

    fa, fb = found_l[:period_a], found_l[period_a:]
    ea, eb = expected_l[:period_a], expected_l[period_a:]
    shift = (fa[0] - ea[0]) % alphabet_size
    if any(fa[i] != (ea[i] + shift) % alphabet_size for i in range(period_a)):
        return False
    if any(fb[i] != (eb[i] - shift) % alphabet_size for i in range(period_b)):
        return False
    return True


def run_seeded_pipeline_smoke(
    *,
    title: str,
    cipher_name: str,
    cipher_kwargs: dict,
    key_values: Sequence[int],
    expected_key_len: int,
    direction: Direction = Direction.RTL,
    print_report: bool = False,
) -> None:
    """Known-key seeded pipeline smoke check. Belongs in tests, not tutorials."""
    print("\nMODE: seeded pipeline smoke test")
    print("ASSUMES: cipher config, key length, and true key as initial seed")
    print("PROVES : API/cipher plumbing and roundtrip correctness\n")

    cipher_spec, key_spec, pt_idx, wli, pt_runes, ct_idx_list, ct_runes, key_arr, cipher_obj = build_ciphertext(
        cipher_name=cipher_name,
        cipher_kwargs=cipher_kwargs,
        key_values=key_values,
        expected_key_len=expected_key_len,
        direction=direction,
    )

    decoded = cipher_obj.decrypt_single(ciphertext=np.asarray(ct_idx_list, dtype=int), key=key_arr)
    direct_ok = [int(v) for v in decoded] == pt_idx
    print(f"{title}: direct known-key decrypt {'PASS/OK' if direct_ok else 'FAIL'}")
    if not direct_ok:
        raise AssertionError("known-key decrypt did not reproduce plaintext")

    scorer_params = default_scorer_params(direction)
    solver = make_seeded_smoke_solver(pt_idx, wli, scorer_params, direction, label=title)

    result = run(
        text=ct_runes,
        cipher=cipher_spec,
        key=key_spec,
        solver=solver,
        device="cpu",
        scorer="rune",
        scorer_params=scorer_params,
        wli_data=wli,
        encoding_dir=direction,
        telemetry_on=True,
        initial_keys=[list(key_values)],
        return_solver_report=bool(print_report),
    )
    solution, solver_report = _split_run_result(result)

    recovered = [int(v) for v in getattr(solution, "plaintext_idx", [])]
    match_ok = recovered[: len(pt_idx)] == pt_idx if recovered else False
    if not match_ok:
        raise AssertionError("seeded pipeline smoke did not recover reference plaintext")

    found_key_list = _as_int_list(getattr(solution, "key", None))
    if found_key_list != [int(v) for v in key_values]:
        raise AssertionError("seeded pipeline smoke did not preserve/recover expected key")

    if print_report:
        print_tutorial_run_report(
            title=title,
            cipher="scheduled_stream_lookup",
            solution=solution,
            solver_report=solver_report,
            match_ok=match_ok,
            app_version=APP_VERSION,
            key_idx=list(key_values),
            key_len=expected_key_len,
            ct_idx=ct_idx_list,
            ct_rune=ct_runes,
            pt_rune_ref=pt_runes,
            pt_idx_ref=pt_idx,
        )


def run_real_key_recovery_demo(
    *,
    title: str,
    cipher_name: str,
    cipher_kwargs: dict,
    key_values: Sequence[int],
    expected_key_len: int,
    stop_score: float = 0.56,
    beam_width: int = 72,
    plateau_rounds: int = 12,
    max_children_per_parent: int = 29,
    key_check: Literal["exact", "two_period_additive_equivalent"] = "exact",
    period_a: int | None = None,
    period_b: int | None = None,
    direction: Direction = Direction.RTL,
) -> None:
    """Real key-recovery tutorial: true key is used to encrypt, not supplied to solver."""
    print("\nMODE: real key-recovery tutorial")
    print("ASSUMES: cipher family, user-supplied schedule/operation/streams/periods/key length")
    print("OPTIMIZES: periodic key values only")
    print("DOES NOT SUPPLY: true key as initial_keys")
    print("GOAL: recover the periodic key, or an equivalent key where the cipher has gauge freedom\n")

    cipher_spec, key_spec, pt_idx, wli, pt_runes, ct_idx_list, ct_runes, _key_arr, _cipher_obj = build_ciphertext(
        cipher_name=cipher_name,
        cipher_kwargs=cipher_kwargs,
        key_values=key_values,
        expected_key_len=expected_key_len,
        direction=direction,
    )

    scorer_params = default_scorer_params(direction)
    solver = make_real_solve_solver(
        stop_score=stop_score,
        beam_width=beam_width,
        plateau_rounds=plateau_rounds,
        max_children_per_parent=max_children_per_parent,
    )

    result = run(
        text=ct_runes,
        cipher=cipher_spec,
        key=key_spec,
        solver=solver,
        device="cpu",
        scorer="rune",
        scorer_params=scorer_params,
        wli_data=wli,
        encoding_dir=direction,
        telemetry_on=True,
        initial_keys=None,
        return_solver_report=True,
    )
    solution, solver_report = _split_run_result(result)

    recovered = [int(v) for v in getattr(solution, "plaintext_idx", [])]
    match_ok = recovered[: len(pt_idx)] == pt_idx if recovered else False

    found_key_list = _as_int_list(getattr(solution, "key", None))
    expected_key_list = [int(v) for v in key_values]

    exact_ok = found_key_list == expected_key_list
    if key_check == "exact":
        key_ok = exact_ok
        key_check_label = "exact"
    elif key_check == "two_period_additive_equivalent":
        if period_a is None or period_b is None:
            raise ValueError("two_period_additive_equivalent requires period_a and period_b")
        key_ok = two_period_additive_equivalent(
            found_key_list,
            expected_key_list,
            period_a=int(period_a),
            period_b=int(period_b),
        )
        key_check_label = "two-period additive equivalent"
    else:
        raise ValueError(f"unknown key_check={key_check!r}")

    print(f"Expected key : {expected_key_list}")
    print(f"Found key    : {found_key_list}")
    print(f"Key exact?   : {exact_ok}")
    print(f"Key check    : {key_check_label}")
    print(f"Key accepted?: {key_ok}")
    print(f"Plaintext OK?: {match_ok}")

    print_tutorial_session_report(
        title=title,
        cipher="scheduled_stream_lookup",
        solution=solution,
        solver_report=solver_report,
        reference=TutorialReference.key_and_plaintext(key_idx=expected_key_list, plaintext_idx=pt_idx),
        run_kind=TutorialRunKind.REAL_KEY_RECOVERY_BENCHMARK,
        stop_policy=TutorialStopPolicy(readable_match_ratio=0.85, target_match_ratio=0.99, stop_score=stop_score),
        match_ok=match_ok,
        app_version=APP_VERSION,
        key_idx=expected_key_list,
        key_len=expected_key_len,
        ct_idx=ct_idx_list,
        ct_rune=ct_runes,
        pt_rune_ref=pt_runes,
        pt_idx_ref=pt_idx,
    )

    if not match_ok:
        raise AssertionError("real solve did not recover the expected plaintext")
    if not key_ok:
        raise AssertionError("real solve did not recover an accepted key")
