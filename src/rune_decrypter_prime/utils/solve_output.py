from __future__ import annotations

import dataclasses
import json
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path

from rdp.data.runeglish import Runeglish


def configure_utf8_stdio() -> None:
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


def as_int_list(values: object) -> list[int]:
    if values is None:
        return []
    if hasattr(values, "tolist"):
        values = values.tolist()
    return [int(value) for value in list(values)]


def zero_positions(values: Sequence[int]) -> list[int]:
    return [index for index, value in enumerate(values) if int(value) == 0]


def match_ratio(candidate: Sequence[int], reference: Sequence[int]) -> float:
    if not candidate and not reference:
        return 1.0
    total = max(len(candidate), len(reference))
    if total == 0:
        return 0.0
    matches = sum(1 for left, right in zip(candidate, reference) if int(left) == int(right))
    return matches / total


def render_plaintext(
    plaintext_idx: Sequence[int],
    wli: Sequence[Sequence[int]],
    *,
    direction: str | object = "ltr",
) -> tuple[str, str]:
    if not plaintext_idx:
        return "", ""
    idx = [int(value) for value in plaintext_idx]
    return Runeglish.to_rune_latin(idx, wli, direction=direction), Runeglish.to_rune(idx, wli)


def page_value(metadata: Mapping[str, object], canonical: str, legacy: str | None = None) -> object:
    if canonical in metadata:
        return metadata[canonical]
    if legacy is not None and legacy in metadata:
        return metadata[legacy]
    return None


def print_kv(key: str, value: object) -> None:
    if isinstance(value, (dict, list, tuple)):
        print(f"{key}: {json.dumps(json_value(value), ensure_ascii=False)}")
    else:
        print(f"{key}: {value}")


def print_block(
    block_name: str,
    fields: Mapping[str, object] | Sequence[tuple[str, object]],
) -> None:
    print(f"\n{block_name}_BEGIN")
    items = fields.items() if isinstance(fields, Mapping) else fields
    for key, value in items:
        print_kv(str(key), value)
    print(f"{block_name}_END")


def print_final_result(
    *,
    block_name: str,
    source_label: str,
    resolved_source_label: str,
    main_page_start: object,
    main_page_end: object,
    ciphertext_length: int,
    wli_length: int,
    recipe: str,
    cipher_family: str,
    method: str,
    key_or_params: object | None,
    match_ratio: float | str | None,
    status: str,
    acceptance_rule: str | None,
    plaintext_latin: str,
    plaintext_runes: str,
    extra_fields: Mapping[str, object] | None = None,
) -> None:
    ratio = f"{match_ratio:.3f}" if isinstance(match_ratio, float) else match_ratio
    fields: list[tuple[str, object]] = [
        ("source_label", source_label),
        ("resolved_source_label", resolved_source_label),
        ("main_page_start", main_page_start),
        ("main_page_end", main_page_end),
        ("ciphertext_length", ciphertext_length),
        ("wli_length", wli_length),
        ("recipe", recipe),
        ("cipher_family", cipher_family),
        ("method", method),
    ]
    if key_or_params is not None:
        fields.append(("key_or_params", key_or_params))
    if extra_fields:
        fields.extend((str(key), value) for key, value in extra_fields.items())
    fields.extend(
        [
            ("match_ratio", ratio),
            ("status", status),
        ]
    )
    if acceptance_rule is not None:
        fields.append(("acceptance_rule", acceptance_rule))

    print(f"\n{block_name}_BEGIN")
    for key, value in fields:
        print_kv(key, value)
    print("plaintext_latin:")
    print(plaintext_latin)
    print("plaintext_runes:")
    print(plaintext_runes)
    print(f"{block_name}_END")


def _get_nested(obj: object, *names: str, default: object = None) -> object:
    current = obj
    for name in names:
        if current is None:
            return default
        if isinstance(current, Mapping):
            current = current.get(name, default)
        else:
            current = getattr(current, name, default)
    return current


def json_value(value: object, *, max_list: int = 40) -> object:
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    if hasattr(value, "shape") and hasattr(value, "tolist"):
        shape = [int(part) for part in getattr(value, "shape", ())]
        flat = value.reshape(-1).tolist() if hasattr(value, "reshape") else value.tolist()
        preview = [json_value(item, max_list=max_list) for item in list(flat)[:max_list]]
        return {"type": type(value).__name__, "shape": shape, "preview": preview}
    if dataclasses.is_dataclass(value):
        return json_value(dataclasses.asdict(value), max_list=max_list)
    if isinstance(value, Mapping):
        return {str(key): json_value(val, max_list=max_list) for key, val in value.items()}
    if isinstance(value, (list, tuple, set)):
        items = list(value)
        if len(items) > max_list:
            return {
                "type": type(value).__name__,
                "length": len(items),
                "preview": [json_value(item, max_list=max_list) for item in items[:max_list]],
            }
        return [json_value(item, max_list=max_list) for item in items]
    if hasattr(value, "to_json_dict"):
        return json_value(value.to_json_dict(), max_list=max_list)
    if hasattr(value, "__dict__"):
        return json_value(vars(value), max_list=max_list)
    return repr(value)


def safe_public_dict(obj: object) -> dict[str, object]:
    if obj is None:
        return {}
    if isinstance(obj, Mapping):
        source = obj
    else:
        source = vars(obj) if hasattr(obj, "__dict__") else {}
    out: dict[str, object] = {}
    for key, value in source.items():
        key_str = str(key)
        if key_str.startswith("_"):
            continue
        out[key_str] = json_value(value)
    return out


def write_json_evidence(path: Path, evidence: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(json_value(dict(evidence)), indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_latest_evidence(
    evidence_dir: Path,
    evidence: Mapping[str, object],
    *,
    timestamped: bool = True,
) -> tuple[Path, Path | None]:
    latest = evidence_dir / "latest_solve_evidence.json"
    write_json_evidence(latest, evidence)
    stamped: Path | None = None
    if timestamped:
        stamped = evidence_dir / f"solve_evidence_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        write_json_evidence(stamped, evidence)
    return latest, stamped


def collect_solver_attempt(
    *,
    result: object,
    solver_variant: str,
    scorer_variant: str,
    key_length: int,
    interruptor_pool: Sequence[int] | None = None,
    interruptor_count: int | None = None,
    reference_idx: Sequence[int] | None = None,
    ciphertext_length: int | None = None,
    wli: Sequence[Sequence[int]] | None = None,
    elapsed_wall_time_s: float | None = None,
    acceptance_match_ratio: float = 1.0,
) -> dict[str, object]:
    solution = getattr(result, "solution", result)
    report = getattr(result, "solver_report", None)
    plaintext_idx = as_int_list(
        getattr(solution, "plaintext_idx", getattr(solution, "plaintext", []))
    )
    plaintext_latin = str(
        getattr(solution, "plaintext_latin", getattr(solution, "plaintext_text", "")) or ""
    )
    plaintext_runes = str(getattr(solution, "plaintext_rune", "") or "")
    if plaintext_idx and wli is not None and (not plaintext_latin or not plaintext_runes):
        plaintext_latin, plaintext_runes = render_plaintext(plaintext_idx, wli)

    key_values = as_int_list(getattr(solution, "key", []))
    found_key_core = key_values[:key_length]
    found_interruptors = [value for value in key_values[key_length:] if value >= 0]
    pool = list(interruptor_pool or [])
    found_interruptors_in_pool = all(value in pool for value in found_interruptors)
    ratio = match_ratio(plaintext_idx, reference_idx) if reference_idx is not None else None
    best_score = _get_nested(solution, "score", default=_get_nested(report, "best_score"))
    stop_reason = _get_nested(solution, "stop_reason", default=_get_nested(report, "stop_reason"))

    solved = True
    if ratio is not None:
        solved = solved and ratio >= acceptance_match_ratio
    if interruptor_count is not None:
        solved = solved and len(found_interruptors) == int(interruptor_count)
    if interruptor_pool is not None:
        solved = solved and found_interruptors_in_pool
    if ciphertext_length is not None:
        solved = solved and len(plaintext_idx) == int(ciphertext_length)

    return {
        "solver_variant": solver_variant,
        "scorer_variant": scorer_variant,
        "found_key_core": found_key_core,
        "found_interruptors": found_interruptors,
        "found_interrupter_count": len(found_interruptors),
        "found_interruptors_in_pool": found_interruptors_in_pool,
        "best_score": best_score,
        "stop_reason": stop_reason,
        "match_ratio": ratio,
        "plaintext_idx_length": len(plaintext_idx),
        "score_time_s": _get_nested(report, "score_time_s", default=_get_nested(solution, "score_time_s")),
        "decrypt_time_s": _get_nested(report, "decrypt_time_s", default=_get_nested(solution, "decrypt_time_s")),
        "tokens": _get_nested(report, "tokens_processed", default=_get_nested(solution, "tokens_processed")),
        "evals_or_candidates": _get_nested(report, "evals", default=_get_nested(solution, "evals")),
        "elapsed_wall_time_s": elapsed_wall_time_s,
        "status": "solved" if solved else "diagnostic_not_yet_solved",
        "plaintext_latin": plaintext_latin,
        "plaintext_runes": plaintext_runes,
    }
