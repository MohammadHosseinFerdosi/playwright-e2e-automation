"""English → Farsi UI copy for Platform customer super-app chrome."""

from __future__ import annotations


class AppLabels:
    """Exact Farsi strings from UAT app chrome — preserve ZWNJ."""

    # Shared chrome / notices
    CLOSE = "بستن"
    CONTINUE = "ادامه"
    GOT_IT = "متوجه شدم"
    SERVICES = "خدمات"
    ALL_SERVICES = "همه خدمات"
    PAY = "پرداخت"
    WALLET = "کیف پول"
    RIAL = "ریال"

    # Auth / login onboarding
    ACCEPT_TERMS_CONTINUE = "قبول شرایط و ادامه"
    LOGIN_WELCOME = "خوش آمدید!"
    LOGIN_PHONE_INSTRUCTION = "جهت ورود، لطفا شماره موبایل خود را وارد کنید."
    MOBILE_NUMBER = "شماره موبایل"
    TERMS_OF_USE = "شرایط استفاده از کمپانی‌پی"
    HAVE_REFERRAL_CODE = "کد معرف دارید؟"
    REFERRAL_CODE = "کد معرف"
    ENTER_REFERRAL_CODE = "کد معرف خود را وارد کنید"
    CODE_PREVIEW = "کد"
    BACK = "بازگشت"
    TERMS_DOCUMENT_TITLE = "شرایط جامع استفاده از خدمات کمپانی‌پی"
    CONFIRM_AND_CONTINUE = "تایید و ادامه"
    ACTIVATION_CODE_SENT = "کد فعال‌سازی به شماره شما ارسال شد."

    # Hub service tiles (ZWNJ variants match live DOM)
    BUY_TOP_UP = "خرید شارژ"
    INTERNET_PACKAGE = "بسته اینترنت"
    CARD_TO_CARD = "کارت‌به‌کارت"
    BILL_PAYMENT = "پرداخت قبض"
    DRIVING_FINE_INQUIRY = "استعلام جریمه"
    ROAD_TOLL = "عوارض جاده‌ای"
    TAXI = "تاکسی"
    CHARITY = "خیریه"
    BARCODE_SCANNER = "بارکد‌خوان"

    # Bill services / confirm
    CHOOSE_BILL_TYPE_HINT = "نوع قبض را برای استعلام"
    TELECOM = "مخابرات"
    LANDLINE = "تلفن ثابت"
    BILL = "قبض"
    LANDLINE_BILL = "قبض تلفن ثابت"
    BILL_ID = "شناسه قبض"
    PAY_ID = "شناسه پرداخت"
    PAYMENT_AMOUNT = "مبلغ پرداختی"

    # Landline inquiry
    DEBT_INQUIRY = "استعلام بدهی"
    LANDLINE_NUMBER = "شماره تلفن ثابت"
    SAVE_AND_INQUIRE = "ذخیره و استعلام"
    SELECT_PAYMENT_PERIOD = "انتخاب دوره پرداخت"
    PERIOD_MID = "میان دوره"
    PERIOD_FINAL = "پایان دوره"
    WITHOUT_DEBT = "بدون بدهی"
    FOR_NUMBER_PREFIX = "برای شماره"

    # Wealth hub tab — verified against live UAT (bottom-nav "سرمایه" tab).
    WEALTH_TILE = "سرمایه"

    # Silver tab action row — verified against live UAT.
    TRANSACTIONS = "تراکنش‌ها"
    CONVERT = "تبدیل"
    REQUEST_CREDIT = "درخواست"
    SILVER_WEALTH_BAG = "نقره کیف ثروت"

    # Silver tab / mini-app tab labels — verified against live UAT.
    SILVER = "نقره"
    BUY = "خرید"
    SELL = "فروش"

    # Silver purchase — wallet-deposit / quick-payment / gateway / receipt flow.
    # Verified against live UAT with a pre-KYC'd, funded account (fresh accounts hit
    # the identity/BNPL gate above instead — see silver_page.py module docstring).
    WEALTH_AMOUNT_FIELD = "مبلغ مورد نظر"
    CONFIRM_AND_PAY = "تایید و پرداخت"
    GATEWAY_CANCEL = "انصراف"
    OPERATION_FAILED = "عملیات ناموفق"
    SILVER_PURCHASE_DESCRIPTION = BUY + " " + SILVER_WEALTH_BAG

    # Silver sale — wallet-withdraw / bank-account / confirmation / receipt flow.
    # Verified against live UAT with the same pre-KYC'd, funded account.
    CONFIRM_SALE = "تایید فروش"
    OPERATION_PENDING = "عملیات در انتظار"
