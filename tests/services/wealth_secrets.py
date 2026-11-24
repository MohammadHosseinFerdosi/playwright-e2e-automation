"""Load ``secrets/uat_wealth.yaml`` (gitignored)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import BaseModel, ConfigDict

from tests.config.settings import REPO_ROOT

DEFAULT_SECRETS_PATH = REPO_ROOT / "secrets" / "uat_wealth.yaml"


class WealthSecrets(BaseModel):
    """UAT identity for wealth silver buy/sell UI flows."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    silver_kyc_cell_number: str

    def __repr__(self) -> str:
        return "WealthSecrets(silver_kyc_cell_number='***')"

    def __str__(self) -> str:
        return repr(self)

    def require_ready(self) -> WealthSecrets:
        """Skip when placeholder values are still present."""
        value = self.silver_kyc_cell_number
        if (
            not value
            or "CHANGE_ME" in value
            or value.startswith("CHANGE")
            or "XXX" in value.upper()
        ):
            pytest.skip(
                "Fill secrets/uat_wealth.yaml "
                "(field 'silver_kyc_cell_number' still looks like a placeholder)"
            )
        return self


def load_wealth_secrets(path: Path | None = None) -> WealthSecrets | None:
    """Load secrets YAML if present."""
    target = path or DEFAULT_SECRETS_PATH
    if not target.is_file():
        return None
    raw: Any = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        return None
    return WealthSecrets.model_validate(raw)


def require_wealth_secrets() -> WealthSecrets:
    """Load secrets or skip the test."""
    secrets = CHANGE_ME
    if secrets is None:
        pytest.skip(
            "Missing secrets/uat_wealth.yaml — copy "
            "secrets/uat_wealth.example.yaml and fill UAT values"
        )
    return secrets.require_ready()
