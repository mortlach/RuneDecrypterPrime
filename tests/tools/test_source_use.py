"""Source runner CLI and import isolation without real builds or long searches."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import sysconfig
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "tutorials/v1/run_tutorials.py"
pytestmark = pytest.mark.tier_a


def _runner():
    spec = importlib.util.spec_from_file_location("source_use_runner_test", RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("group,count", [
    ("getting-started", 10), ("release", 13), ("bundled", 20),
    ("full-assets", 2), ("qualification", 3),
])
def test_cli_groups_keep_current_membership(group, count):
    runner = _runner()
    args = runner._parse_args([group])
    assert len(runner._selected_tutorials(runner.GROUPS[args.group])) == count


def test_only_matches_numbers_names_paths_and_preserves_order():
    runner = _runner()
    expected = runner._selected_tutorials(runner.TutorialRunSet.GETTING_STARTED)
    assert runner._resolve_only(["01", "07", "10", "01"]) == (expected[0], expected[6], expected[9])
    assert runner._resolve_only([expected[0].name, expected[6].stem,
                                 expected[9].relative_to(ROOT).as_posix()]) == (expected[0], expected[6], expected[9])


@pytest.mark.parametrize("value", ["vigenere", "no-such-tutorial", "../../outside.py"])
def test_only_rejects_ambiguous_unknown_or_outside_names(value):
    with pytest.raises(ValueError):
        _runner()._resolve_only([value])


def test_list_is_read_only_and_does_not_launch(monkeypatch, capsys):
    runner = _runner()
    monkeypatch.setattr(runner, "_prepare_output_dir", lambda: pytest.fail("list must not create output"))
    monkeypatch.setattr(runner, "_run_one", lambda *_: pytest.fail("list must not run"))
    assert runner.main(["--list"]) == 0
    output = capsys.readouterr().out
    assert "getting-started" in output and "10_prepare_a_real_source_search" in output
    assert "two_period_cribs_p13_p31_search" in output
    assert "[full-assets, qualification]" in output


def test_programmatic_main_honours_ci_run_set_not_process_argv(monkeypatch, tmp_path):
    runner = _runner()
    runner.RUN_SET = runner.TutorialRunSet.FULL_ASSET_EXAMPLES
    runner.OUTPUT_DIR = tmp_path
    launches = []
    monkeypatch.setattr(sys, "argv", ["pytest", "-q", "--unrelated"])
    monkeypatch.setattr(runner, "_run_one", lambda path: (launches.append(path) is None, None))
    assert runner.main() == 0
    assert tuple(path.name for path in launches) == runner.FULL_ASSET_EXAMPLE_NAMES


def test_child_environment_prepends_source_and_keeps_output_routing(monkeypatch, tmp_path):
    runner = _runner()
    runner.OUTPUT_DIR = tmp_path
    runner._prepare_output_dir()
    monkeypatch.setenv("PYTHONPATH", "some_existing_path")
    script = runner._getting_started()[0]
    env = runner._child_environment(script)
    assert env["PYTHONPATH"].split(os.pathsep)[0] == str(ROOT / "src")
    assert env["PYTHONPATH"].endswith("some_existing_path")
    assert env["RDP_OUTPUT_ROOT"] == str(runner._output_dir() / script.stem)
    assert os.environ["PYTHONPATH"] == "some_existing_path"


def test_cli_failure_and_logging_options_preserve_exit_status(monkeypatch, tmp_path, capsys):
    runner = _runner()
    runner.OUTPUT_DIR = tmp_path
    calls = []
    def fail(path):
        calls.append(path)
        assert runner.WRITE_OUTPUT_LOGS is False
        assert runner.CONSOLE_OUTPUT is runner.ConsoleOutput.FULL
        return False, None
    monkeypatch.setattr(runner, "_run_one", fail)
    assert runner.main(["--only", "01", "07", "--no-logs", "--full-output",
                        "--stop-on-first-failure"]) == 1
    assert len(calls) == 1
    assert "selected=2 run=1 passed=0 failed=1" in capsys.readouterr().out


def test_source_precedes_installed_package_even_if_already_later_on_path(tmp_path):
    unrelated = tmp_path / "installed"
    (unrelated / "rdp").mkdir(parents=True)
    (unrelated / "rdp/__init__.py").write_text("raise RuntimeError('wrong RDP imported')")
    code = "\n".join((
        "import sys, runpy", f"sys.path[:0] = [{str(unrelated)!r}, {str(ROOT / 'src')!r}]",
        f"runpy.run_path({str(RUNNER)!r}, run_name='source_probe')",
        "import rdp", f"assert rdp.__file__ == {str(ROOT / 'src/rdp/__init__.py')!r}",
        "print('checkout origin verified')",
    ))
    result = subprocess.run([sys.executable, "-I", "-B", "-X", "utf8", "-c", code],
                            cwd=tmp_path, text=True, encoding="utf-8", capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_standalone_list_from_unrelated_cwd_needs_no_pythonpath(tmp_path):
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "RDP_OUTPUT_ROOT": str(tmp_path / "output")}
    env.pop("PYTHONPATH", None)
    result = subprocess.run([sys.executable, "-I", "-S", "-B", "-X", "utf8", str(RUNNER), "--list"],
                            cwd=tmp_path, env=env, text=True, encoding="utf-8", capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Runner groups" in result.stdout
    assert not (tmp_path / "output").exists()


def test_basic_source_subprocess_does_not_need_rdps_native_or_other_runtime_deps(tmp_path):
    payload = json.dumps({"src": str(ROOT / "src"), "site": sysconfig.get_paths()["purelib"]})
    code = r'''
import importlib.abc, json, sys
from pathlib import Path
payload = json.loads(sys.argv[1])
sys.path.extend([payload["src"], payload["site"]])
class Deny(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in {"zstandard", "tzdata", "platformdirs", "lark", "torch"} or fullname.rsplit(".", 1)[-1] in {"_fastlm", "_hamming", "_span_hamming_fast", "_ngram_hamming_fast"}:
            raise ModuleNotFoundError(fullname, name=fullname)
sys.meta_path.insert(0, Deny())
import rdp
from rdp import api
assert Path(rdp.__file__).resolve().is_relative_to(Path(payload["src"]).resolve())
plain, key = (0, 1, 2, 3, 4, 5), (3, 5)
cipher = api.CipherSpec.vigenere()
assert api.decrypt(api.encrypt(plain, cipher=cipher, key=key), cipher=cipher, key=key) == plain
data = api.liber_primus.load_source("welcome_pilgrim")
assert len(data.ct_idx) == len(data.wli) == 515
assert api.score_many(()) == ()
'''
    env = {**os.environ, "RDP_OUTPUT_ROOT": str(tmp_path)}
    result = subprocess.run([sys.executable, "-I", "-S", "-B", "-X", "utf8", "-c", code, payload],
                            cwd=tmp_path, env=env, text=True, encoding="utf-8", capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr
