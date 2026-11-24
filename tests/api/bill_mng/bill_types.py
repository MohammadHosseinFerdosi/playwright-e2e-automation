r"""Platform API ``BillType`` ints (JSON / UI ``/bill/identifier/{type}``).

Source: ``docs/bill-mng-sdet/BILL_AUTOMATION_GUIDANCE_BOOK.md`` §7.2.

Do **not** confuse with admin ``UtilityBillType`` path codes (WATER=\"1\", TELEPHONE=\"4\").
"""

from __future__ import annotations

from enum import Enum, IntEnum


class BillType(IntEnum):
    """API BillType used by bill-mng requests and app routes ``/bill/identifier/{n}``."""

    WATER = 4
    ELECTRICITY = 5
    GAS = 6
    TELEPHONE = 7  # TCI / مخابرات / تلفن ثابت
    MUNICIPALITY = 8
    TAX = 9
    DRIVING_PENALTY = 10
    MCI_MOBILE = 11
    MTN_MOBILE = 12
    RIGHTEL_MOBILE = 13

    @property
    def identifier_path(self) -> str:
        """App path after choosing a bill type on ``/bill``."""
        return f"/bill/identifier/{int(self)}"


class UtilityBillType(str, Enum):
    """Admin path ``{type}`` for ``PUT /admin/bills/configs/{type}`` (model codes)."""

    WATER = "1"
    ELECTRICITY = "2"
    GAS = "3"
    TELEPHONE = "4"
    MUNICIPALITY = "6"
    TAX = "8"
    DRIVING_PENALTY = "9"
    MCI_MOBILE = "15"
    MTN_MOBILE = "25"
    RIGHTEL_MOBILE = "35"


_BILL_TYPE_TO_UTILITY: dict[BillType, UtilityBillType] = {
    BillType.WATER: UtilityBillType.WATER,
    BillType.ELECTRICITY: UtilityBillType.ELECTRICITY,
    BillType.GAS: UtilityBillType.GAS,
    BillType.TELEPHONE: UtilityBillType.TELEPHONE,
    BillType.MUNICIPALITY: UtilityBillType.MUNICIPALITY,
    BillType.TAX: UtilityBillType.TAX,
    BillType.DRIVING_PENALTY: UtilityBillType.DRIVING_PENALTY,
    BillType.MCI_MOBILE: UtilityBillType.MCI_MOBILE,
    BillType.MTN_MOBILE: UtilityBillType.MTN_MOBILE,
    BillType.RIGHTEL_MOBILE: UtilityBillType.RIGHTEL_MOBILE,
}


def utility_bill_type_for(api_type: BillType) -> UtilityBillType:
    """Map GET ``configs[].type`` (API int) to admin PUT path code."""
    try:
        return _BILL_TYPE_TO_UTILITY[api_type]
    except KeyError as exc:
        raise KeyError(f"No UtilityBillType mapping for {api_type!r}") from exc


# Backward-compatible aliases used by Platform validate steps.
BILL_TYPE_WATER = int(BillType.WATER)
BILL_TYPE_TELEPHONE = int(BillType.TELEPHONE)
