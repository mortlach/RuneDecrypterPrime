from __future__ import annotations
from pathlib import Path
from rune_decrypter_prime.io.artifact_policy import (
    EXTERNAL_PATH,
    REDACTED_PATH_TEXT,
    artifact_json_value,
    artifact_path,
    portable_exception_message,
)


def test_artifact_path_preserves_relative_path_values(tmp_path: Path) -> None:
    assert (
        artifact_path(Path("artifacts/report.json"), root=tmp_path)
        == "artifacts/report.json"
    )


def test_artifact_path_converts_absolute_paths_under_root(tmp_path: Path) -> None:
    path = tmp_path / "artifacts" / "report.json"
    assert artifact_path(path, root=tmp_path) == "artifacts/report.json"


def test_artifact_path_converts_external_absolute_paths_to_marker(
    tmp_path: Path,
) -> None:
    path = tmp_path.parent / "outside.txt"
    assert artifact_path(path, root=tmp_path) == EXTERNAL_PATH


def test_artifact_json_value_recursively_converts_path_values(tmp_path: Path) -> None:
    root_local = tmp_path / "artifacts" / "report.json"
    payload = {
        "path": root_local,
        "nested": [Path("relative.txt"), tmp_path.parent / "outside.txt"],
    }
    assert artifact_json_value(payload, root=tmp_path) == {
        "path": "artifacts/report.json",
        "nested": ["relative.txt", EXTERNAL_PATH],
    }


def test_artifact_json_value_leaves_plain_strings_unchanged(tmp_path: Path) -> None:
    value = "C:\\Users\\name\\not-a-path-object.txt"
    assert artifact_json_value({"message": value}, root=tmp_path) == {"message": value}


def test_portable_exception_message_redacts_unix_absolute_paths() -> None:
    message, redacted = portable_exception_message(
        RuntimeError("cannot write /home/name/private/secret.txt")
    )
    assert message == f"cannot write {REDACTED_PATH_TEXT}"
    assert redacted is True


def test_portable_exception_message_redacts_quoted_unix_path_with_spaces() -> None:
    message, redacted = portable_exception_message(
        RuntimeError("cannot write '/home/name/My Project/secret.txt'")
    )
    assert message == f"cannot write '{REDACTED_PATH_TEXT}'"
    assert redacted is True


def test_portable_exception_message_redacts_windows_absolute_paths() -> None:
    message, redacted = portable_exception_message(
        RuntimeError("cannot write C:\\Users\\name\\private\\secret.txt")
    )
    assert message == f"cannot write {REDACTED_PATH_TEXT}"
    assert redacted is True


def test_portable_exception_message_redacts_quoted_windows_path_with_spaces() -> None:
    message, redacted = portable_exception_message(
        RuntimeError("cannot write 'C:\\Users\\Name\\My Project\\secret.txt'")
    )
    assert message == f"cannot write '{REDACTED_PATH_TEXT}'"
    assert redacted is True


def test_portable_exception_message_redacts_unc_paths() -> None:
    message, redacted = portable_exception_message(
        RuntimeError("cannot write \\\\server\\share\\private\\secret.txt")
    )
    assert message == f"cannot write {REDACTED_PATH_TEXT}"
    assert redacted is True


def test_portable_exception_message_redacts_quoted_unc_path_with_spaces() -> None:
    message, redacted = portable_exception_message(
        RuntimeError("cannot write '\\\\server\\share\\My Project\\secret.txt'")
    )
    assert message == f"cannot write '{REDACTED_PATH_TEXT}'"
    assert redacted is True


def test_portable_exception_message_truncates_long_messages() -> None:
    message, redacted = portable_exception_message(RuntimeError("x" * 300))
    assert len(message) == 240
    assert message.endswith("...")
    assert redacted is True
