"""Pydantic models for wallet create/charge/teardown orchestration."""

from __future__ import annotations

from pydantic import BaseModel, Field

from tests.config.constants import CURRENCY_IRR


class WalletChargeConfig(BaseModel):
    """One wallet create/charge instruction for ``create_user_with_charged_wallets``."""

    definition: str
    wallet_charge_amount: int = 0
    cashoutable_charge_amount: int = 0
    should_be_expired: bool = False


class BusinessWalletChargeConfig(BaseModel):
    """One business-wallet create/charge instruction.

    ``definition`` must be a business wallet name from CONSTANTS
    (e.g. ``refund``, ``spend``) — same rule as Robot.
    """

    definition: str
    wallet_charge_amount: int = 0
    currency: str = CURRENCY_IRR


class WalletInfo(BaseModel):
    """Snapshot of a single customer wallet after create/charge."""

    name: str
    type: str
    initial_amount: int = 0
    cashoutable_amount: int = 0
    expired: bool = False
    expires_at_epoch: float | None = None


class BusinessWalletInfo(BaseModel):
    """Snapshot of a single business wallet after create/charge."""

    name: str
    initial_amount: int = 0
    currency: str = CURRENCY_IRR


class ChargedUser(BaseModel):
    """Customer with charged wallets registered for teardown."""

    user_id: str
    user_cell_number: str
    user_national_code: str = ""
    access_token: str = ""
    wallets: list[WalletInfo] = Field(default_factory=list)
    total_initial_amount: int = 0


class ChargedBusiness(BaseModel):
    """Business with charged wallets registered for teardown."""

    business_id: str
    business_name: str
    user_name: str
    password: CHANGE_ME
    wallets: list[BusinessWalletInfo] = Field(default_factory=list)
