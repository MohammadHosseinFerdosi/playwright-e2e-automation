"""Request/response models for Shahkar cell-number inquiry."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from tests.api.kyc.models import KycResult, KycResultBody, parse_result_body

logger = logging.getLogger(__name__)


class CellNumberInquiryRequest(BaseModel):
    """POST /kyc/cell-number/inquiry body."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    cell_number: str | None = Field(default=None, alias="cellNumber")
    national_code: str | None = Field(default=None, alias="nationalCode")

    def to_payload(self) -> dict[str, Any]:
        """Serialize the inquiry JSON body, omitting unset identity fields."""
        return self.model_dump(by_alias=True, exclude_none=True)


class CellNumberInquiryBody(BaseModel):
    """Successful cell-number inquiry envelope plus ``verified``."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    result: KycResult
    verified: bool | None = None


class ShahkarProviderSetting(BaseModel):
    """One provider entry in admin Shahkar ``providerSettings``."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    provider_name: int = Field(alias="providerName")
    weight: float
    active: bool


class ShahkarSettingDetail(BaseModel):
    """``settingDetail`` for admin Shahkar provider POST and search."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    provider_settings: list[ShahkarProviderSetting] = Field(alias="providerSettings")
    active_auto_weighting: bool | None = Field(default=None, alias="activeAutoWeighting")
    min_weight_auto_weighting: float | None = Field(
        default=None, alias="minWeightAutoWeighting"
    )


class ShahkarProviderSettingsRequest(BaseModel):
    """Admin POST body to pin or restore Shahkar provider settings."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    setting_detail: ShahkarSettingDetail = Field(alias="settingDetail")

    def to_payload(self) -> dict[str, Any]:
        """Serialize the admin settings JSON body, including unknown live fields."""
        return self.model_dump(by_alias=True, exclude_none=True)


class ShahkarSettingsSearchBody(BaseModel):
    """Admin search body that includes ``settingDetail``."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    setting_detail: ShahkarSettingDetail = Field(alias="settingDetail")
    result: KycResult | None = None


def parse_cell_number_inquiry_body(body: Any) -> CellNumberInquiryBody | KycResultBody | Any:
    """Parse a cell-number inquiry JSON body."""
    if not isinstance(body, dict):
        return body
    if "verified" in body:
        try:
            return CellNumberInquiryBody.model_validate(body)
        except ValidationError as exc:
            logger.debug(
                "cell-number inquiry body did not match CellNumberInquiryBody: %s", exc
            )
    return parse_result_body(body) or body


def parse_shahkar_settings_body(
    body: Any,
) -> ShahkarSettingsSearchBody | KycResultBody | Any:
    """Parse admin Shahkar settings POST/search JSON."""
    if not isinstance(body, dict):
        return body
    if "settingDetail" in body:
        try:
            return ShahkarSettingsSearchBody.model_validate(body)
        except ValidationError as exc:
            logger.debug("shahkar settings body did not match search model: %s", exc)
    return parse_result_body(body) or body
