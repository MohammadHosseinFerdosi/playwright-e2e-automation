"""Load ``secrets/uat_digital_signature.yaml`` (gitignored)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import BaseModel, ConfigDict

from tests.config.settings import REPO_ROOT

DEFAULT_SECRETS_PATH = REPO_ROOT / "secrets" / "uat_digital_signature.yaml"


class DigitalSignatureSecrets(BaseModel):
    """UAT secrets for digital-signature flows."""
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    user_id: str
    requester_app_name: str = "credit-onboarding"
    signature_type: int = 1
    password: CHANGE_ME
    custom_video_text: str

    birth_date_register: str
    birth_date_initiate: str
    national_card_code: str
    national_card_serial: str
    postal_code: str
    national_card_expiration_date: str
    father_name: str
    address: str
    city: str
    province: str
    gender: int = 1
    first_name_fa: str
    last_name_fa: str
    first_name_en: str
    last_name_en: str

    def require_ready(self) -> DigitalSignatureSecrets:
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
                    f"Fill secrets/uat_digital_signature.yaml "
                    f"(field {field_name!r} still looks like a placeholder)"
                )
        return self


def load_digital_signature_secrets(
    path: Path | None = None,
) -> DigitalSignatureSecrets | None:
    """Load secrets YAML if present."""
    target = path or DEFAULT_SECRETS_PATH
    if not target.is_file():
        return None
    raw: Any = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        return None
    return DigitalSignatureSecrets.model_validate(raw)


def require_digital_signature_secrets() -> DigitalSignatureSecrets:
    """Load secrets or skip the test."""
    secrets = CHANGE_ME
    if secrets is None:
        pytest.skip(
            "Missing secrets/uat_digital_signature.yaml — copy "
            "secrets/uat_digital_signature.example.yaml and fill UAT values"
        )
    return secrets.require_ready()
