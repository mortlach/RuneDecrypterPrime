from __future__ import annotations
import contextlib
import hashlib
import importlib
import importlib.util
import json
import re
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = (PROJECT_ROOT / "src").resolve()
REQUIRED_MODULES = (
    "rune_decrypter_prime",
    "rdp",
    "rune_decrypter_prime.scoring.language_model._fastlm",
    "rune_decrypter_prime.scoring.hamming._hamming",
    "rune_decrypter_prime.scoring.span_hamming._span_hamming_fast",
)
BLOCKED_MODULES = (
    "rune_decrypter_prime.ciphers.dev",
    "rune_decrypter_prime.keyops.dev",
    "rune_decrypter_prime.data.liber_primus.old",
)
PUBLIC_API_ALLOWLIST = (
    PROJECT_ROOT / "v1_docs" / "reference" / "public_api_allowlist.md"
)


def _under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _assert_v1_public_contract() -> None:
    from rdp import api

    paths = {
        match.group(1)
        for line in PUBLIC_API_ALLOWLIST.read_text(encoding="utf-8").splitlines()
        if (match := re.match(r"^\| `([^`]+)` \|", line))
        and match.group(1).startswith("rdp.")
    }
    expected = {
        f"{prefix}.{name}"
        for prefix, namespace in (
            ("rdp.api", api),
            ("rdp.api.advanced", api.advanced),
            ("rdp.api.display", api.display),
            ("rdp.api.liber_primus", api.liber_primus),
            ("rdp.api.experimental", api.experimental),
        )
        for name in namespace.__all__
    }
    if len(paths) != 141 or paths != expected:
        raise AssertionError(
            f"installed public surface mismatch: documented={len(paths)} exported={len(expected)}"
        )
    for path in paths:
        module_name, attr_name = path.rsplit(".", 1)
        if not hasattr(importlib.import_module(module_name), attr_name):
            raise AssertionError(f"installed public path missing: {path}")
    for obsolete in ("RunAPI", "solve", "cipher_instance", "preview", "transform"):
        if hasattr(api, obsolete):
            raise AssertionError(
                f"obsolete installed public export present: {obsolete}"
            )


def _assert_v1_operations() -> None:
    from rdp import api

    cipher = api.CipherSpec.vigenere()
    key: api.ConcreteKey = (3, 5)
    plaintext: api.RuneIndices = (0, 1, 2, 3, 4, 5)
    ciphertext = api.encrypt(plaintext, cipher=cipher, key=key)
    if api.decrypt(ciphertext, cipher=cipher, key=key) != plaintext:
        raise AssertionError("installed known-key Vigenere round trip failed")

    result = api.run(
        api.RunSpec(
            problem_input=api.RuneIndexInput(
                ciphertext,
                tuple((0, 1) for _ in ciphertext),
            ),
            cipher=cipher,
            key_space=api.KeySpec.repeating(length=len(key)),
            solver=api.SolverSpec.beam_search(width=1, rounds=1, seed=7),
            initial_keys=(key,),
            telemetry_enabled=False,
        )
    )
    if not isinstance(result, api.RunResult):
        raise AssertionError("installed api.run did not return RunResult")


def main() -> int:
    with (
        tempfile.TemporaryDirectory(prefix="rdp_a5_wheel_smoke_") as td,
        contextlib.chdir(td),
    ):
        loaded = []
        for name in REQUIRED_MODULES:
            mod = importlib.import_module(name)
            file = getattr(mod, "__file__", None)
            if file:
                p = Path(file).resolve()
                if _under(p, SOURCE_ROOT):
                    raise AssertionError(f"source-tree contamination for {name}: {p}")
                loaded.append((name, str(p)))
        for name in BLOCKED_MODULES:
            if importlib.util.find_spec(name) is not None:
                raise AssertionError(
                    f"development/old namespace present in wheel: {name}"
                )
        from rune_decrypter_prime.data import asset_paths

        asset_root = asset_paths.find_assets_root()
        if _under(asset_root, PROJECT_ROOT / "assets"):
            raise AssertionError(
                f"installed wheel fell back to checkout assets: {asset_root}"
            )
        package_data = Path(asset_paths.__file__).resolve().parent
        manifest_path = package_data / "assets_manifest_ci_light_v1.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        rows = manifest.get("installed_assets", [])
        if not rows:
            raise AssertionError("packaged CI-light manifest has no installed_assets")
        for row in rows:
            path = asset_root / row["final_relpath"]
            if not path.is_file():
                raise AssertionError(
                    f"packaged CI-light asset missing: {row['final_relpath']}"
                )
            if path.stat().st_size != int(row["size_bytes"]):
                raise AssertionError(
                    f"packaged CI-light size mismatch: {row['final_relpath']}"
                )
            if _sha256(path) != row["sha256"]:
                raise AssertionError(
                    f"packaged CI-light hash mismatch: {row['final_relpath']}"
                )
        lm_index = asset_root / "language_model" / "lmp" / "index.json"
        if not lm_index.is_file():
            raise AssertionError("packaged language-model index.json missing")
        from rune_decrypter_prime.scoring.language_model.paths import default_lm_root

        if default_lm_root() != lm_index.parent.resolve():
            raise AssertionError(
                "default LM root does not resolve to packaged CI-light data"
            )
        _assert_v1_public_contract()
        _assert_v1_operations()
        print(f"[a5-wheel-smoke] PASS assets={len(rows)}")
        print("[a5-wheel-smoke] PASS public_paths=141 operations=run/encrypt/decrypt")
        for name, path in loaded:
            print(f"[a5-wheel-smoke] {name} -> {path}")
        print(f"[a5-wheel-smoke] package_asset_root -> {asset_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
