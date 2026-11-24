"""Load ``secrets/uat_bank_transfer.yaml`` (gitignored)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import BaseModel, ConfigDict

from tests.config.settings import REPO_ROOT

DEFAULT_SECRETS_PATH = REPO_ROOT / "secrets" / "uat_bank_transfer.yaml"


class BankTransferSecrets(BaseModel):
    """UAT secrets for debit bank-transfer gateway-common flows."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    user_id: str
    forwarded_for: str = "10.10.10.10"
    business_id: str = "business-test"
    agenda: str = "0"
    preferred_type: str = "0"
    marker_amount: int = 10001
    safe_amount: int = 1000

    mongo_uri: str
    mongo_db_name: str = "bank_transfer_db"
    routing_settle_seconds: float = 1.0

    test_gateway: str = "mellat"
    mellat_client_code: str = "bn_mellat"
    mellat_bank_code: str = "012"
    mellat_service_type: str = "INTERNAL_TRANSFER"
    mellat_target_iban: str
    mellat_owner_name: str = "qa test"
    mellat_account_number: str
    mellat_account_id: str = "accout_13"
    mellat_cross_bank_iban: str = "IR720560960180002115663001"
    melli_target_iban: str = "IR590170000000210581080009"
    parsian_target_iban: str = "IR550540109730102779329604"
    mellat_statement_reference_tc: str = ""
    manual_settled_tc: str = ""
    # TREASURY direct-route (API agenda=4).
    direct_route_agenda: int = 4
    melli_direct_source_iban: str = "IR380170000000118950253002"
    melli_direct_target_iban: str = "IR720560960180002115663001"
    melli_direct_account_number: str = "0118950253002"
    mellat_direct_source_iban: str = "IR810120020000008446431915"
    mellat_direct_target_iban: str = "IR720560960180002115663001"
    mellat_rtgs_target_iban: str = "IR730540109720101359685601"
    mellat_rtgs_min_amount: int = 1_000_000_000
    mellat_rtgs_probe_amount: int = 1_010_000_000
    mellat_rtgs_reference_tc: str = ""
    parsian_cross_bank_iban: str = "IR720560960180002115663001"
    parsian_account_number: str = "47001267216603"
    ft_shahin_account_number: str = "0221639012009"
    ft_shahin_internal_iban: str = "IR330190000000109099090004"
    ft_shahin_paya_source_iban: str = "IR950190000000221639012009"
    ft_shahin_paya_target_iban: str = "IR720560960180002115663001"
    ft_shahin_rtgs_target_iban: str = "IR730540109720101359685601"
    ft_shahin_rtgs_min_amount: int = 1_000_000_000
    ft_shahin_rtgs_probe_amount: int = 1_010_000_000
    ach_chunk: int = 10000
    ach_probe_amount: int = 10000
    allow_live_transfer: bool = False

    @property
    def shahin_target_iban(self) -> str:
        """Deprecated ``clientCode: shahin`` dest IBAN. Nemo still reads this name.

        Maps to the only Shahin product: ft_shahin same-bank dest.
        """
        return self.ft_shahin_internal_iban

    def require_ready(self) -> BankTransferSecrets:
        """Skip when placeholder values are still present."""
        for field_name, value in self.model_dump().items():
            if not isinstance(value, str):
                continue
            if "CHANGE_ME" in value or value.startswith("CHANGE"):
                pytest.skip(
                    f"Fill secrets/uat_bank_transfer.yaml "
                    f"(field {field_name!r} still looks like a placeholder)"
                )
        return self


def load_bank_transfer_secrets(
    path: Path | None = None,
) -> BankTransferSecrets | None:
    """Load secrets YAML if present."""
    target = path or DEFAULT_SECRETS_PATH
    if not target.is_file():
        return None
    raw: Any = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        return None
    return BankTransferSecrets.model_validate(raw)


def require_bank_transfer_secrets() -> BankTransferSecrets:
    """Load secrets or skip the test."""
    secrets = CHANGE_ME
    if secrets is None:
        pytest.skip(
            "Missing secrets/uat_bank_transfer.yaml — copy "
            "secrets/uat_bank_transfer.example.yaml and fill UAT values"
        )
    return secrets.require_ready()


def require_live_transfer(secrets: BankTransferSecrets) -> None:
    """Skip when live money transfers are not enabled in secrets."""
    if not secrets.allow_live_transfer:
        pytest.skip(
            "Live transfer settle disabled — set allow_live_transfer: true in "
            "secrets/uat_bank_transfer.yaml"
        )
