"""Native liveness request/response models."""

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


class RegisterLivenessRequest(BaseModel):
    """Native liveness register payload."""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    type: int
    name: PersonName
    english_name: PersonName = Field(alias="englishName")
    national_card: NationalCard = Field(alias="nationalCard")
    birth_date: str = Field(alias="birthDate")
    postal_code: str = Field(alias="postalCode")
    national_card_expiration_date: str = Field(alias="nationalCardExpirationDate")
    father_name: str = Field(alias="fatherName")
    address: str
    city: str
    province: str
    gender: int
    custom_video_text: str = Field(alias="customVideoText")

    def to_payload(self) -> dict[str, Any]:
        """Serialize for the liveness register JSON body."""
        return self.model_dump(by_alias=True, exclude_none=True)


class LivenessStatusBody(BaseModel):
    """Parsed liveness status response.

    Prefer ``livenessStatus``; some builds still return ``status``.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    liveness_status: int | None = Field(default=None, alias="livenessStatus")
    status: int | None = None
    result: KycResult | None = None

    @property
    def effective_status(self) -> int | None:
        """Prefer ``livenessStatus``; fall back to legacy ``status``."""
        if self.liveness_status is not None:
            return self.liveness_status
        return self.status


def parse_liveness_status_body(body: Any) -> LivenessStatusBody | KycResultBody | Any:
    """Parse a liveness status response body."""
    if not isinstance(body, dict):
        return body
    if "livenessStatus" in body or "status" in body:
        try:
            return LivenessStatusBody.model_validate(body)
        except ValidationError:
            pass
    return parse_result_body(body) or body


def parse_liveness_action_body(body: Any) -> KycResultBody | Any:
    """Parse a liveness action response body."""
    return parse_result_body(body) or body
