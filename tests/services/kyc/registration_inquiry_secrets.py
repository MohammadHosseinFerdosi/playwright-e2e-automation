"""Load ``secrets/uat_registration_inquiry.yaml`` (gitignored)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from tests.api.kyc.registration.models import BirthCertificateInfo
from tests.config.settings import REPO_ROOT

DEFAULT_SECRETS_PATH = REPO_ROOT / "secrets" / "uat_registration_inquiry.yaml"


class RegistrationPerson(BaseModel):
    """One UAT person used as inquiry input and expected identity."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    national_code: str
    birth_date: str
    persian_birth_date: str | None = None
    first_name: str | None = Field(default=None, alias="firstName")
    last_name: str | None = Field(default=None, alias="lastName")
    father_name: str | None = Field(default=None, alias="fatherName")
    birth_place: str | None = Field(default=None, alias="birthPlace")
    shenasname_seri: str | None = Field(default=None, alias="shenasnameSeri")
    shenasname_serial: str | None = Field(default=None, alias="shenasnameSerial")
    shenasname_no: str | None = Field(default=None, alias="shenasnameNo")
    birth_certificate_info: BirthCertificateInfo | None = Field(
        default=None, alias="birthCertificateInfo"
    )
    death_status: int | None = Field(default=None, alias="deathStatus")
    gender: int | None = Field(default=None, alias="gender")

    @field_validator(
        "national_code",
        "birth_date",
        "persian_birth_date",
        "first_name",
        "last_name",
        "father_name",
        "birth_place",
        "shenasname_seri",
        "shenasname_serial",
        "shenasname_no",
        mode="before",
    )
    @classmethod
    def _stringify(cls, value: Any) -> Any:
        if value is None:
            return value
        return str(value)


class RegistrationInquirySecrets(BaseModel):
    """UAT values for identity registration inquiry."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    requester_app_name: str = "AutomationTestData"
    min_weight_auto_weighting: float = 0.05
    wrong_national_code: str
    valid_person: RegistrationPerson
    dead_person: RegistrationPerson
    invalid_person: RegistrationPerson
    alternate_person: RegistrationPerson = Field(
        validation_alias=AliasChoices(
            "alternate_person",
            "missing_birth_place_person",
        )
    )

    def __repr__(self) -> str:
        return (
            "RegistrationInquirySecrets("
            f"requester_app_name={self.requester_app_name!r}, "
            "national_codes='***')"
        )

    def __str__(self) -> str:
        return repr(self)

    def require_ready(self) -> RegistrationInquirySecrets:
        """Skip when placeholder values are still present."""
        if _is_placeholder(self.wrong_national_code):
            pytest.skip("Fill secrets/uat_registration_inquiry.yaml (wrong_national_code)")
        for name in (
            "valid_person",
            "dead_person",
            "invalid_person",
            "alternate_person",
        ):
            person: RegistrationPerson = getattr(self, name)
            if _is_placeholder(person.national_code) or _is_placeholder(person.birth_date):
                pytest.skip(
                    f"Fill secrets/uat_registration_inquiry.yaml (field {name} still looks like a placeholder)"
                )
        return self

    def journal_national_codes(self) -> tuple[str, ...]:
        """National codes whose journals must be cleared before a scenario."""
        return (
            self.valid_person.national_code,
            self.dead_person.national_code,
            self.invalid_person.national_code,
            self.alternate_person.national_code,
            self.wrong_national_code,
        )


def _is_placeholder(value: str) -> bool:
    return "CHANGE_ME" in value or value.startswith("CHANGE") or "XXX" in value.upper()


def load_registration_inquiry_secrets(
    path: Path | None = None,
) -> RegistrationInquirySecrets | None:
    """Load secrets YAML if present."""
    target = path or DEFAULT_SECRETS_PATH
    if not target.is_file():
        return None
    raw: Any = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        return None
    return RegistrationInquirySecrets.model_validate(raw)


def require_registration_inquiry_secrets() -> RegistrationInquirySecrets:
    """Load secrets or skip the test."""
    secrets = load_registration_inquiry_secrets()
    if secrets is None:
        pytest.skip(
            "Missing secrets/uat_registration_inquiry.yaml — copy "
            "secrets/uat_registration_inquiry.example.yaml and fill UAT values"
        )
    return secrets.require_ready()
