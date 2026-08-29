from __future__ import annotations
import pathlib
import zipfile
import pytest
from tools.assets.audit_lm_large_assets import inspect_file_for_path_signatures, inspect_npz_for_path_signatures
pytestmark = pytest.mark.tier_a

def _private_drive_signature() -> bytes:
    return b'D' + b':/'

def test_npz_audit_reports_member_level_classification(tmp_path: pathlib.Path) -> None:
    npz_path = tmp_path / 'ecdf' / 'char' / 'rtl' / 'model.npz'
    npz_path.parent.mkdir(parents=True)
    with zipfile.ZipFile(npz_path, 'w') as archive:
        archive.writestr('metadata.json', b'{"source": "' + _private_drive_signature() + b'local/source"}')
        archive.writestr('array.npy', b'\x93NUMPY' + _private_drive_signature() + b'\x00' * 8)
    rows = inspect_npz_for_path_signatures(npz_path, 'ecdf/char/rtl/model.npz')
    assert rows == [{'runtime_relpath': 'ecdf/char/rtl/model.npz', 'zip_member': 'metadata.json', 'member_kind': 'text', 'signatures': ['D' + ':/'], 'classification': 'local_metadata'}, {'runtime_relpath': 'ecdf/char/rtl/model.npz', 'zip_member': 'array.npy', 'member_kind': 'npy', 'signatures': ['D' + ':/'], 'classification': 'false_positive'}]

def test_npz_audit_marks_wli_part_files_as_excluded(tmp_path: pathlib.Path) -> None:
    npz_path = tmp_path / 'wli' / 'rtl' / 'wli29_joint_rtl_4_wise_part00000.npz'
    npz_path.parent.mkdir(parents=True)
    with zipfile.ZipFile(npz_path, 'w') as archive:
        archive.writestr('array.npy', b'\x93NUMPY' + _private_drive_signature() + b'\x00' * 8)
    rows = inspect_npz_for_path_signatures(npz_path, 'wli/rtl/wli29_joint_rtl_4_wise_part00000.npz')
    assert rows[0]['classification'] == 'excluded_file'

def test_opaque_zstd_model_path_signature_is_reported_as_binary_false_positive(tmp_path: pathlib.Path) -> None:
    model = tmp_path / 'wli' / 'rtl' / 'wli29_joint_rtl_4_wise.bin.zst'
    model.parent.mkdir(parents=True)
    model.write_bytes(b'compressed bytes ' + _private_drive_signature() + b' accidental byte sequence')
    rows = inspect_file_for_path_signatures(tmp_path, model)
    assert rows == [{'runtime_relpath': 'wli/rtl/wli29_joint_rtl_4_wise.bin.zst', 'zip_member': None, 'member_kind': 'binary', 'signatures': ['D' + ':/'], 'classification': 'false_positive'}]
