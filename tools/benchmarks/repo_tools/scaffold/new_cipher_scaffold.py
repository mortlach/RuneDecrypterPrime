from __future__ import annotations

import argparse
from pathlib import Path


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return here.parents[4]


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a new cipher skeleton under src/rune_decrypter_prime/ciphers.")
    parser.add_argument("--name", default="my_cipher", help="Cipher module name in snake_case.")
    parser.add_argument("--class-name", default="MyCipher", help="Cipher class name.")
    args = parser.parse_args()

    target_dir = _repo_root() / "src" / "rune_decrypter_prime" / "ciphers"
    target_dir.mkdir(parents=True, exist_ok=True)
    out = target_dir / f"{args.name}.py"
    template = f"""
# Auto-generated skeleton; fill in encrypt/decrypt and key validation.
class {args.class_name}:
    def __init__(self, **kwargs):
        pass

    def encrypt(self, indices):
        return indices

    def decrypt(self, indices, key):
        return indices

    @staticmethod
    def validate_key(key):
        return True
"""
    out.write_text(template.strip() + "\n", encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
