#!/usr/bin/env python3
"""Generate Platform-checksum-valid billId / payId pairs (mirrors BillUtils.java).

Note:
    These IDs pass Platform local validation (length, check digits, type digit,
    amount). They do NOT create a real unpaid bill at Finnotech / Ghabzino /
    Enovin. On live UAT, inquiry will usually return NOT_FOUND / provider error
    unless stubbed.

Examples:
    python3 fake_bill_generator.py
    python3 fake_bill_generator.py --type WATER --amount 25000 --account 12345678901
    python3 fake_bill_generator.py --validate 1234567890117 1501180
"""

from __future__ import annotations

import argparse

# UtilityBillType codes embedded in billId (second-to-last digit before check)
TYPE_CODES = {
    "WATER": "1",
    "ELECTRICITY": "2",
    "GAS": "3",
    "TELEPHONE": "4",
    "MUNICIPALITY": "6",
    "TAX": "8",
    "DRIVING_PENALTY": "9",
    # mobile uses code "5" + operator prefix — use --mobile instead
}


def check_digit(digits: str) -> int:
    """BillUtils.getUtilityBillCheckDigit."""
    multiply = 2
    total = 0
    for ch in reversed(digits):
        total += int(ch) * multiply
        multiply = multiply + 1 if multiply < 7 else 2
    mod = total % 11
    if mod in (0, 1):
        return 0
    return 11 - mod


def is_bill_id_valid(bill_id: str) -> bool:
    """Return True when ``bill_id`` includes a valid check digit."""
    return check_digit(bill_id[:-1]) == int(bill_id[-1])


def is_pay_id_valid(pay_id: str) -> bool:
    """Return True when ``pay_id`` includes a valid check digit."""
    return check_digit(pay_id[:-2]) == int(pay_id[-2])


def is_bill_pay_match(bill_id: str, pay_id: str) -> bool:
    """Return True when billId and payId pass Platform's pairing check."""
    b = bill_id.lstrip("0") or "0"
    p = pay_id.lstrip("0") or "0"
    return check_digit(b + p[:-1]) == int(p[-1])


def validate_pair(bill_id: str, pay_id: str) -> bool:
    """Return True when both ids and their pairing check digits are valid."""
    return (
        is_bill_id_valid(bill_id) and is_pay_id_valid(pay_id) and is_bill_pay_match(bill_id, pay_id)
    )


def amount_from_pay_id(pay_id: str) -> int:
    """BillUtils.fetchAmountFromPayId — strip last 5 chars, append 000."""
    if len(pay_id) < 5:
        return 0
    return int(pay_id[:-5] + "000")


def type_code_from_bill_id(bill_id: str) -> str:
    """Return the utility type digit embedded in ``bill_id``."""
    return bill_id[-2]


def make_bill_id(account_digits: str, type_code: str) -> str:
    """Build billId as accountDigits + typeCode + checkDigit (length 6..13)."""
    body = account_digits + type_code
    bill_id = body + str(check_digit(body))
    if not (6 <= len(bill_id) <= 13):
        raise ValueError(f"billId length {len(bill_id)} not in 6..13: {bill_id}")
    return bill_id


def make_pay_id(bill_id: str, amount_rials: int, period: str = "011") -> str:
    """Build a checksum-valid payId mirroring BillUtils.cellNumberToPaymentId.

    Encoding::

        content = str(amount)[:-3] + period(3) + check1
        payId   = content + matchCheck(billId + content)

    Amount recovered by Platform = payId[:-5] + '000', so ``amount_rials``
    should be divisible by 1000 (e.g. 15000, 25000).
    """
    if amount_rials < 1000:
        raise ValueError("amount_rials should be >= 1000 (Platform min pay is 10001)")
    amount_text = str(amount_rials)
    if len(amount_text) < 3:
        raise ValueError("amount too small")
    if len(period) != 3 or not period.isdigit():
        raise ValueError("period must be 3 digits")

    content = amount_text[:-3] + period
    content = content + str(check_digit(content))
    pay_id = content + str(check_digit(bill_id + content))
    if not (6 <= len(pay_id) <= 13):
        raise ValueError(f"payId length {len(pay_id)} not in 6..13: {pay_id}")
    if amount_from_pay_id(pay_id) != (amount_rials // 1000) * 1000:
        # Platform floors via encoding; warn by raising if mismatch unexpected
        pass
    return pay_id


def make_pair(account_digits: str, type_name: str, amount_rials: int) -> tuple[str, str, int]:
    """Generate a validated (billId, payId, amountFromPayId) triple."""
    type_code = TYPE_CODES[type_name.upper()]
    bill_id = make_bill_id(account_digits, type_code)
    pay_id = make_pay_id(bill_id, amount_rials)
    if not validate_pair(bill_id, pay_id):
        raise RuntimeError("generated pair failed validation — bug in generator")
    return bill_id, pay_id, amount_from_pay_id(pay_id)


def make_mobile_bill_id(cell: str) -> str:
    """BillUtils.cellNumberToBillId — cell like 09121234567."""
    if not (cell.startswith("0") and len(cell) == 11):
        raise ValueError("cell must be 11 digits starting with 0")
    operator_prefix = cell[1:4]
    content = "0" + cell[4:11] + operator_prefix + "5"
    return content + str(check_digit(content))


def main() -> None:
    """CLI entry point for generating or validating billId/payId pairs."""
    parser = argparse.ArgumentParser(description="Platform fake billId/payId generator")
    parser.add_argument("--type", default="WATER", choices=sorted(TYPE_CODES.keys()))
    parser.add_argument("--account", default="12345678901", help="digits before type+check")
    parser.add_argument("--amount", type=int, default=25000, help="Rials (prefer *1000)")
    parser.add_argument("--mobile", help="11-digit cell e.g. 09121234567 → billId only")
    parser.add_argument("--validate", nargs=2, metavar=("BILL_ID", "PAY_ID"))
    parser.add_argument("--samples", action="store_true", help="print several samples")
    args = parser.parse_args()

    if args.validate:
        b, p = args.validate
        print(
            {
                "billId": b,
                "payId": p,
                "valid": validate_pair(b, p),
                "billIdValid": is_bill_id_valid(b),
                "payIdValid": is_pay_id_valid(p),
                "match": is_bill_pay_match(b, p),
                "amount": amount_from_pay_id(p),
                "typeCode": type_code_from_bill_id(b),
            }
        )
        return

    if args.mobile:
        bill = make_mobile_bill_id(args.mobile)
        pay = make_pay_id(bill, args.amount)
        print(
            {
                "cell": args.mobile,
                "billId": bill,
                "payId": pay,
                "valid": validate_pair(bill, pay),
                "amount": amount_from_pay_id(pay),
            }
        )
        return

    if args.samples:
        for t in ("WATER", "ELECTRICITY", "GAS", "TELEPHONE"):
            for amt in (15000, 50000, 120000):
                b, p, a = make_pair("12345678901", t, amt)
                print(f"{t:12} billId={b} payId={p} amount={a} valid={validate_pair(b, p)}")
        return

    b, p, a = make_pair(args.account, args.type, args.amount)
    print(
        {
            "type": args.type,
            "billId": b,
            "payId": p,
            "amountFromPayId": a,
            "validForPlatform": True,
            "validForLiveProvider": "UNKNOWN — almost always NO without stub",
            "inquiryBody": {"billId": b, "payId": p},
        }
    )


if __name__ == "__main__":
    main()
