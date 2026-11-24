"""Shared KYC result / identity shapes."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class KycResult(BaseModel):
    """Shared KYC result envelope fields."""
    model_config = ConfigDict(extra="ignore")

    title: str
    status: int | None = None
    message: str | None = None
    level: str | None = None


class KycResultBody(BaseModel):
    """Body containing only a KYC result."""
    model_config = ConfigDict(extra="ignore")

    result: KycResult


class PersonName(BaseModel):
    """First/last name pair."""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    first_name: str = Field(alias="firstName")
    last_name: str = Field(alias="lastName")


class NationalCard(BaseModel):
    """National card code/serial pair."""
    model_config = ConfigDict(extra="ignore")

    code: str
    serial: str


def parse_result_body(body: Any) -> KycResultBody | None:
    """Parse a KYC result-only JSON body."""
    if isinstance(body, dict) and isinstance(body.get("result"), dict):
        return KycResultBody.model_validate(body)
    return None


def result_title(body: Any) -> str | None:
    """Return ``result.title`` from a parsed or raw KYC body."""
    result = getattr(body, "result", None)
    if result is not None:
        title = getattr(result, "title", None)
        return title if isinstance(title, str) else None
    if isinstance(body, dict):
        raw = body.get("result")
        if isinstance(raw, dict):
            title = raw.get("title")
            return title if isinstance(title, str) else None
    return None
