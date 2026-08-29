from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

class AssetProfileError(ValueError):
    """Raised when the canonical V1 asset-profile contract is invalid."""

@dataclass(frozen=True, slots=True)
class AssetProfile:
    name: str
    description: str
    release_asset_set: str
    verification_manifest: str
    download_release_assets: bool
    language_model_orders: tuple[int, ...]
    pytest_marker_expression: str | None
    tutorial_run_set: str

def _require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AssetProfileError(f'{label} must be a non-empty string')
    return value.strip()

def _require_manifest_path(value: Any, label: str) -> str:
    text = _require_text(value, label)
    if '\\' in text:
        raise AssetProfileError(f'{label} must use forward slashes')
    path = Path(text)
    if path.is_absolute() or any((part in {'', '.', '..'} for part in path.parts)):
        raise AssetProfileError(f'{label} must be a safe repository-relative path')
    if path.suffix.lower() != '.json':
        raise AssetProfileError(f'{label} must name a JSON file')
    return path.as_posix()

def _profile(name: str, raw: Any) -> AssetProfile:
    if not isinstance(raw, dict):
        raise AssetProfileError(f'profiles.{name} must be an object')
    expected = {'description', 'release_asset_set', 'verification_manifest', 'download_release_assets', 'language_model_orders', 'pytest_marker_expression', 'tutorial_run_set'}
    if set(raw) != expected:
        missing = sorted(expected - set(raw))
        extra = sorted(set(raw) - expected)
        raise AssetProfileError(f'profiles.{name} fields mismatch; missing={missing}, extra={extra}')
    download = raw['download_release_assets']
    if not isinstance(download, bool):
        raise AssetProfileError(f'profiles.{name}.download_release_assets must be boolean')
    orders_raw = raw['language_model_orders']
    if not isinstance(orders_raw, list) or not orders_raw:
        raise AssetProfileError(f'profiles.{name}.language_model_orders must be a non-empty list')
    if any((isinstance(order, bool) or not isinstance(order, int) for order in orders_raw)):
        raise AssetProfileError(f'profiles.{name}.language_model_orders must contain integers')
    orders = tuple(orders_raw)
    if orders != tuple(sorted(set(orders))) or any((order not in {1, 2, 3, 4} for order in orders)):
        raise AssetProfileError(f'profiles.{name}.language_model_orders must be unique sorted orders 1-4')
    marker = raw['pytest_marker_expression']
    if marker is not None and (not isinstance(marker, str) or not marker.strip()):
        raise AssetProfileError(f'profiles.{name}.pytest_marker_expression must be null or non-empty')
    return AssetProfile(name=name, description=_require_text(raw['description'], f'profiles.{name}.description'), release_asset_set=_require_text(raw['release_asset_set'], f'profiles.{name}.release_asset_set'), verification_manifest=_require_manifest_path(raw['verification_manifest'], f'profiles.{name}.verification_manifest'), download_release_assets=download, language_model_orders=orders, pytest_marker_expression=None if marker is None else marker.strip(), tutorial_run_set=_require_text(raw['tutorial_run_set'], f'profiles.{name}.tutorial_run_set'))

def load_asset_profiles(path: Path | str) -> tuple[str, dict[str, AssetProfile]]:
    manifest_path = Path(path)
    try:
        raw = json.loads(manifest_path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise AssetProfileError(f'invalid asset profile JSON {manifest_path}: {exc}') from exc
    if not isinstance(raw, dict):
        raise AssetProfileError('asset profile manifest must be an object')
    if raw.get('schema') != 'rdp_v1_asset_profiles.v1':
        raise AssetProfileError('asset profile schema must be rdp_v1_asset_profiles.v1')
    profiles_raw = raw.get('profiles')
    if not isinstance(profiles_raw, dict) or not profiles_raw:
        raise AssetProfileError('profiles must be a non-empty object')
    profiles = {name: _profile(name, value) for name, value in profiles_raw.items()}
    default = _require_text(raw.get('default_profile'), 'default_profile')
    if default not in profiles:
        raise AssetProfileError(f'default_profile {default!r} is not defined')
    return (default, profiles)

def select_asset_profile(path: Path | str, name: str | None=None) -> AssetProfile:
    default, profiles = load_asset_profiles(path)
    selected = default if name is None else name
    if selected not in profiles:
        raise AssetProfileError(f'unknown asset profile {selected!r}; expected one of {sorted(profiles)}')
    return profiles[selected]
__all__ = ['AssetProfile', 'AssetProfileError', 'load_asset_profiles', 'select_asset_profile']
