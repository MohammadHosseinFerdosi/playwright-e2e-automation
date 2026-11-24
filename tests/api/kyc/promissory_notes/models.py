"""Promissory-note request/response models."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from tests.api.kyc.models import KycResult, KycResultBody, parse_result_body

logger = logging.getLogger(__name__)


class PromissoryOwner(BaseModel):
    """Owner block on promissory init."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    user_id: str = Field(alias="userId")
    cell_number: str = Field(alias="cellNumber")
    national_code: str = Field(alias="nationalCode")
    birth_date: str = Field(alias="birthDate")
    postal_code: str = Field(alias="postalCode")
    city: str
    address: str


class InquiryRequest(BaseModel):
    """Inquiry body: one or more tracking codes."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    tracking_codes: list[str] = Field(alias="trackingCodes")

    def to_payload(self) -> dict[str, Any]:
        """Serialize for the inquiry JSON body."""
        return self.model_dump(by_alias=True, exclude_none=True)


class RouteRequest(BaseModel):
    """Route a tracking code to a recipient (selects provider)."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    tracking_code: str = Field(alias="trackingCode")
    recipient_code: int = Field(alias="recipientCode")

    def to_payload(self) -> dict[str, Any]:
        """Serialize for the route JSON body."""
        return self.model_dump(by_alias=True, exclude_none=True)


class InitRequest(BaseModel):
    """Init after route — creates the note; provider generate is asynchronous."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    tracking_code: str = Field(alias="trackingCode")
    owner: PromissoryOwner
    iban: str
    amount: str
    due_type: str = Field(alias="dueType")
    due_offset_in_years: str = Field(alias="dueOffsetInYears")
    recipient_id: str = Field(alias="recipientId")
    recipient_code: int = Field(alias="recipientCode")
    description: str

    def to_payload(self) -> dict[str, Any]:
        """Serialize for the init JSON body."""
        return self.model_dump(by_alias=True, exclude_none=True)


class TrackingCodeRequest(BaseModel):
    """Body with a single tracking code (cancel / refund / revert / sign)."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    tracking_code: str = Field(alias="trackingCode")

    def to_payload(self) -> dict[str, Any]:
        """Serialize for tracking-code JSON bodies."""
        return self.model_dump(by_alias=True, exclude_none=True)


class TrackingCodesRequest(BaseModel):
    """Body with a list of tracking codes (notify batch)."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    tracking_codes: list[str] = Field(alias="trackingCodes")

    def to_payload(self) -> dict[str, Any]:
        """Serialize for trackingCodes JSON bodies."""
        return self.model_dump(by_alias=True, exclude_none=True)


class SealRequest(BaseModel):
    """Seal a signed promissory note."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    tracking_code: str = Field(alias="trackingCode")
    promissory_note_sign_tracking_code: str = Field(
        alias="promissoryNoteSignTrackingCode"
    )
    check_expiration: bool = Field(alias="checkExpiration")

    def to_payload(self) -> dict[str, Any]:
        """Serialize for the seal JSON body."""
        return self.model_dump(by_alias=True, exclude_none=True)


class PaymentsInitRequest(BaseModel):
    """Stamp-duty payment init body."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    user_id: str = Field(alias="userId")
    amount: int
    promissory_note_tracking_code: str = Field(alias="promissoryNoteTrackingCode")
    callback_url: str = Field(alias="callbackUrl")

    def to_payload(self) -> dict[str, Any]:
        """Serialize for payments/init JSON body."""
        return self.model_dump(by_alias=True, exclude_none=True)


class ProviderSuccessRateSearchRequest(BaseModel):
    """Paginated provider success-rate search body."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    restrictions: list[Any] = Field(default_factory=list)
    orders: list[Any] = Field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        """Serialize for success-rate search JSON body."""
        return self.model_dump(by_alias=True, exclude_none=True)


class ProviderWeightDto(BaseModel):
    """One provider row inside recipient settings."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    provider_name: int = Field(alias="providerName")
    weight: float
    active: bool
    priority: int = 1


class RecipientDto(BaseModel):
    """Recipient + provider weights for admin settings."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    recipient: int
    providers_dto: list[ProviderWeightDto] = Field(alias="providersDto")


class ProviderSettingsRequest(BaseModel):
    """POST admin settings/provider body."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    recipient_dto: RecipientDto = Field(alias="recipientDto")
    active_auto_weighting: bool = Field(alias="activeAutoWeighting")

    def to_payload(self) -> dict[str, Any]:
        """Serialize for admin settings/provider."""
        return self.model_dump(by_alias=True, exclude_none=True)


class RouteBody(BaseModel):
    """Parsed route success body."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    result: KycResult | None = None
    provider: int | None = None
    provider_name: str | None = Field(default=None, alias="providerName")
    has_payment: bool | None = Field(default=None, alias="hasPayment")
    mandatory_fields: list[str] | None = Field(default=None, alias="mandatoryFields")
    has_renew: bool | None = Field(default=None, alias="hasRenew")


class InquiryNote(BaseModel):
    """One note in an inquiry success list."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    tracking_code: str | None = Field(default=None, alias="trackingCode")
    status: int | None = None


class InquiryBody(BaseModel):
    """Parsed inquiry success body."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    result: KycResult | None = None
    promissory_notes: list[InquiryNote] | None = Field(
        default=None, alias="promissoryNotes"
    )


class ProviderSettingsBody(BaseModel):
    """Parsed GET admin settings/provider body (partial)."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    setting_detail: dict[str, Any] | None = Field(default=None, alias="settingDetail")


class RecipientListItem(BaseModel):
    """One recipient row from admin settings search."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    recipient: int


class SettingsSearchBody(BaseModel):
    """Admin settings search response."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    result: KycResult | None = None
    recipient_list: list[RecipientListItem] | None = Field(
        default=None, alias="recipientList"
    )


class SuccessRateStatItem(BaseModel):
    """One row from admin success-rate statistic."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    provider_name: int | None = Field(default=None, alias="providerName")
    success_rate: float | None = Field(default=None, alias="successRate")


class SuccessRateHistoryItem(BaseModel):
    """One row from paginated admin success-rate search."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    provider_name: str | int | None = Field(default=None, alias="providerName")
    success_rate: float | None = Field(default=None, alias="successRate")


class SuccessRateSearchBody(BaseModel):
    """Paginated admin success-rate search response."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    result: KycResult | None = None
    rates: list[SuccessRateHistoryItem] | None = None
    total_elements: int | None = Field(default=None, alias="totalElements")
    total_pages: int | None = Field(default=None, alias="totalPages")


def parse_route_body(body: Any) -> RouteBody | KycResultBody | Any:
    """Parse route JSON into a typed body."""
    if not isinstance(body, dict):
        return body
    if "provider" in body or isinstance(body.get("result"), dict):
        try:
            return RouteBody.model_validate(body)
        except ValidationError as exc:
            logger.debug("route body did not match RouteBody: %s", exc)
    return parse_result_body(body) or body


def parse_inquiry_body(body: Any) -> InquiryBody | KycResultBody | Any:
    """Parse inquiry JSON into a typed body."""
    if not isinstance(body, dict):
        return body
    if "promissoryNotes" in body:
        try:
            return InquiryBody.model_validate(body)
        except ValidationError as exc:
            logger.debug("inquiry body did not match InquiryBody: %s", exc)
    return parse_result_body(body) or body


def parse_settings_body(body: Any) -> ProviderSettingsBody | KycResultBody | Any:
    """Parse admin settings/provider JSON."""
    if not isinstance(body, dict):
        return body
    if "settingDetail" in body:
        try:
            return ProviderSettingsBody.model_validate(body)
        except ValidationError as exc:
            logger.debug("settings body did not match ProviderSettingsBody: %s", exc)
    return parse_result_body(body) or body


def parse_result_or_raw(body: Any) -> KycResultBody | Any:
    """Parse result-only bodies (init / refund / cancel success or error)."""
    if not isinstance(body, dict):
        return body
    return parse_result_body(body) or body


def parse_settings_search_body(body: Any) -> SettingsSearchBody | KycResultBody | Any:
    """Parse admin settings search JSON."""
    if not isinstance(body, dict):
        return body
    if "recipientList" in body:
        try:
            return SettingsSearchBody.model_validate(body)
        except ValidationError as exc:
            logger.debug("settings search body mismatch: %s", exc)
    return parse_result_body(body) or body


def parse_success_rate_stat_body(
    body: Any,
) -> list[SuccessRateStatItem] | KycResultBody | Any:
    """Parse admin success-rate statistic list."""
    if isinstance(body, list):
        try:
            return [SuccessRateStatItem.model_validate(row) for row in body]
        except ValidationError as exc:
            logger.debug("success-rate stat list mismatch: %s", exc)
            return body
    return parse_result_or_raw(body)


def parse_success_rate_search_body(
    body: Any,
) -> SuccessRateSearchBody | KycResultBody | Any:
    """Parse paginated success-rate search JSON."""
    if not isinstance(body, dict):
        return body
    if "totalElements" in body or "rates" in body:
        try:
            return SuccessRateSearchBody.model_validate(body)
        except ValidationError as exc:
            logger.debug("success-rate search body mismatch: %s", exc)
    return parse_result_body(body) or body
