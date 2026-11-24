"""Assertion helpers for Platform landline UI (thin BDD steps call these)."""

from __future__ import annotations

from collections.abc import Callable
from urllib.parse import urlparse

from tests.config.settings import Settings
from tests.services.assert_report import AssertionReport
from tests.ui.pages.app.bill.bill_confirm_page import BillConfirmPage
from tests.ui.pages.app.bill.bill_services_page import BillServicesPage
from tests.ui.pages.app.bill.landline_inquiry_page import (
    LandlineInquiryPage,
    PaymentPeriod,
    PeriodDebtState,
)
from tests.ui.pages.app.hub_page import HubPage

LANDLINE_OPEN_PERIOD_STEP = r"^the customer opens the (?P<period>mid|final) payment period$"
LANDLINE_PERIOD_STATE_STEP = r"^the (?P<term>mid|final) period is (?P<state>payable|without debt)$"
OPEN_FROM_HUB_STEP = r"^the customer opens (?P<feature>[A-Za-z0-9 -]+) from the hub$"


def _url_matches_landing(
    actual_url: str, expected_url: str, path_fragment: str
) -> tuple[bool, bool]:
    actual = urlparse(actual_url)
    expected = urlparse(expected_url)
    host_ok = actual.netloc.lower() == expected.netloc.lower()
    actual_path = actual.path.rstrip("/") or "/"
    expected_path = (expected.path or path_fragment).rstrip("/") or "/"
    path_ok = actual_path == expected_path or path_fragment.rstrip("/") in actual_path
    return host_ok, path_ok


def _url_starts_with(actual_url: str, expected_prefix: str) -> bool:
    prefix = expected_prefix.rstrip("/")
    return (
        actual_url.rstrip("/").startswith(prefix)
        or actual_url.startswith(prefix + "/")
        or actual_url.startswith(prefix + "?")
    )


def assert_on_app_hub(hub_page: HubPage, settings: Settings) -> None:
    """Assert the browser landed on the configured Platform app hub."""
    hub_page.should_be_on_hub()
    actual_url = hub_page.current_url()
    expected_hub = settings.app_hub_url.rstrip("/")
    hub_path = (
        settings.hub_page_path
        if settings.hub_page_path.startswith("/")
        else f"/{settings.hub_page_path}"
    )
    host_ok, path_ok = _url_matches_landing(actual_url, settings.app_hub_url, hub_path)

    report = AssertionReport("App hub landing")
    report.note(f"expected hub URL={expected_hub!r}")
    report.note(f"actual URL={actual_url!r}")
    report.note(f"page title={hub_page.page_title()!r}")
    report.check("URL host matches configured hub", host_ok)
    report.check("URL path is hub", path_ok, detail=f"path={urlparse(actual_url).path!r}")
    report.check("URL starts with configured hub URL", _url_starts_with(actual_url, expected_hub))
    report.truthy("hub chrome visible", hub_page.is_hub_chrome_visible())
    report.assert_all()


def assert_on_bill_services(bill_services_page: BillServicesPage, settings: Settings) -> None:
    """Assert the browser landed on the bill services list page."""
    bill_services_page.should_be_on_bill_services()
    actual_url = bill_services_page.current_url()
    expected = f"{settings.app_base_url.rstrip('/')}{bill_services_page.PATH}"
    host_ok, path_ok = _url_matches_landing(actual_url, expected, bill_services_page.PATH)

    report = AssertionReport("Bill services landing")
    report.note(f"expected bill URL={expected!r}")
    report.note(f"actual URL={actual_url!r}")
    report.note(f"page title={bill_services_page.page_title()!r}")
    report.check("URL host matches app base", host_ok)
    report.check("URL path is /bill", path_ok)
    report.check("URL starts with configured bill URL", _url_starts_with(actual_url, expected))
    report.truthy("bill services chrome visible", bill_services_page.is_bill_chrome_visible())
    report.assert_all()


def assert_on_landline_inquiry(
    landline_inquiry_page: LandlineInquiryPage, settings: Settings
) -> None:
    """Assert the browser landed on the landline inquiry identifier page."""
    landline_inquiry_page.should_be_on_landline_inquiry()
    actual_url = landline_inquiry_page.current_url()
    expected_path = landline_inquiry_page.PATH
    expected = f"{settings.app_base_url.rstrip('/')}{expected_path}"
    bill_type = landline_inquiry_page.BILL_TYPE
    host_ok, path_ok = _url_matches_landing(actual_url, expected, expected_path)

    report = AssertionReport("Landline inquiry landing")
    report.note(f"BillType.{bill_type.name}={int(bill_type)}")
    report.note(f"expected URL={expected!r}")
    report.note(f"actual URL={actual_url!r}")
    report.note(f"page title={landline_inquiry_page.page_title()!r}")
    report.check("URL host matches app base", host_ok)
    report.check("URL path is TCI identifier route", path_ok)
    report.check(
        f"URL contains /bill/identifier/{int(bill_type)}",
        f"/bill/identifier/{int(bill_type)}" in actual_url,
    )
    report.check("URL starts with configured landline URL", _url_starts_with(actual_url, expected))
    report.truthy("landline inquiry form visible", landline_inquiry_page.is_inquiry_form_visible())
    report.assert_all()


def assert_payment_period_sheet(
    landline_inquiry_page: LandlineInquiryPage, inquiry_id: str
) -> None:
    """Assert the payment-period bottom sheet is visible for ``inquiry_id``."""
    landline_inquiry_page.wait_for_payment_period_sheet()
    report = AssertionReport("Payment period sheet")
    report.note(f"inquiry_id={inquiry_id!r}")
    report.truthy(
        "sheet title انتخاب دوره پرداخت",
        landline_inquiry_page.is_payment_period_sheet_visible(),
    )
    report.truthy(
        "mid period label", landline_inquiry_page.is_period_label_visible(PaymentPeriod.MID)
    )
    report.truthy(
        "final period label",
        landline_inquiry_page.is_period_label_visible(PaymentPeriod.FINAL),
    )
    report.truthy(
        "phone line برای شماره {inquiry_id}",
        landline_inquiry_page.is_phone_line_visible_for(inquiry_id),
    )
    report.assert_all()


def assert_period_debt_state(
    landline_inquiry_page: LandlineInquiryPage,
    period: PaymentPeriod | str,
    state: PeriodDebtState | str,
) -> None:
    """Assert a mid/final period row shows the expected payable/without-debt state."""
    period_key = (
        period if isinstance(period, PaymentPeriod) else PaymentPeriod(period.strip().lower())
    )
    state_key = (
        state if isinstance(state, PeriodDebtState) else PeriodDebtState(state.strip().lower())
    )
    label = landline_inquiry_page.period_label(period_key)
    report = AssertionReport(f"Period debt state — {label}")
    report.note(f"row text={landline_inquiry_page.period_row_text(period_key)!r}")
    report.note(f"row classes={landline_inquiry_page.period_row_classes(period_key)!r}")
    if state_key is PeriodDebtState.PAYABLE:
        report.check(
            f"{label} is clickable (cursor-pointer)",
            landline_inquiry_page.period_is_clickable(period_key),
        )
        report.check(
            f"{label} shows payable price",
            landline_inquiry_page.period_shows_payable(period_key),
            detail="expected ریال amount, not بدون بدهی / is-disabled",
        )
    else:
        report.check(
            f"{label} is disabled (is-disabled)",
            landline_inquiry_page.period_is_disabled(period_key),
        )
        report.check(
            f"{label} shows without debt",
            landline_inquiry_page.period_shows_without_debt(period_key),
            detail="expected بدون بدهی",
        )
        report.check(
            f"{label} is not clickable",
            not landline_inquiry_page.period_is_clickable(period_key),
        )
    report.assert_all()


def assert_period_not_actionable(
    landline_inquiry_page: LandlineInquiryPage, period: PaymentPeriod | str
) -> None:
    """Assert a period row is disabled and does not navigate to bill confirm."""
    period_key = (
        period if isinstance(period, PaymentPeriod) else PaymentPeriod(period.strip().lower())
    )
    label = landline_inquiry_page.period_label(period_key)
    report = AssertionReport(f"Period not actionable — {label}")
    report.note(f"row classes={landline_inquiry_page.period_row_classes(period_key)!r}")
    report.check(
        f"{label} is disabled (is-disabled)",
        landline_inquiry_page.period_is_disabled(period_key),
    )
    report.check(
        f"{label} shows without debt",
        landline_inquiry_page.period_shows_without_debt(period_key),
    )
    report.check(
        f"{label} is not clickable",
        not landline_inquiry_page.period_is_clickable(period_key),
    )
    report.check(
        f"{label} does not open bill confirm",
        landline_inquiry_page.period_does_not_navigate_to_confirm(period_key),
        detail=f"url={landline_inquiry_page.current_url()!r}",
    )
    report.assert_all()


def assert_no_payable_period_offered(landline_inquiry_page: LandlineInquiryPage) -> None:
    """Both periods without debt + disabled (ready for both-paid pool phone)."""
    report = AssertionReport("No payable payment period")
    if not landline_inquiry_page.is_payment_period_sheet_visible():
        landline_inquiry_page.wait_for_payment_period_sheet(timeout_ms=20_000)
    report.truthy("period sheet visible", landline_inquiry_page.is_payment_period_sheet_visible())
    for period in (PaymentPeriod.MID, PaymentPeriod.FINAL):
        label = landline_inquiry_page.period_label(period)
        report.note(f"{label} classes={landline_inquiry_page.period_row_classes(period)!r}")
        report.check(f"{label} is disabled", landline_inquiry_page.period_is_disabled(period))
        report.check(
            f"{label} shows without debt",
            landline_inquiry_page.period_shows_without_debt(period),
        )
        report.check(
            f"{label} is not clickable",
            not landline_inquiry_page.period_is_clickable(period),
        )
    report.check(
        "mid does not open confirm",
        landline_inquiry_page.period_does_not_navigate_to_confirm(PaymentPeriod.MID),
    )
    report.assert_all()


def assert_bill_confirm_details(bill_confirm_page: BillConfirmPage, settings: Settings) -> None:
    """Assert bill confirm shows billId/payId and payment amount chrome."""
    bill_confirm_page.should_be_on_confirm()
    actual_url = bill_confirm_page.current_url()
    report = AssertionReport("Bill confirm details")
    report.note(f"actual URL={actual_url!r}")
    report.note(f"page title={bill_confirm_page.page_title()!r}")
    report.check(
        "URL is bill confirm",
        bill_confirm_page.PATH in actual_url,
        detail=f"expected path containing {bill_confirm_page.PATH!r}",
    )
    report.check(
        "URL host matches app base",
        urlparse(actual_url).netloc.lower() == urlparse(settings.app_base_url).netloc.lower(),
    )
    report.truthy(
        "شناسه قبض and شناسه پرداخت visible", bill_confirm_page.is_bill_identity_visible()
    )
    report.truthy("مبلغ پرداختی / ریال visible", bill_confirm_page.is_payment_amount_visible())
    report.assert_all()


_HubOpen = Callable[
    [HubPage, BillServicesPage, LandlineInquiryPage, Settings],
    None,
]


def _open_landline_bill_inquiry(
    hub_page: HubPage,
    bill_services_page: BillServicesPage,
    landline_inquiry_page: LandlineInquiryPage,
    settings: Settings,
) -> None:
    assert_on_app_hub(hub_page, settings)
    hub_page.open_bill_payment()
    assert_on_bill_services(bill_services_page, settings)
    bill_services_page.open_landline_telephone()
    assert_on_landline_inquiry(landline_inquiry_page, settings)


_HUB_FEATURES: dict[str, _HubOpen] = {
    "landline bill inquiry": _open_landline_bill_inquiry,
}


def known_hub_features() -> list[str]:
    """Registered hub feature phrases, for the regex unit test to keep in sync."""
    return sorted(_HUB_FEATURES)


def open_from_hub(
    feature: str,
    hub_page: HubPage,
    bill_services_page: BillServicesPage,
    landline_inquiry_page: LandlineInquiryPage,
    settings: Settings,
) -> None:
    """Open one SuperApp hub destination from the captured Gherkin feature.

    Args:
        feature: Captured tail from ``OPEN_FROM_HUB_STEP``.
        hub_page: Customer hub page object.
        bill_services_page: Bill-services landing page.
        landline_inquiry_page: Landline inquiry form.
        settings: App URLs used by landing asserts.

    Raises:
        KeyError: If the feature has no registered opener.
    """
    opener = _HUB_FEATURES.get(feature)
    if opener is None:
        raise KeyError(f"No hub feature for {feature!r}; known: {known_hub_features()}")
    opener(hub_page, bill_services_page, landline_inquiry_page, settings)
