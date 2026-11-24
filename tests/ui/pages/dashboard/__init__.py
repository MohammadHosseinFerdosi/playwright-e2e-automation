"""Dashboard page objects."""

from tests.ui.pages.dashboard.bill_inquiry_modal import DashboardBillInquiryModal
from tests.ui.pages.dashboard.bill_provider_weights_modal import (
    DashboardBillProviderWeightsModal,
)
from tests.ui.pages.dashboard.home_page import DashboardHomePage
from tests.ui.pages.dashboard.login_page import DashboardLoginPage
from tests.ui.pages.dashboard.operator_picker_modal import DashboardOperatorPickerModal
from tests.ui.pages.dashboard.super_app_page import DashboardSuperAppPage
from tests.ui.pages.dashboard.topup_provider_weights_modal import (
    DashboardTopupProviderWeightsModal,
)

__all__ = [
    "DashboardBillInquiryModal",
    "DashboardBillProviderWeightsModal",
    "DashboardHomePage",
    "DashboardLoginPage",
    "DashboardOperatorPickerModal",
    "DashboardSuperAppPage",
    "DashboardTopupProviderWeightsModal",
]
