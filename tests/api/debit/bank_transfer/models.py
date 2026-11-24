"""Bank-transfer route / inquiry request and response models."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

logger = logging.getLogger(__name__)


class TransferRouteRequest(BaseModel):
    """POST /bank-transfer/transfer/route body.

    Essential fields: trackingCode, businessId, targetIban, amount, ownerName,
    description, preferredType, agenda.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    tracking_code: str = Field(alias="trackingCode")
    business_id: str = Field(alias="businessId")
    target_iban: str = Field(alias="targetIban")
    # DSH probes may send decimal / string amounts (status below 500).
    amount: int | float | str
    owner_name: str = Field(alias="ownerName")
    description: str
    preferred_type: str = Field(alias="preferredType")
    agenda: str

    def to_payload(self) -> dict[str, Any]:
        """Serialize for the route JSON body."""
        return self.model_dump(by_alias=True, exclude_none=True)


class TransferResult(BaseModel):
    """Nested ``result`` on bank-transfer responses."""

    model_config = ConfigDict(extra="ignore")

    title: str | None = None
    status: int | None = None
    message: str | None = None
    level: str | None = None


class TransferRouteBody(BaseModel):
    """Parsed route / inquiry success body (partial)."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    result: TransferResult | None = None
    tracking_code: str | None = Field(default=None, alias="trackingCode")
    client_code: str | None = Field(default=None, alias="clientCode")
    bank_code: str | None = Field(default=None, alias="bankCode")
    type: int | None = None
    fee: int | float | None = None
    # Route may use string lifecycle status; inquiry uses numeric enums.
    status: str | int | None = None
    transactions: list[Any] | None = None


def parse_transfer_body(body: Any) -> TransferRouteBody | dict[str, Any] | Any:
    """Parse route/inquiry JSON into ``TransferRouteBody`` when possible."""
    if not isinstance(body, dict):
        return body
    try:
        return TransferRouteBody.model_validate(body)
    except ValidationError as exc:
        logger.debug("transfer body mismatch: %s", exc)
        return body


class StatementPageBody(BaseModel):
    """Parsed GET/POST statement page (partial)."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    result: TransferResult | None = None
    statements: list[dict[str, Any]] | None = None
    items: list[dict[str, Any]] | None = None
    content: list[dict[str, Any]] | None = None


def parse_statement_body(body: Any) -> StatementPageBody | dict[str, Any] | Any:
    """Parse statement JSON into ``StatementPageBody`` when possible."""
    if not isinstance(body, dict):
        return body
    try:
        return StatementPageBody.model_validate(body)
    except ValidationError as exc:
        logger.debug("statement body mismatch: %s", exc)
        return body


class SchedulerTriggerBody(BaseModel):
    """Optional body on ACH test-hook triggers."""

    model_config = ConfigDict(extra="ignore")

    result: TransferResult | None = None


def parse_scheduler_body(body: Any) -> SchedulerTriggerBody | dict[str, Any] | Any:
    """Parse scheduler trigger JSON when shape matches."""
    if not isinstance(body, dict):
        return body
    try:
        return SchedulerTriggerBody.model_validate(body)
    except ValidationError as exc:
        logger.debug("scheduler body mismatch: %s", exc)
        return body


def result_title(body: Any) -> str | None:
    """``result.title`` from typed or raw body."""
    if isinstance(
        body, (TransferRouteBody, StatementPageBody, SchedulerTriggerBody)
    ) and body.result is not None:
        return body.result.title
    if isinstance(body, dict):
        result = body.get("result")
        if isinstance(result, dict):
            title = result.get("title")
            return title if isinstance(title, str) else None
    return None


class TransferDirectRouteRequest(BaseModel):
    """POST /bank-transfer/transfer/direct-route body (TREASURY agenda)."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    tracking_code: str = Field(alias="trackingCode")
    business_id: str = Field(alias="businessId")
    source_iban: str | None = Field(default=None, alias="sourceIban")
    target_iban: str = Field(alias="targetIban")
    amount: int | float | str
    owner_name: str = Field(alias="ownerName")
    description: str
    preferred_type: str = Field(alias="preferredType")
    agenda: int

    def to_payload(self) -> dict[str, Any]:
        """Serialize; omit sourceIban when None (missing-source negatives)."""
        return self.model_dump(by_alias=True, exclude_none=True)
