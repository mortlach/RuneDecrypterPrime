from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, Mapping


def persist_run_config_with_locks(
    *,
    run_config: Dict[str, Any],
    run_config_path: Path,
    build_non_scoring_lock_payload_fn: Callable[[], Dict[str, Any]],
    build_scoring_lock_payload_fn: Callable[[], Dict[str, Any]],
    hash_payload_fn: Callable[[Dict[str, Any]], str],
    write_json_fn: Callable[[Path, Any], None],
    git_short_fn: Callable[[], str],
    git_commit_fn: Callable[[], str],
    git_dirty_fn: Callable[[], bool],
    sha256_file_fn: Callable[[Path], str],
) -> Mapping[str, str]:
    write_json_fn(run_config_path, run_config)
    non_scoring_lock_hash = hash_payload_fn(build_non_scoring_lock_payload_fn())
    scoring_lock_hash = hash_payload_fn(build_scoring_lock_payload_fn())
    run_config_payload_hash = hash_payload_fn(run_config)
    run_config["lock_hashes"] = dict(
        non_scoring=str(non_scoring_lock_hash),
        scoring=str(scoring_lock_hash),
        run_config_payload=str(run_config_payload_hash),
    )
    run_config["git"] = dict(
        short=str(git_short_fn()),
        commit=str(git_commit_fn()),
        dirty=int(1 if bool(git_dirty_fn()) else 0),
    )
    write_json_fn(run_config_path, run_config)
    run_config_hash = sha256_file_fn(run_config_path)
    return dict(
        non_scoring_lock_hash=str(non_scoring_lock_hash),
        scoring_lock_hash=str(scoring_lock_hash),
        run_config_payload_hash=str(run_config_payload_hash),
        run_config_hash=str(run_config_hash),
    )
