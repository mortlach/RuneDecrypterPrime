from __future__ import annotations
from pathlib import Path
import pytest

pytestmark = pytest.mark.tier_a


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_manifest_in_includes_native_extension_sources() -> None:
    root = _repo_root()
    manifest_path = root / "MANIFEST.in"
    assert (
        manifest_path.is_file()
    ), "MANIFEST.in is required so sdist-based wheel builds include native C++ sources."
    text = manifest_path.read_text(encoding="utf-8")
    required_patterns = [
        "recursive-include src/rune_decrypter_prime/scoring/language_model *.cpp *.hpp *.h",
        "recursive-include src/rune_decrypter_prime/scoring/hamming *.cpp *.hpp *.h",
        "recursive-include src/rune_decrypter_prime/scoring/span_hamming *.cpp *.hpp *.h",
    ]
    missing = [pattern for pattern in required_patterns if pattern not in text]
    assert not missing, (
        "MANIFEST.in is missing native source include patterns:\n"
        + "\n".join((f"- {pattern}" for pattern in missing))
    )
