"""Platform utility billId / payId helpers (mirrors BillUtils + fake_bill_generator).

Checksum-valid pairs pass Platform local validation. They do **not** guarantee a
live provider debt — use only for validation / WireMock-paired tests unless the
pair is known to exist on UAT.
"""

from __future__ import annotations

# UtilityBillType codes embedded in billId (digit before check digit)
TYPE_CODES = {
    "WATER": "1",
    "ELECTRICITY": "2",
    "GAS": "3",
    "TELEPHONE": "4",
    "MUNICIPALITY": "6",
    "TAX": "8",
    "DRIVING_PENALTY": "9",
}


class BillIdService:
    """Generate and validate Platform-checksum bill/pay identifiers."""

    def check_digit(self, digits: str) -> int:
        """BillUtils.getUtilityBillCheckDigit — mod-11 style."""
        multiply = 2
        total = 0
        for ch in reversed(digits):
            total += int(ch) * multiply
            multiply = multiply + 1 if multiply < 7 else 2
        mod = total % 11
        if mod in (0, 1):
            return 0
        return 11 - mod

    def is_bill_id_valid(self, bill_id: str) -> bool:
        """Return True when ``bill_id`` digits include a valid check digit."""
        if len(bill_id) < 2 or not bill_id.isdigit():
            return False
        return self.check_digit(bill_id[:-1]) == int(bill_id[-1])

    def is_pay_id_valid(self, pay_id: str) -> bool:
        """Return True when ``pay_id`` digits include a valid check digit."""
        if len(pay_id) < 3 or not pay_id.isdigit():
            return False
        return self.check_digit(pay_id[:-2]) == int(pay_id[-2])

    def is_bill_pay_match(self, bill_id: str, pay_id: str) -> bool:
        """Return True when billId and payId match Platform's pairing check."""
        b = bill_id.lstrip("0") or "0"
        p = pay_id.lstrip("0") or "0"
        return self.check_digit(b + p[:-1]) == int(p[-1])

    def validate_pair(self, bill_id: str, pay_id: str) -> bool:
        """Return True when both ids and their pairing check digits are valid."""
        return (
            self.is_bill_id_valid(bill_id)
            and self.is_pay_id_valid(pay_id)
            and self.is_bill_pay_match(bill_id, pay_id)
        )

    def amount_from_pay_id(self, pay_id: str) -> int:
        """BillUtils.fetchAmountFromPayId — strip last 5 chars, append 000."""
        if len(pay_id) < 5:
            return 0
        return int(pay_id[:-5] + "000")

    def make_bill_id(self, account_digits: str, type_code: str) -> str:
        """Build a checksum-valid billId (length 6..13)."""
        body = account_digits + type_code
        bill_id = body + str(self.check_digit(body))
        if not (6 <= len(bill_id) <= 13):
            raise ValueError(f"billId length {len(bill_id)} not in 6..13: {bill_id}")
        return bill_id

    def make_pay_id(self, bill_id: str, amount_rials: int, period: str = "011") -> str:
        """Build a checksum-valid payId for ``bill_id`` and ``amount_rials``."""
        if amount_rials < 1000:
            raise ValueError("amount_rials should be >= 1000 (Platform min pay is 10001)")
        amount_text = str(amount_rials)
        if len(period) != 3 or not period.isdigit():
            raise ValueError("period must be 3 digits")
        content = amount_text[:-3] + period
        content = content + str(self.check_digit(content))
        pay_id = content + str(self.check_digit(bill_id + content))
        if not (6 <= len(pay_id) <= 13):
            raise ValueError(f"payId length {len(pay_id)} not in 6..13: {pay_id}")
        return pay_id

    def make_pair(
        self,
        account_digits: str,
        type_name: str,
        amount_rials: int,
    ) -> tuple[str, str, int]:
        """Generate a validated (billId, payId, amountFromPayId) triple."""
        type_code = TYPE_CODES[type_name.upper()]
        bill_id = self.make_bill_id(account_digits, type_code)
        pay_id = self.make_pay_id(bill_id, amount_rials)
        if not self.validate_pair(bill_id, pay_id):
            raise RuntimeError("generated pair failed validation — bug in BillIdService")
        return bill_id, pay_id, self.amount_from_pay_id(pay_id)

    def broken_checksum_pair(
        self,
        account_digits: str = "12345678901",
        type_name: str = "WATER",
        amount_rials: int = 25000,
    ) -> tuple[str, str]:
        """Checksum-valid payId with a deliberately broken billId check digit."""
        bill_id, pay_id, _ = self.make_pair(account_digits, type_name, amount_rials)
        flipped = str((int(bill_id[-1]) + 1) % 10)
        if flipped == bill_id[-1]:
            flipped = "1" if bill_id[-1] != "1" else "2"
        broken_bill = bill_id[:-1] + flipped
        return broken_bill, pay_id
