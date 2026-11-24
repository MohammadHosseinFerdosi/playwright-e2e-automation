"""Curated landline / TCI bill pool (Option E) — gitignored YAML.

Load real phones and TCI credentials for UAT automation. Missing or incomplete
cases should ``pytest.skip`` rather than fail CI when secrets are absent.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from pydantic import BaseModel, ConfigDict, Field

from tests.config.settings import REPO_ROOT, Settings

if TYPE_CHECKING:
    from tests.api.tci.client import TciClient


class TciCredentials(BaseModel):
    """TCI DigiPort / Platform proxy credentials."""

    model_config = ConfigDict(extra="ignore")

    base_url: str = "https://bill.demo-platform.com/tci/"
    code: str
    password: CHANGE_ME


_CASES_NEEDING_INQUIRY_ID = frozenset(
    {
        "with_debt",
        "no_debt",
        "province_blocked",
        "both_terms_debt",
        "mid_only_debt",
        "both_terms_debt_region",
        "invalid_phone",
    }
)
_CASES_NEEDING_TEL_OR_INQUIRY = frozenset({"with_debt", "no_debt", "province_blocked", "invalid"})


class TelephoneCase(BaseModel):
    """One curated landline fixture for Platform and/or TCI."""

    model_config = ConfigDict(extra="ignore")

    mode: str
    inquiry_id: str | None = None
    tel_number: str | None = None
    expected_tel_status: int | None = None
    bill_id: str | None = None
    pay_id: str | None = None
    notes: str | None = None

    def require_inquiry_id(self) -> str:
        """Return ``inquiry_id`` or skip when the pool case has none."""
        if not self.inquiry_id:
            pytest.skip("Pool case has no inquiry_id for landline inquiry")
        return self.inquiry_id

    def require_tel_number(self) -> str:
        """Return ``tel_number`` or skip when the pool case has none."""
        if not self.tel_number:
            pytest.skip("Pool case has no tel_number for TCI")
        return self.tel_number


class TelephoneBillPool(BaseModel):
    """Typed view of ``secrets/uat_telephone_bills.yaml``."""

    model_config = ConfigDict(extra="ignore")

    tci: TciCredentials | None = None
    cases: dict[str, TelephoneCase] = Field(default_factory=dict)

    def has_case(self, name: str) -> bool:
        """Return True when ``name`` exists in the loaded pool."""
        return name in self.cases

    def require_case(self, name: str) -> TelephoneCase:
        """Return the named case or skip when it is missing from the YAML pool."""
        case = self.cases.get(name)
        if case is None:
            pytest.skip(
                f"Telephone pool case {name!r} missing — copy "
                f"secrets/uat_telephone_bills.example.yaml to "
                f"secrets/uat_telephone_bills.yaml and fill values"
            )
        return case

    def require_prepared_case(self, name: str) -> TelephoneCase:
        """Load a pool case and skip when required fields for that scenario are absent."""
        case = self.require_case(name)
        if name in _CASES_NEEDING_INQUIRY_ID and not case.inquiry_id:
            pytest.skip(f"Pool case {name!r} has no inquiry_id")
        if name in _CASES_NEEDING_TEL_OR_INQUIRY and not (case.tel_number or case.inquiry_id):
            pytest.skip(f"Pool case {name!r} incomplete")
        return case

    def require_tci(self) -> TciCredentials:
        """Return TCI credentials or skip when missing / still CHANGE_ME."""
        if self.tci is None or not self.tci.password or self.tci.password == "CHANGE_ME":
            pytest.skip(
                "TCI credentials missing or still CHANGE_ME in secrets/uat_telephone_bills.yaml"
            )
        return self.tci


def require_tci_client(client: TciClient | None) -> TciClient:
    """Return a live ``TciClient`` or skip when the fixture yielded ``None``."""
    if client is None:
        pytest.skip("TCI client not available")
    return client


def load_telephone_bill_pool(settings: Settings) -> TelephoneBillPool:
    """Load pool from Settings path; empty pool if file is absent."""
    path = Path(settings.telephone_bills_secrets_path)
    if not path.is_absolute():
        path = REPO_ROOT / path
    if not path.is_file():
        return TelephoneBillPool()
    raw: Any = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        return TelephoneBillPool()
    return TelephoneBillPool.model_validate(raw)
