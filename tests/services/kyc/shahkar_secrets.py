"""Load ``secrets/uat_shahkar.yaml`` (gitignored)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import BaseModel, ConfigDict

from tests.config.settings import REPO_ROOT

DEFAULT_SECRETS_PATH = REPO_ROOT / "secrets" / "uat_shahkar.yaml"


class ShahkarSecrets(BaseModel):
    """UAT identity for basic Shahkar cell-number inquiry."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    requester_app_name: str = "testData"
    national_code: str
    matching_cell_number: str
    mismatch_cell_number: str

    def __repr__(self) -> str:
        return (
            "ShahkarSecrets("
            f"requester_app_name={self.requester_app_name!r}, "
            "national_code='***', matching_cell_number='***', "
            "mismatch_cell_number='***')"
        )

    def __str__(self) -> str:
        return repr(self)

    def require_ready(self) -> ShahkarSecrets:
        """Skip when placeholder values are still present."""
        for field_name, value in self.model_dump().items():
            if not isinstance(value, str):
                continue
            if (
                "CHANGE_ME" in value
                or value.startswith("CHANGE")
                or "XXX" in value.upper()
            ):
                pytest.skip(
                    f"Fill secrets/uat_shahkar.yaml "
                    f"(field {field_name!r} still looks like a placeholder)"
                )
        return self


def load_shahkar_secrets(path: Path | None = None) -> ShahkarSecrets | None:
    """Load secrets YAML if present."""
    target = path or DEFAULT_SECRETS_PATH
    if not target.is_file():
        return None
    raw: Any = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        return None
    return ShahkarSecrets.model_validate(raw)


def require_shahkar_secrets() -> ShahkarSecrets:
    """Load secrets or skip the test."""
    secrets = CHANGE_ME
    if secrets is None:
        pytest.skip(
            "Missing secrets/uat_shahkar.yaml — copy "
            "secrets/uat_shahkar.example.yaml and fill UAT values"
        )
    return secrets.require_ready()
