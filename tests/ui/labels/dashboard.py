"""English → Farsi UI copy for Platform management console (dashboard)."""

from __future__ import annotations


class DashboardLabels:
    """Exact Farsi strings from UAT dashboard chrome — preserve ZWNJ."""

    LOGIN_SUBMIT = "ورود"

    SETTINGS = "تنظیمات"
    SUPER_APP = "سوپر اپ"
    SUPER_APP_LIST = "لیست سوپر اپ"
    OPERATIONAL_DASHBOARD = "داشبورد عملیاتی"
    # ZWNJ (U+200C) between ی and پ — matches live DOM.
    PLATFORM_SERVICES = "خدمات کمپانی‌پی"

    BILL_INQUIRY = "استعلام قبض"
    SELECT_BILL_TYPE = "انتخاب نوع قبض"
    CLOSE = "بستن"
    BACK = "بازگشت"
    CONFIRM_UPDATE = "ثبت و بروزرسانی"
    SUCCESS_TOAST = "عملیات با موفقیت انجام شد"
    SERVICE_DISTRIBUTION = "تنظیم تقسیم سرویس"

    ELECTRICITY = "برق"
    GAS = "گاز"
    TAX = "مالیات"
    MTN_MOBILE = "موبایل ایرانسل"
    LANDLINE = "تلفن ثابت"
    MCI_MOBILE = "موبایل همراه اول"
    WATER = "آب"
    MUNICIPALITY = "شهرداری"
    RIGHTEL_MOBILE = "موبایل رایتل"
    DRIVING_PENALTY = "جریمه راهنمایی و رانندگی"

    ELECTRICITY_INQUIRY = "استعلام برق"
    LANDLINE_INQUIRY = "استعلام تلفن ثابت"

    FINNOTECH = "فینوتک"
    GHABZINO = "قبضینو"
    TCI = "مخابرات"

    # Topup / IPKG (Super App)
    INTERNET_PACKAGE = "بسته اینترنت"
    TOPUP = "شارژ"
    SELECT_OPERATOR = "انتخاب اپراتور"
    # ZWNJ variants match live dashboard tiles/titles.
    OPERATOR_MCI = "همراه‌اول"
    OPERATOR_MTN = "ایرانسل"
    OPERATOR_RIGHTEL = "رایتل"
    OPERATOR_SHATEL = "شاتل"

    PROVIDER_ENIAC = "انیاک جدید"
    PROVIDER_RAYAN_MEHR = "رایان مهر"
    PROVIDER_JIRING = "جیرینگ"
    PROVIDER_BEHSA = "بهسا"

    INTERNET_MCI_DISTRIBUTION = "بسته اینترنت همراه‌اول"
    TOPUP_MCI_DISTRIBUTION = "شارژ همراه‌اول"


# Ordered bill-type tiles on the bill inquiry picker (UAT).
BILL_TYPE_TILES: tuple[str, ...] = (
    DashboardLabels.ELECTRICITY,
    DashboardLabels.GAS,
    DashboardLabels.TAX,
    DashboardLabels.MTN_MOBILE,
    DashboardLabels.LANDLINE,
    DashboardLabels.MCI_MOBILE,
    DashboardLabels.WATER,
    DashboardLabels.MUNICIPALITY,
    DashboardLabels.RIGHTEL_MOBILE,
    DashboardLabels.DRIVING_PENALTY,
)

# Gherkin / Outline English keys → Farsi UI labels.
BILL_TYPE_KEYS: dict[str, str] = {
    "electricity": DashboardLabels.ELECTRICITY,
    "gas": DashboardLabels.GAS,
    "tax": DashboardLabels.TAX,
    "mtn mobile": DashboardLabels.MTN_MOBILE,
    "landline": DashboardLabels.LANDLINE,
    "mci mobile": DashboardLabels.MCI_MOBILE,
    "water": DashboardLabels.WATER,
    "municipality": DashboardLabels.MUNICIPALITY,
    "rightel mobile": DashboardLabels.RIGHTEL_MOBILE,
    "driving penalty": DashboardLabels.DRIVING_PENALTY,
}

# Dialog titles (استعلام …) — not the picker tile keys in BILL_TYPE_KEYS.
DISTRIBUTION_TITLE_KEYS: dict[str, str] = {
    "electricity inquiry": DashboardLabels.ELECTRICITY_INQUIRY,
    "landline inquiry": DashboardLabels.LANDLINE_INQUIRY,
}

PROVIDER_KEYS: dict[str, str] = {
    "finnotech": DashboardLabels.FINNOTECH,
    "ghabzino": DashboardLabels.GHABZINO,
    "tci": DashboardLabels.TCI,
    "eniac": DashboardLabels.PROVIDER_ENIAC,
    "rayan mehr": DashboardLabels.PROVIDER_RAYAN_MEHR,
    "jiring": DashboardLabels.PROVIDER_JIRING,
    "behsa": DashboardLabels.PROVIDER_BEHSA,
}

PRODUCT_KEYS: dict[str, str] = {
    "internet package": DashboardLabels.INTERNET_PACKAGE,
    "topup": DashboardLabels.TOPUP,
}

OPERATOR_KEYS: dict[str, str] = {
    "mci": DashboardLabels.OPERATOR_MCI,
    "mtn": DashboardLabels.OPERATOR_MTN,
    "rightel": DashboardLabels.OPERATOR_RIGHTEL,
    "shatel": DashboardLabels.OPERATOR_SHATEL,
}

OPERATOR_TILES_INTERNET: tuple[str, ...] = (
    DashboardLabels.OPERATOR_MCI,
    DashboardLabels.OPERATOR_MTN,
    DashboardLabels.OPERATOR_RIGHTEL,
    DashboardLabels.OPERATOR_SHATEL,
)

OPERATOR_TILES_TOPUP: tuple[str, ...] = (
    DashboardLabels.OPERATOR_MCI,
    DashboardLabels.OPERATOR_MTN,
    DashboardLabels.OPERATOR_RIGHTEL,
)

# Dialog title for product + operator (MCI first).
DISTRIBUTION_TITLE_PRODUCT_KEYS: dict[str, str] = {
    "internet package mci": DashboardLabels.INTERNET_MCI_DISTRIBUTION,
    "topup mci": DashboardLabels.TOPUP_MCI_DISTRIBUTION,
}

# API product path segments.
PRODUCT_API_KEYS: dict[str, str] = {
    "internet package": "internet",
    "topup": "sim-card",
}

# MCI internet UI order → provider ids.
MCI_INTERNET_PROVIDERS: tuple[int, ...] = (4, 2, 3, 5)


def resolve_label(mapping: dict[str, str], key: str, *, kind: str) -> str:
    """Map an English Gherkin key to Farsi UI copy."""
    normalized = key.strip().lower()
    try:
        return mapping[normalized]
    except KeyError as exc:
        known = ", ".join(sorted(mapping))
        raise KeyError(f"Unknown {kind} key {key!r}. Known: {known}") from exc
