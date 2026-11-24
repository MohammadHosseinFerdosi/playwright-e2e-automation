"""Digital-signature request/response models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from tests.api.kyc.models import (
    KycResult,
    KycResultBody,
    NationalCard,
    PersonName,
    parse_result_body,
)


class InitiateBasicBody(BaseModel):
    """Parsed initiate/basic success body."""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    tracking_code: str = Field(alias="trackingCode")
    result: KycResult | None = None


class GenerateSignatureBody(BaseModel):
    """Parsed generate success body."""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    result: KycResult
    image_id: str | None = Field(default=None, alias="imageId")
    tracking_code: str | None = Field(default=None, alias="trackingCode")


class InitiateBasicRequest(BaseModel):
    """Initiate/basic request payload."""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    birth_date: str = Field(alias="birthDate")
    name: PersonName
    english_name: PersonName = Field(alias="englishName")
    national_card: NationalCard = Field(alias="nationalCard")
    postal_code: str = Field(alias="postalCode")
    type: int
    liveness_type: int = Field(alias="livenessType")
    gender: int
    password: str | None = None
    custom_video_text: str | None = Field(default=None, alias="customVideoText")

    def to_payload(self) -> dict[str, Any]:
        """Serialize for the initiate/basic JSON body."""
        return self.model_dump(by_alias=True, exclude_none=True)


class GenerateSignatureRequest(BaseModel):
    """Generate certificate request payload."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    password: str
    type: int
    provider_tracking_code: str = Field(alias="providerTrackingCode")

    def to_payload(self) -> dict[str, Any]:
        """Serialize for the generate JSON body."""
        return self.model_dump(by_alias=True, exclude_none=True)


def parse_initiate_body(body: Any) -> InitiateBasicBody | KycResultBody | Any:
    """Parse initiate/basic JSON into a typed body."""
    if not isinstance(body, dict):
        return body
    if "trackingCode" in body:
        try:
            return InitiateBasicBody.model_validate(body)
        except ValidationError:
            pass
    return parse_result_body(body) or body


def parse_generate_body(body: Any) -> GenerateSignatureBody | KycResultBody | Any:
    """Parse generate JSON into a typed body."""
    if not isinstance(body, dict):
        return body
    if isinstance(body.get("result"), dict) and (
        "trackingCode" in body or "imageId" in body
    ):
        try:
            return GenerateSignatureBody.model_validate(body)
        except ValidationError:
            pass
    return parse_result_body(body) or body
