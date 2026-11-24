"""Microservice gateway path prefixes shared across Platform API teams.

Loaded from ``config/environment-stage.yaml`` so teams do not invent paths.
``MS_BILL_MNG_PATH`` is pytest-only (not in the Robot YAML) and is defined here.

Import only the constants a module uses — unused named exports were removed
(YAGNI). Lookup by YAML key is always available via ``get_ms_path``.
"""

from __future__ import annotations

from collections.abc import Mapping
from functools import lru_cache

import yaml

from tests.config.settings import ENVIRONMENT_YAML

# Present in pytest ports but absent from Robot environment-stage.yaml.
_EXTRA_MS_PATHS: dict[str, str] = {
    "MS_BILL_MNG_PATH": "/bill-mng/platform/api",
}


@lru_cache(maxsize=1)
def ms_path_map() -> Mapping[str, str]:
    """All ``MS_*`` path prefixes from env YAML plus pytest-only extras."""
    raw = yaml.safe_load(ENVIRONMENT_YAML.read_text(encoding="utf-8")) or {}
    paths: dict[str, str] = dict(_EXTRA_MS_PATHS)
    for key, value in raw.items():
        if isinstance(key, str) and isinstance(value, str) and key.startswith("MS_"):
            paths[key] = value
    return paths


def get_ms_path(name: str) -> str:
    """Look up a path by YAML key name (e.g. ``MS_TGS_PATH``).

    Raises:
        KeyError: When ``name`` is not present in the env map.
    """
    try:
        return ms_path_map()[name]
    except KeyError as exc:
        known = ", ".join(sorted(ms_path_map()))
        raise KeyError(f"Unknown MS path {name!r}. Known: {known}") from exc


def _path(name: str) -> str:
    return get_ms_path(name)


# Named exports actually imported by the suite today.
MS_UAA_PATH = _path("MS_UAA_PATH")
MS_PURCHASE_PATH = _path("MS_PURCHASE_PATH")
MS_WALLET_PROVIDER_PATH = _path("MS_WALLET_PROVIDER_PATH")
MS_NEMO_PATH = _path("MS_NEMO_PATH")
MS_BILL_MNG_PATH = _path("MS_BILL_MNG_PATH")
MS_TGS_PATH = _path("MS_TGS_PATH")
MS_SWITCH_PSP_PATH = _path("MS_SWITCH_PSP_PATH")
MS_MOCK_PATH = _path("MS_MOCK_PATH")
MS_KYC_LIVENESS_PATH = _path("MS_KYC_LIVENESS_PATH")
MS_KYC_PATH = _path("MS_KYC_PATH")
MS_DIGITAL_SIGNATURE_PATH = _path("MS_DIGITAL_SIGNATURE_PATH")
MS_GL_PATH = _path("MS_GL_PATH")
MS_PROMISSORY_NOTE_PATH = _path("MS_PROMISSORY_NOTE_PATH").rstrip("/")
MS_BANK_TRANSFER_PATH = _path("MS_BANK_TRANSFER_PATH")
