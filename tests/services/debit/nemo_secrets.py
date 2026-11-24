"""Load ``secrets/uat_nemo.yaml`` (gitignored) for debit Nemo cash-out."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import BaseModel, ConfigDict

from tests.config.settings import REPO_ROOT

DEFAULT_SECRETS_PATH = REPO_ROOT / "secrets" / "uat_nemo.yaml"
UNKNOWN_USER = "09111111111"
NEGATIVE_INVALID_IBAN = "NOT-A-VALID-IBAN"
NEGATIVE_IBAN_SPACES = "IR82 0120 0200 0000 9734 0986 52"

REGISTER_KYC_BLOCK_TITLES = frozenset(
    {
        "FAILURE",
        "WALLET_CASH_OUT_KYC_REJECTED",
        "PEPE_CASHOUT_KYC_REQUIRED",
        "PEPE_CASHOUT_MULTIPLE_SETTLEMENT_NOT_ALLOWED",
        "PEPE_CASHOUT_WALLET_BALANCE_NOT_ENOUGH",
    }
)

PLATFORM_CLIENT_REJECT_TITLES = frozenset(
    {
        "INVALID_PARAMETER",
        "FAILURE",
        "BAD_REQUEST",
        "TRANSACTION_NOT_FOUND",
        "BANKPROXY_DUPLICATE_TRANSACTION",
        "BANKPROXY_NO_GATEWAY",
        "BANKPROXY_BANK_UNKNOWN_ERROR",
        "BANKPROXY_AMOUNT_INVALID",
        "BANKPROXY_CREDIT_NOT_ENOUGH",
        "UNKNOWN",
        "SECURE_STORE_GENERIC_ERROR",
        "USER_NOT_FOUND",
    }
)


class NemoSecrets(BaseModel):
    """UAT secrets for Nemo wallet cash-out predict/register."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    user_id: str
    forwarded_for: str = "10.10.10.10"
    birth_date: str = "1990-01-01T00:00:00.000Z"
    agent: str = "CONSOLE"
    safe_amount: int = 10000
    marker_amount: int = 10001
    min_cash_out_amount: int = 10000
    max_cash_out_amount: int = 200_000_000
    amount_below_min: int = 9999
    amount_above_max: int = 200_000_001

    pan_value: str = ""
    pan_type: str = "1"
    pan_prefix: str = ""
    pan_postfix: str = ""
    pan_expire: str = "1405/12"

    target_iban: str = ""
    mongo_uri: str = ""
    mongo_db_name: str = "wallet_db"

    allow_live_cash_out: bool = False
    skip_live_register: bool = False
    register_kyc_blocked: bool = False
    pin_code: str = ""
    cell_number: str = ""
    cashout_bt_reference_tc: str = ""
    transfer_agenda: int = 0

    def require_ready(self) -> NemoSecrets:
        """Skip when placeholder values are still present."""
        for field_name, value in self.model_dump().items():
            if not isinstance(value, str):
                continue
            if "CHANGE_ME" in value or value.startswith("CHANGE"):
                pytest.skip(
                    f"Fill secrets/uat_nemo.yaml "
                    f"(field {field_name!r} still looks like a placeholder)"
                )
        return self

    def configured_pan(self) -> dict[str, str]:
        """Build targetPan for predict; skip when card is not configured."""
        value = (self.pan_value or "").strip()
        prefix = (self.pan_prefix or "").strip()
        postfix = (self.pan_postfix or "").strip()
        if not prefix:
            if not value:
                pytest.skip(
                    "Set pan_value or pan_prefix+pan_postfix in secrets/uat_nemo.yaml"
                )
            prefix = value[:6]
        if not postfix:
            if not value:
                pytest.skip(
                    "Set pan_value or pan_prefix+pan_postfix in secrets/uat_nemo.yaml"
                )
            postfix = value[-4:]
        if not value:
            value = f"{prefix}******{postfix}"
        return {
            "value": value,
            "type": self.pan_type,
            "expireDate": self.pan_expire,
            "prefix": prefix,
            "postfix": postfix,
        }

    def require_target_iban(self) -> str:
        """User verified IBAN for register."""
        iban = (self.target_iban or "").strip()
        if not iban:
            pytest.skip("Set target_iban in secrets/uat_nemo.yaml")
        return iban


def load_nemo_secrets(path: Path | None = None) -> NemoSecrets | None:
    """Load secrets YAML if present."""
    target = path or DEFAULT_SECRETS_PATH
    if not target.is_file():
        return None
    raw: Any = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        return None
    return NemoSecrets.model_validate(raw)


def require_nemo_secrets() -> NemoSecrets:
    """Load secrets or skip the test."""
    secrets = load_nemo_secrets()
    if secrets is None:
        pytest.skip(
            "Missing secrets/uat_nemo.yaml — copy secrets/uat_nemo.example.yaml "
            "and fill UAT values"
        )
    return secrets.require_ready()


def require_nemo_pin(secrets: NemoSecrets) -> str:
    """Require app PIN for gateway Bearer login."""
    pin = (secrets.pin_code or "").strip()
    if not pin:
        pytest.skip("App-gateway smoke needs pin_code in secrets/uat_nemo.yaml")
    return pin


def require_live_cash_out(secrets: NemoSecrets) -> None:
    """Skip when live IBAN register settle is disabled."""
    if secrets.skip_live_register or secrets.register_kyc_blocked:
        pytest.skip(
            "Live Nemo register skipped — skip_live_register / register_kyc_blocked "
            "in secrets/uat_nemo.yaml"
        )
    if not secrets.allow_live_cash_out:
        pytest.skip(
            "Live cash-out register disabled — set allow_live_cash_out: true in "
            "secrets/uat_nemo.yaml"
        )
