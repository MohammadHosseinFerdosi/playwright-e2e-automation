"""Request/response models for identity registration inquiry."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from tests.api.kyc.models import KycResult, KycResultBody, parse_result_body

logger = logging.getLogger(__name__)


class BirthCertificateInfo(BaseModel):
    """Birth-certificate serial block on a registration inquiry body."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    birth_certificate_serial: str | None = Field(
        default=None, alias="birthCertificateSerial"
    )
    birth_certificate_number: str | None = Field(
        default=None, alias="birthCertificateNumber"
    )
    birth_certificate_series: str | None = Field(
        default=None, alias="birthCertificateSeries"
    )


class RegistrationInquiryRequest(BaseModel):
    """POST /kyc/identity/registration/inquiry body."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    national_code: str | None = Field(default=None, alias="nationalCode")
    birth_date: str | None = Field(default=None, alias="birthDate")
    force_inquiry: bool | None = Field(default=None, alias="forceInquiry")
    inquiry_type: int | None = Field(default=None, alias="inquiryType")
    strong_validation: bool | None = Field(default=None, alias="strongValidation")

    def to_payload(self) -> dict[str, Any]:
        """Serialize the inquiry JSON body, omitting unset identity fields."""
        return self.model_dump(by_alias=True, exclude_none=True)


class RegistrationInquiryBody(BaseModel):
    """Successful registration inquiry identity envelope."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    result: KycResult
    first_name: str | None = Field(default=None, alias="firstName")
    last_name: str | None = Field(default=None, alias="lastName")
    father_name: str | None = Field(default=None, alias="fatherName")
    national_code: str | None = Field(default=None, alias="nationalCode")
    birth_date: str | None = Field(default=None, alias="birthDate")
    birth_place: str | None = Field(default=None, alias="birthPlace")
    shenasname_seri: str | None = Field(default=None, alias="shenasnameSeri")
    shenasname_serial: str | None = Field(default=None, alias="shenasnameSerial")
    shenasname_no: str | None = Field(default=None, alias="shenasnameNo")
    birth_certificate_info: BirthCertificateInfo | None = Field(
        default=None, alias="birthCertificateInfo"
    )
    death_status: int | None = Field(default=None, alias="deathStatus")
    gender: int | None = Field(default=None, alias="gender")


class RegistrationProviderSetting(BaseModel):
    """One provider row in admin registration ``providerSettings``."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    provider_name: int = Field(alias="providerName")
    priority: int | None = None
    weight: float
    active: bool | None = None


class RegistrationSettingsRequest(BaseModel):
    """Admin POST body to pin or restore registration provider weights."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    inquiry_type: int | None = Field(default=None, alias="inquiryType")
    provider_settings: list[RegistrationProviderSetting] = Field(
        alias="providerSettings"
    )
    active_auto_weighting: bool = Field(alias="activeAutoWeighting")
    min_weight_auto_weighting: float = Field(alias="minWeightAutoWeighting")

    def to_payload(self) -> dict[str, Any]:
        """Serialize the admin settings JSON body, omitting unset inquiry type."""
        return self.model_dump(by_alias=True, exclude_none=True)


class RegistrationSettingsSearchBody(BaseModel):
    """Admin search body with the live registration provider list."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    providers: list[RegistrationProviderSetting] = Field(default_factory=list)
    min_weight_auto_weighting: float | None = Field(
        default=None, alias="minWeightAutoWeighting"
    )
    active_auto_weighting: bool | None = Field(
        default=None, alias="activeAutoWeighting"
    )
    result: KycResult | None = None


def parse_registration_inquiry_body(
    body: Any,
) -> RegistrationInquiryBody | KycResultBody | Any:
    """Parse a registration inquiry JSON body."""
    if not isinstance(body, dict):
        return body
    if "nationalCode" in body or "firstName" in body:
        try:
            return RegistrationInquiryBody.model_validate(body)
        except ValidationError as exc:
            logger.debug(
                "registration inquiry body did not match RegistrationInquiryBody: %s",
                exc,
            )
    return parse_result_body(body) or body


def parse_registration_settings_body(
    body: Any,
) -> RegistrationSettingsSearchBody | KycResultBody | Any:
    """Parse admin registration-provider POST/search JSON."""
    if not isinstance(body, dict):
        return body
    if "providers" in body:
        try:
            return RegistrationSettingsSearchBody.model_validate(body)
        except ValidationError as exc:
            logger.debug(
                "registration settings body did not match search model: %s", exc
            )
    return parse_result_body(body) or body
