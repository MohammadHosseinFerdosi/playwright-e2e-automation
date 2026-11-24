"""Named ``parsers.re`` patterns that must equal the inline decorator strings.

Step files write the regex as ``r"..."`` on ``@given/@when/@then`` so humans and the
Gherkin plugin can see it. These constants feed unit tests;
``test_service_constants_match_inline_decorator_regexes`` fails if they drift.
"""

from __future__ import annotations

TELEPHONE_POOL_CASE_STEP = r'^the telephone bill pool has an? "(?P<case_name>[A-Za-z0-9_]+)" case$'

CASH_OUT_GATEWAY_STEP = r"^cash-out goes through (?P<gateway>[A-Za-z0-9 ]+)$"

NEMO_CUSTOMER_CAPABILITY_STEP = r"^a Nemo customer can (?P<capability>[A-Za-z0-9 -]+)$"

BILL_INQUIRY_REJECTED_STEP = r"^the bill inquiry is rejected as (?P<result_title>[A-Za-z0-9_]+)$"

BILL_PAYMENT_INIT_REJECTED_STEP = (
    r"^the bill payment init is rejected as (?P<result_title>[A-Za-z0-9_]+)$"
)

ADMIN_BILLS_CONFIG_REJECTED_STEP = (
    r"^the admin bills config update is rejected as (?P<result_title>[A-Za-z0-9_]+)$"
)
