"""Request/response models for postal-code address inquiry."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from tests.api.kyc.models import KycResult, KycResultBody, parse_result_body

logger = logging.getLogger(__name__)


class PostalAddress(BaseModel):
    """Address payload returned by a successful postal-code inquiry."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    province: str | None = None
    town_ship: str | None = Field(default=None, alias="townShip")
    district: str | None = None
    locality_name: str | None = Field(default=None, alias="localityName")
    sub_locality: str | None = Field(default=None, alias="subLocality")
    street: str | None = None
    street2: str | None = None
    house_no: str | None = Field(default=None, alias="houseNo")
    house_number: int | str | None = Field(default=None, alias="houseNumber")
    floor: str | None = None


class PostalCodeInquiryBody(BaseModel):
    """Successful postal-code inquiry envelope plus ``address``."""

    model_config = ConfigDict(extra="ignore")

    result: KycResult
    address: PostalAddress | None = None


class AddressProviderSetting(BaseModel):
    """One provider row in admin address ``providerSettings``."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    provider_name: int = Field(alias="providerName")
    weight: float


class AddressSettingDetail(BaseModel):
    """``settingDetail`` for admin address provider GET/POST."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    provider_settings: list[AddressProviderSetting] = Field(alias="providerSettings")


class AddressProviderSettingsRequest(BaseModel):
    """Admin POST body to pin or restore address provider weights."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    setting_detail: AddressSettingDetail = Field(alias="settingDetail")

    def to_payload(self) -> dict[str, Any]:
        """Serialize the admin settings JSON body, including unknown live fields."""
        return self.model_dump(by_alias=True, exclude_none=True)


class AddressSettingsBody(BaseModel):
    """Admin GET/POST body that includes ``settingDetail``."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    setting_detail: AddressSettingDetail = Field(alias="settingDetail")
    result: KycResult | None = None


def parse_postal_code_inquiry_body(
    body: Any,
) -> PostalCodeInquiryBody | KycResultBody | Any:
    """Parse a postal-code inquiry JSON body."""
    if not isinstance(body, dict):
        return body
    if "address" in body:
        try:
            return PostalCodeInquiryBody.model_validate(body)
        except ValidationError as exc:
            logger.debug("postal-code body did not match PostalCodeInquiryBody: %s", exc)
    return parse_result_body(body) or body


def parse_address_settings_body(
    body: Any,
) -> AddressSettingsBody | KycResultBody | Any:
    """Parse admin address-provider GET/POST JSON."""
    if not isinstance(body, dict):
        return body
    if "settingDetail" in body:
        try:
            return AddressSettingsBody.model_validate(body)
        except ValidationError as exc:
            logger.debug("address settings body did not match AddressSettingsBody: %s", exc)
    return parse_result_body(body) or body
