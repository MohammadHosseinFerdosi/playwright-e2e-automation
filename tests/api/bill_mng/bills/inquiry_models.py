"""Pydantic request/response models for bill-mng inquiry."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from tests.api.bill_mng.bills.result import BillResult

TERM_TYPE_MID = 0
TERM_TYPE_FINAL = 1


class BillInquiryByInquiryIdRequest(BaseModel):
    """استعلام بدهی — ``payMethod: 3`` + type + inquiryId."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    pay_method: int = Field(default=3, alias="payMethod")
    type: int | None = None
    inquiry_id: str = Field(alias="inquiryId")

    def to_payload(self) -> dict[str, Any]:
        """Serialize to the bill-mng inquiry JSON body."""
        data = self.model_dump(by_alias=True, exclude_none=True)
        return data


class DefaultBillInquiryRequest(BaseModel):
    """پرداخت با شناسه — billId + payId."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    bill_id: str = Field(alias="billId")
    pay_id: str = Field(alias="payId")

    def to_payload(self) -> dict[str, Any]:
        """Serialize to the bill-mng inquiry JSON body."""
        return self.model_dump(by_alias=True)


class BillInfoDto(BaseModel):
    """One entry in ``billInfos`` from a successful inquiry."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    amount: int | None = None
    fee_charge: int | None = Field(default=None, alias="feeCharge")
    name: str | None = None
    bill_id: str | None = Field(default=None, alias="billId")
    pay_id: str | None = Field(default=None, alias="payId")
    bill_type: int | None = Field(default=None, alias="billType")
    term_type: int | None = Field(default=None, alias="termType")
    target_telephone: str | None = Field(default=None, alias="targetTelephone")
    tracking_code: str | None = Field(default=None, alias="trackingCode")


class BillInquiryBody(BaseModel):
    """Success (or result-bearing) inquiry response body."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    result: BillResult
    bill_infos: list[BillInfoDto] = Field(default_factory=list, alias="billInfos")
    bill_info: BillInfoDto | None = Field(default=None, alias="billInfo")

    def infos_by_term(self) -> dict[int, BillInfoDto]:
        """Map ``termType`` → first matching ``BillInfoDto`` (do not rely on list order)."""
        by_term: dict[int, BillInfoDto] = {}
        for info in self.bill_infos:
            if info.term_type is None:
                continue
            if info.term_type not in by_term:
                by_term[info.term_type] = info
        return by_term

    def term_types_present(self) -> set[int]:
        """Return the set of ``termType`` values present in ``billInfos``."""
        return {t for t in self.infos_by_term()}

    def payable_infos(self) -> list[BillInfoDto]:
        """Payable rows: amount > 0 with billId and payId."""
        return [i for i in self.bill_infos if i.bill_id and i.pay_id and (i.amount or 0) > 0]

    def payable_by_term(self) -> dict[int, BillInfoDto]:
        """Map payable ``termType`` → ``BillInfoDto`` (amount > 0 with ids)."""
        return {
            t: info
            for t, info in self.infos_by_term().items()
            if info.bill_id and info.pay_id and (info.amount or 0) > 0
        }
