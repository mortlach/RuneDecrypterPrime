from __future__ import annotations
import re
import subprocess
import sys
from pathlib import Path
import pytest
pytestmark = pytest.mark.tier_a

def test_railfence_tutorial_script_recovers_plaintext():
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / 'tutorials' / 'v1' / 'Tutorial_Railfence.py'
    assert script.is_file(), 'tutorial script is missing'
    src_path = repo_root / 'src'
    launch = f"import runpy, sys; sys.path.insert(0, {str(src_path)!r}); runpy.run_path({str(script)!r}, run_name='__main__')"
    result = subprocess.run([sys.executable, '-c', launch], cwd=str(repo_root), capture_output=True, text=True, encoding='utf-8', errors='replace', check=True)
    stdout = result.stdout
    assert 'RDP standard summary' in stdout, stdout
    assert 'match_ratio: 1.0' in stdout, stdout
    assert 'stop_category: budget' in stdout, stdout
    match = re.search('Match ratio:\\s*([0-9.]+)', stdout)
    assert match, f'match ratio not found in output:\n{stdout}'
    assert float(match.group(1)) >= 0.95
