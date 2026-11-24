"""Load ``secrets/uat_postal_code.yaml`` (gitignored)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import BaseModel, ConfigDict, Field

from tests.api.kyc.addresses.models import PostalAddress
from tests.config.settings import REPO_ROOT

DEFAULT_SECRETS_PATH = REPO_ROOT / "secrets" / "uat_postal_code.yaml"


class PostalCodeSecrets(BaseModel):
    """UAT values for postal-code address inquiry."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    requester_app_name: str = "testData"
    user_id: str
    postal_code: str
    unknown_postal_code: str
    invalid_postal_code: str
    jibit_address: PostalAddress = Field(alias="jibitAddress")

    def __repr__(self) -> str:
        return (
            "PostalCodeSecrets("
            f"requester_app_name={self.requester_app_name!r}, "
            "user_id='***', postal_code='***', unknown_postal_code='***', "
            f"invalid_postal_code={self.invalid_postal_code!r})"
        )

    def __str__(self) -> str:
        return repr(self)

    def require_ready(self) -> PostalCodeSecrets:
        """Skip when placeholder values are still present."""
        for field_name, value in self.model_dump().items():
            if isinstance(value, dict):
                _skip_if_placeholder_map(field_name, value)
                continue
            if isinstance(value, str) and _is_placeholder(value):
                pytest.skip(
                    f"Fill secrets/uat_postal_code.yaml "
                    f"(field {field_name!r} still looks like a placeholder)"
                )
        return self


def _is_placeholder(value: str) -> bool:
    return "CHANGE_ME" in value or value.startswith("CHANGE") or "XXX" in value.upper()


def _skip_if_placeholder_map(field_name: str, values: dict[str, Any]) -> None:
    for nested_name, nested_value in values.items():
        if isinstance(nested_value, str) and _is_placeholder(nested_value):
            pytest.skip(
                f"Fill secrets/uat_postal_code.yaml "
                f"(field {field_name}.{nested_name!r} still looks like a placeholder)"
            )


def load_postal_code_secrets(path: Path | None = None) -> PostalCodeSecrets | None:
    """Load secrets YAML if present."""
    target = path or DEFAULT_SECRETS_PATH
    if not target.is_file():
        return None
    raw: Any = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        return None
    return PostalCodeSecrets.model_validate(raw)


def require_postal_code_secrets() -> PostalCodeSecrets:
    """Load secrets or skip the test."""
    secrets = load_postal_code_secrets()
    if secrets is None:
        pytest.skip(
            "Missing secrets/uat_postal_code.yaml — copy "
            "secrets/uat_postal_code.example.yaml and fill UAT values"
        )
    return secrets.require_ready()
