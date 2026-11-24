"""Typed access to ``data/CONSTANTS.yaml``.

Foundation fields are validated attributes; the full YAML is available via
``Constants.raw`` / ``Constants.get`` for domain-specific keys (LOS plan IDs,
LMS enums, etc.) without batch-porting every constant into Python.
"""

from __future__ import annotations

from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from tests.config.settings import REPO_ROOT

CONSTANTS_YAML = REPO_ROOT / "data" / "CONSTANTS.yaml"


class Constants(BaseModel):
    """Subset of CONSTANTS.yaml that the platform + wallet/payment/bill stack uses.

    Extra YAML keys are preserved in ``raw`` (and via ``get``) so domain teams
    can read LOS/LMS/etc. values without waiting for a typed field.
    """

    model_config = ConfigDict(extra="ignore", frozen=True)

    raw: Mapping[str, Any] = Field(exclude=True)

    api_success_state: str = Field(alias="API_SUCCESS_STATE")
    wallet_time_bound_definition: str = Field(alias="WALLET_TIME_BOUND_DEFINITION")
    wallet_default_definition: str = Field(alias="WALLET_DEFAULT_DEFINITION")
    currency_irr: str = Field(alias="CURRENCY_IRR")
    currency_crr: str = Field(alias="CURRENCY_CRR")
    customer_type: str = Field(alias="CUSTOMER_TYPE")
    business_type: str = Field(alias="BUSINESS_TYPE")

    b_wallet_spend_definition: str = Field(alias="B_WALLET_SPEND_DEFINITION")
    b_wallet_credit_spend_definition: str = Field(
        alias="B_WALLET_CREDIT_SPEND_DEFINITION"
    )
    b_wallet_refund_definition: str = Field(alias="B_WALLET_REFUND_DEFINITION")
    b_wallet_credit_refund_definition: str = Field(
        alias="B_WALLET_CREDIT_REFUND_DEFINITION"
    )
    b_wallet_reward_definition: str = Field(alias="B_WALLET_REWARD_DEFINITION")
    b_wallet_cashback_definition: str = Field(alias="B_WALLET_CASHBACK_DEFINITION")
    b_wallet_settlement_definition: str = Field(alias="B_WALLET_SETTLEMENT_DEFINITION")
    b_wallet_direct_debit_definition: str = Field(
        alias="B_WALLET_DIRECT_DEBIT_DEFINITION"
    )
    b_wallet_refund_manual_definition: str = Field(
        alias="B_WALLET_REFUND_MANUAL_DEFINITION"
    )
    b_wallet_refund_custom_definition: str = Field(
        alias="B_WALLET_REFUND_CUSTOM_DEFINITION"
    )
    b_wallet_settlement_fee_definition: str = Field(
        alias="B_WALLET_SETTLEMENT_FEE_DEFINITION"
    )
    b_wallet_debit_settlement_definition: str = Field(
        alias="B_WALLET_DEBIT_SETTLEMENT_DEFINITION"
    )
    b_wallet_credit_settlement_definition: str = Field(
        alias="B_WALLET_CREDIT_SETTLEMENT_DEFINITION"
    )

    upg_ticket_type: int = Field(alias="UPG_TICKET_TYPE")
    ipg_feature_name: int = Field(alias="IPG_FEATURE_NAME")
    dpg_feature_name: int = Field(alias="DPG_FEATURE_NAME")
    wallet_feature_name: int = Field(alias="WALLET_FEATURE_NAME")
    cpg_feature_name: int = Field(alias="CPG_FEATURE_NAME")
    bpg_feature_name: int = Field(alias="BPG_FEATURE_NAME")
    capg_feature_name: int = Field(alias="CAPG_FEATURE_NAME")
    ipg_cashin_feature_name: int = Field(alias="IPG_CASHIN_FEATURE_NAME")
    dpg_cashin_feature_name: int = Field(alias="DPG_CASHIN_FEATURE_NAME")
    credit_activation_name: int = Field(alias="CREDIT_ACTIVATION_NAME")
    purchase_transaction_type: int = Field(alias="PURCHASE_TRANSACTION_TYPE")
    ticket_landing_url: str = Field(alias="TICKET_LANDING_URL")
    test_callback_url: str = Field(alias="TEST_CALLBACK_URL")
    test_x_forwarded_for: str = Field(alias="TEST_X_FORWARDED_FOR")
    wallet_destination_type: str = Field(alias="WALLET_DESTINATION_TYPE")
    platform_version_2023: str = Field(alias="PLATFORM_VERSION_2023")

    android_agent: str = Field(alias="ANDROID_AGENT")
    web_agent: str = Field(alias="WEB_AGENT")
    hybrid_android_agent: str = Field(alias="HYBRID_ANDROID_AGENT")
    hybrid_ios_agent: str = Field(alias="HYBRID_IOS_AGENT")

    login_type_api: str = Field(alias="LOGIN_TYPE_API")
    login_type_app: str = Field(alias="LOGIN_TYPE_APP")

    def get(self, key: str, default: Any = None) -> Any:
        """Read any CONSTANTS.yaml key (including domain-only / untyped ones)."""
        return self.raw.get(key, default)

    def __getitem__(self, key: str) -> Any:
        try:
            return self.raw[key]
        except KeyError as exc:
            raise KeyError(key) from exc


@lru_cache(maxsize=1)
def load_constants(path: Path | None = None) -> Constants:
    """Load and cache CONSTANTS.yaml."""
    constants_path = path or CONSTANTS_YAML
    data = yaml.safe_load(constants_path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {constants_path}, got {type(data)}")
    return Constants.model_validate({**data, "raw": data})


# Module-level aliases matching Robot variable names (common imports).
_C = load_constants()

API_SUCCESS_STATE = _C.api_success_state
WALLET_TIME_BOUND_DEFINITION = _C.wallet_time_bound_definition
WALLET_DEFAULT_DEFINITION = _C.wallet_default_definition
CURRENCY_IRR = _C.currency_irr
CURRENCY_CRR = _C.currency_crr
CUSTOMER_TYPE = _C.customer_type
BUSINESS_TYPE = _C.business_type

B_WALLET_SPEND_DEFINITION = _C.b_wallet_spend_definition
B_WALLET_CREDIT_SPEND_DEFINITION = _C.b_wallet_credit_spend_definition
B_WALLET_REFUND_DEFINITION = _C.b_wallet_refund_definition
B_WALLET_CREDIT_REFUND_DEFINITION = _C.b_wallet_credit_refund_definition
B_WALLET_REWARD_DEFINITION = _C.b_wallet_reward_definition
B_WALLET_CASHBACK_DEFINITION = _C.b_wallet_cashback_definition
B_WALLET_SETTLEMENT_DEFINITION = _C.b_wallet_settlement_definition
B_WALLET_DIRECT_DEBIT_DEFINITION = _C.b_wallet_direct_debit_definition
B_WALLET_REFUND_MANUAL_DEFINITION = _C.b_wallet_refund_manual_definition
B_WALLET_REFUND_CUSTOM_DEFINITION = _C.b_wallet_refund_custom_definition
B_WALLET_SETTLEMENT_FEE_DEFINITION = _C.b_wallet_settlement_fee_definition
B_WALLET_DEBIT_SETTLEMENT_DEFINITION = _C.b_wallet_debit_settlement_definition
B_WALLET_CREDIT_SETTLEMENT_DEFINITION = _C.b_wallet_credit_settlement_definition

UPG_TICKET_TYPE = _C.upg_ticket_type
IPG_FEATURE_NAME = _C.ipg_feature_name
DPG_FEATURE_NAME = _C.dpg_feature_name
WALLET_FEATURE_NAME = _C.wallet_feature_name
CPG_FEATURE_NAME = _C.cpg_feature_name
BPG_FEATURE_NAME = _C.bpg_feature_name
CAPG_FEATURE_NAME = _C.capg_feature_name
IPG_CASHIN_FEATURE_NAME = _C.ipg_cashin_feature_name
DPG_CASHIN_FEATURE_NAME = _C.dpg_cashin_feature_name
CREDIT_ACTIVATION_NAME = _C.credit_activation_name
WALLET_DESTINATION_TYPE = _C.wallet_destination_type
PLATFORM_VERSION_2023 = _C.platform_version_2023
TEST_CALLBACK_URL = _C.test_callback_url
TEST_X_FORWARDED_FOR = _C.test_x_forwarded_for
TICKET_LANDING_URL = _C.ticket_landing_url
WEB_AGENT = _C.web_agent
ANDROID_AGENT = _C.android_agent
