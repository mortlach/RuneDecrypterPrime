"""Fast helper contracts. Real compiler proof runs separately in disposable trees."""
from __future__ import annotations

import json
import runpy
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools import build_native as builder

pytestmark = pytest.mark.tier_a


@pytest.mark.parametrize("all_native,count", [(False, 3), (True, 4)])
def test_selected_modules_preserve_release_boundary(all_native, count):
    names = builder._selected_modules(all_native)
    assert len(names) == count
    assert names[:3] == (
        "rdp.scoring.language_model._fastlm",
        "rdp.scoring.hamming._hamming",
        "rdp.scoring.span_hamming._span_hamming_fast",
    )
    assert ("rdp.scoring.ngram_hamming._ngram_hamming_fast" in names) is all_native


@pytest.mark.parametrize("argv,experimental", [([], False), (["--all"], True)])
def test_main_delegates_then_verifies_selected_modules(monkeypatch, tmp_path, argv, experimental):
    calls = []
    monkeypatch.setattr(builder, "_missing_build_requirements", lambda: ())
    monkeypatch.setattr(builder, "_output_directory", lambda: tmp_path)
    monkeypatch.setattr(builder, "_build_release", lambda output: calls.append(("release", output)))
    monkeypatch.setattr(builder, "_build_experimental", lambda output: calls.append(("all", output)))
    monkeypatch.setattr(builder, "_verify", lambda names, output: calls.append(("verify", names)))
    assert builder.main(argv) == 0
    assert calls[0] == ("release", tmp_path)
    assert [name for name, _ in calls] == (["release", "all", "verify"] if experimental else ["release", "verify"])
    assert calls[-1] == ("verify", builder._selected_modules(experimental))


def test_missing_dependencies_do_not_build(monkeypatch, capsys):
    monkeypatch.setattr(builder, "_missing_build_requirements", lambda: ("pybind11",))
    monkeypatch.setattr(builder, "_output_directory", lambda: pytest.fail("must not start build"))
    assert builder.main([]) == 2
    assert "pybind11" in capsys.readouterr().err


@pytest.mark.parametrize("stage", ["_build_release", "_verify"])
def test_failed_build_or_verification_is_not_success(monkeypatch, tmp_path, capsys, stage):
    monkeypatch.setattr(builder, "_missing_build_requirements", lambda: ())
    monkeypatch.setattr(builder, "_output_directory", lambda: tmp_path)
    monkeypatch.setattr(builder, "_build_release", lambda *_: None)
    monkeypatch.setattr(builder, "_verify", lambda *_: None)
    def fail(*_):
        raise RuntimeError("controlled failure")
    monkeypatch.setattr(builder, stage, fail)
    assert builder.main([]) == 1
    captured = capsys.readouterr()
    assert "controlled failure" in captured.err
    assert "Native modules are ready" not in captured.out


def test_default_uses_canonical_build_with_external_scratch(monkeypatch, tmp_path):
    commands = []
    def run(command, **kwargs):
        commands.append((command, kwargs))
        for name in builder.RELEASE_NATIVE_MODULES:
            path = builder._artifact(tmp_path / "lib", name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"test artifact")
    monkeypatch.setattr(builder, "_run", run)
    builder._build_release(tmp_path)
    command, options = commands[0]
    assert command[:5] == [sys.executable, "-B", "-X", "utf8", str(builder.SETUP_PY)]
    assert command[5:7] == ["build_ext", "--inplace"]
    assert command[command.index("--build-temp") + 1] == str(tmp_path / "tmp")
    assert command[command.index("--build-lib") + 1] == str(tmp_path / "lib")
    assert options["log"].parent == tmp_path


def test_skipped_native_build_is_detected_even_before_import(monkeypatch, tmp_path):
    monkeypatch.setattr(builder, "_run", lambda *_, **__: None)
    with pytest.raises(RuntimeError, match="did not produce"):
        builder._build_release(tmp_path)


def test_all_stages_unchanged_builder_and_only_copies_selected_binary(monkeypatch, tmp_path):
    source = tmp_path / "src"
    destination = source / "rdp/scoring/ngram_hamming"
    destination.mkdir(parents=True)
    unrelated = destination / "keep.txt"
    unrelated.write_text("keep")
    monkeypatch.setattr(builder, "SRC", source)
    output = tmp_path / "evidence"
    def run(command, **kwargs):
        stage = output / "research"
        staged = stage / builder.NGRAM_BUILDER.relative_to(builder.ROOT)
        assert command[-1] == str(staged)
        assert staged.read_bytes() == builder.NGRAM_BUILDER.read_bytes()
        assert kwargs["cwd"] == stage
        assert command[4] == "-c"
        extension = SimpleNamespace(
            sources=[str(stage / builder.NGRAM_REL / "fast_bindings.cpp")],
            extra_compile_args=["retained compiler flags"],
            extra_link_args=["retained linker flags"],
        )
        called = []
        namespace = {"REPO_ROOT": stage, "ext_modules": [extension],
                     "main": lambda: called.append(tuple(sys.argv))}
        def load(path, run_name):
            assert path == str(staged)
            assert run_name != "__main__"
            return namespace
        with monkeypatch.context() as child:
            child.setattr(runpy, "run_path", load)
            child.setattr(sys, "argv", ["-c", str(staged)])
            exec(command[-2], {})
        assert extension.sources == [(builder.NGRAM_REL / "fast_bindings.cpp").as_posix()]
        assert extension.extra_compile_args == ["retained compiler flags"]
        assert extension.extra_link_args == ["retained linker flags"]
        assert called == [(str(staged),)]
        for name in builder.EXPERIMENTAL_NATIVE_MODULES:
            target = builder._artifact(stage / "src", name)
            target.write_bytes(b"fresh experimental artifact")
    monkeypatch.setattr(builder, "_run", run)
    builder._build_experimental(output)
    for name in builder.EXPERIMENTAL_NATIVE_MODULES:
        assert builder._artifact(source, name).read_bytes() == b"fresh experimental artifact"
    assert unrelated.read_text() == "keep"


def test_verification_uses_fresh_isolated_checkout_native_imports(monkeypatch, tmp_path):
    captured = []
    monkeypatch.setattr(builder, "_run", lambda command, **kw: captured.append(command))
    builder._verify(builder.RELEASE_NATIVE_MODULES, tmp_path)
    command = captured[0]
    assert command[1:5] == ["-I", "-B", "-X", "utf8"]
    payload = json.loads(command[-1])
    assert payload["src"] == str(builder.SRC)
    assert payload["modules"] == list(builder.RELEASE_NATIVE_MODULES)
    assert "ExtensionFileLoader" in command[-2]
    assert "actual != expected" in command[-2]


def test_build_output_honours_external_root_without_importing_rdp(monkeypatch, tmp_path):
    monkeypatch.setenv("RDP_OUTPUT_ROOT", str(tmp_path))
    output = builder._output_directory()
    assert output.parent == tmp_path / "build_native"
    assert output.is_dir()


@pytest.mark.parametrize("value", ["", "relative"])
def test_invalid_output_root_fails(monkeypatch, value):
    monkeypatch.setenv("RDP_OUTPUT_ROOT", value)
    with pytest.raises(ValueError, match="absolute"):
        builder._output_directory()


def test_child_failure_is_logged_and_nonzero(tmp_path, capsys):
    log = tmp_path / "failed.log"
    with pytest.raises(RuntimeError, match="exit code 7"):
        builder._run([sys.executable, "-B", "-X", "utf8", "-c",
                      "print('compiler failure'); raise SystemExit(7)"],
                     label="Fixture compiler", log=log, cwd=tmp_path)
    assert "compiler failure" in log.read_text(encoding="utf-8")
    assert "compiler failure" in capsys.readouterr().out


def test_release_contract_keeps_fourth_binary_out():
    contract = (builder.ROOT / "tools/ci/a5_artifact_contract.py").read_text(encoding="utf-8")
    assert "experimental _ngram_hamming_fast must remain unbuilt" in contract
    assert "_ngram_hamming_fast" not in builder.SETUP_PY.read_text(encoding="utf-8")
    source = Path(builder.__file__).read_text(encoding="utf-8")
    assert "/O2" not in source and "-march=native" not in source
