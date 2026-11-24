"""Nemo cash-out request/response models."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

logger = logging.getLogger(__name__)


class TargetPan(BaseModel):
    """Card pan fragment for cash-out predict."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    value: str | None = None
    type: str = "1"
    expire_date: str = Field(default="1405/12", alias="expireDate")
    prefix: str = ""
    postfix: str = ""

    def to_payload(self) -> dict[str, Any]:
        """Serialize pan; omit value when None (missing-field probes)."""
        data = self.model_dump(by_alias=True, exclude_none=True)
        return data


class CashOutPredictRequest(BaseModel):
    """POST /wallets/cash-out/predict body."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    amount: int | float
    target_pan: TargetPan | None = Field(default=None, alias="targetPan")

    def to_payload(self) -> dict[str, Any]:
        """Serialize predict JSON."""
        payload: dict[str, Any] = {"amount": self.amount}
        if self.target_pan is not None:
            payload["targetPan"] = self.target_pan.to_payload()
        return payload


class CashOutRegisterRequest(BaseModel):
    """POST /wallets/cash-out/register body."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    amount: int
    iban: str | None = None
    birth_date: str | None = Field(default=None, alias="birthDate")

    def to_payload(self) -> dict[str, Any]:
        """Serialize register JSON; omit missing optional fields."""
        return self.model_dump(by_alias=True, exclude_none=True)


class TransferRoutePredictionRequest(BaseModel):
    """POST /nemo/transfer/route-prediction body.

    Essential fields: amount, agenda, targetIban.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    amount: int
    agenda: int
    target_iban: str = Field(alias="targetIban")

    def to_payload(self) -> dict[str, Any]:
        """Serialize for the app-gateway JSON body."""
        return self.model_dump(by_alias=True)


class TransferFeeRequest(BaseModel):
    """POST /nemo/transfer/fee body.

    Essential field: amount.
    """

    model_config = ConfigDict(extra="ignore")

    amount: int

    def to_payload(self) -> dict[str, Any]:
        """Serialize for the app-gateway JSON body."""
        return self.model_dump()


class NemoResult(BaseModel):
    """Nested ``result`` on Nemo responses."""

    model_config = ConfigDict(extra="ignore")

    title: str | None = None
    status: int | None = None
    message: str | None = None


class CashOutPredictBody(BaseModel):
    """Parsed predict success body (partial)."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    result: NemoResult | None = None
    fee: int | float | None = None


class CashOutRegisterBody(BaseModel):
    """Parsed register / detail body (partial)."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    result: NemoResult | None = None
    tracking_code: str | None = Field(default=None, alias="trackingCode")
    ticket: str | None = None
    status: str | int | None = None
    amount: int | None = None


class TransferGatewayBody(BaseModel):
    """Parsed app-gateway route-prediction / fee body."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    result: NemoResult | None = None
    client_code: str | None = Field(default=None, alias="clientCode")
    bank_code: str | None = Field(default=None, alias="bankCode")
    fee: int | float | None = None


def parse_predict_body(body: Any) -> CashOutPredictBody | dict[str, Any] | Any:
    """Parse predict JSON when shape matches."""
    if not isinstance(body, dict):
        return body
    try:
        return CashOutPredictBody.model_validate(body)
    except ValidationError as exc:
        logger.debug("predict body mismatch: %s", exc)
        return body


def parse_register_body(body: Any) -> CashOutRegisterBody | dict[str, Any] | Any:
    """Parse register/detail JSON when shape matches."""
    if not isinstance(body, dict):
        return body
    try:
        return CashOutRegisterBody.model_validate(body)
    except ValidationError as exc:
        logger.debug("register body mismatch: %s", exc)
        return body


def parse_gateway_body(body: Any) -> TransferGatewayBody | dict[str, Any] | Any:
    """Parse app-gateway JSON when shape matches."""
    if not isinstance(body, dict):
        return body
    try:
        return TransferGatewayBody.model_validate(body)
    except ValidationError as exc:
        logger.debug("gateway body mismatch: %s", exc)
        return body


def result_title(body: Any) -> str | None:
    """``result.title`` from typed or raw body."""
    if isinstance(
        body, (CashOutPredictBody, CashOutRegisterBody, TransferGatewayBody)
    ):
        if body.result is not None:
            return body.result.title
    if isinstance(body, dict):
        result = body.get("result")
        if isinstance(result, dict):
            title = result.get("title")
            return title if isinstance(title, str) else None
    return None


def tracking_code_from_body(body: Any) -> str | None:
    """TrackingCode or ticket from register response."""
    if isinstance(body, CashOutRegisterBody):
        for val in (body.tracking_code, body.ticket):
            if isinstance(val, str) and val.strip():
                return val.strip()
        return None
    if isinstance(body, dict):
        for key in ("trackingCode", "ticket"):
            val = body.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    return None
