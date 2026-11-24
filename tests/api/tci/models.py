"""Pydantic models for Platform TCI proxy (bill.demo-platform.com/tci/)."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TciCredentialBody(BaseModel):
    """TCI proxy credentials (``code`` + ``password``)."""

    model_config = ConfigDict(extra="ignore")

    code: str
    password: str


class TciParameter(BaseModel):
    """One ``parameters[]`` entry on a TCI service request."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    parameter_name: str = Field(alias="parameterName")
    parameter_value: str = Field(alias="parameterValue")


class TciServiceRequest(BaseModel):
    """Outbound body for TCI inquiry / payment-register services."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    credential: TciCredentialBody
    parameters: list[TciParameter]
    service: str

    @classmethod
    def for_tel_inquiry(
        cls,
        *,
        code: str,
        password: str,
        tel_number: str,
        service: str,
    ) -> TciServiceRequest:
        """Build a telNumber inquiry request for the given TCI service name."""
        return cls(
            credential=TciCredentialBody(code=code, password=password),
            parameters=[
                TciParameter(parameterName="telNumber", parameterValue=tel_number),
            ],
            service=service,
        )


class TciStatus(BaseModel):
    """Status object embedded in some TCI ``responseText`` payloads."""

    model_config = ConfigDict(extra="ignore")

    code: int | None = None
    message: str | None = None


class TciBillData(BaseModel):
    """Inner bill fields (PDF ``result.data`` or flat ``responseText``)."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    tel_status: int | None = Field(default=None, alias="telStatus")
    service_status: str | None = Field(default=None, alias="serviceStatus")
    bill_id: str | int | None = Field(default=None, alias="billId")
    payment_id: str | int | None = Field(default=None, alias="paymentId")
    amount: int | float | None = None
    cycle_id: str | int | None = Field(default=None, alias="cycleId")
    message: str | None = None


class TciInnerPayload(BaseModel):
    """Parsed ``responseText`` — supports flat and ``result.data`` shapes."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    tel_status: int | None = Field(default=None, alias="telStatus")
    service_status: str | None = Field(default=None, alias="serviceStatus")
    bill_id: str | int | None = Field(default=None, alias="billId")
    payment_id: str | int | None = Field(default=None, alias="paymentId")
    amount: int | float | None = None
    cycle_id: str | int | None = Field(default=None, alias="cycleId")
    message: str | None = None
    status: TciStatus | None = None
    result: dict[str, Any] | None = None
    meta: dict[str, Any] | None = None

    def as_bill_data(self) -> TciBillData:
        """Normalize flat or nested ``result.data`` shapes into ``TciBillData``."""
        if self.tel_status is not None or self.bill_id is not None:
            return TciBillData.model_validate(
                {
                    "telStatus": self.tel_status,
                    "serviceStatus": self.service_status,
                    "billId": self.bill_id,
                    "paymentId": self.payment_id,
                    "amount": self.amount,
                    "cycleId": self.cycle_id,
                    "message": self.message,
                }
            )
        data = (self.result or {}).get("data") if isinstance(self.result, dict) else None
        if isinstance(data, dict):
            return TciBillData.model_validate(data)
        return TciBillData()


class TciProxyResponse(BaseModel):
    """Outer Platform TCI gateway envelope."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    is_successful: bool = Field(alias="isSuccessful")
    error: int = 0
    error_description: str | None = Field(default=None, alias="errorDescription")
    response_status_code: int | None = Field(default=None, alias="responseStatusCode")
    response_text: str | None = Field(default=None, alias="responseText")
    request_id: str | None = Field(default=None, alias="requestId")

    def parse_inner(self) -> TciInnerPayload:
        """Parse ``responseText`` JSON into ``TciInnerPayload``."""
        if not self.response_text:
            return TciInnerPayload()
        raw = json.loads(self.response_text)
        if not isinstance(raw, dict):
            return TciInnerPayload()
        return TciInnerPayload.model_validate(raw)

    def province_blocked(self) -> bool:
        """Return True when TCI reports the province is not allowed."""
        inner = self.parse_inner()
        status_msg = ""
        if inner.status is not None and inner.status.message:
            status_msg = inner.status.message
        msg = f"{inner.message or ''} {status_msg}"
        if inner.result and isinstance(inner.result.get("status"), dict):
            msg += " " + str(inner.result["status"].get("message") or "")
        return "province is not allowed" in msg.lower()


SERVICE_FINAL_TERM = "tci-end-getBillAccInfo"
SERVICE_MID_TERM = "tci-mid-getBillAccInfo"
