"""Fixture helpers for Nemo cash-out BDD (keep step files thin)."""

from __future__ import annotations

from collections.abc import Generator

from tests.api.client import ApiClient
from tests.services.debit.nemo_cash_out import NemoCashOutFlow
from tests.services.debit.nemo_secrets import NemoSecrets, require_nemo_secrets
from tests.services.debit.nemo_wallet_db import NemoWalletDb


def load_nemo_secrets_or_skip() -> NemoSecrets:
    """Load secrets for fixtures."""
    return require_nemo_secrets()


def open_nemo_wallet(
    secrets: NemoSecrets,
) -> Generator[NemoWalletDb | None, None, None]:
    """Yield opened wallet_db when mongo_uri is filled; else None."""
    uri = (secrets.mongo_uri or "").strip()
    if not uri or "CHANGE_ME" in uri:
        yield None
        return
    wallet = NemoWalletDb(secrets)
    wallet.open()
    try:
        yield wallet
    finally:
        wallet.close()


def build_nemo_flow(
    client: ApiClient,
    secrets: NemoSecrets,
    wallet: NemoWalletDb | None,
) -> NemoCashOutFlow:
    """Construct flow for a scenario."""
    return NemoCashOutFlow(client, secrets, wallet)


def prepare_customer_capability(flow: NemoCashOutFlow, capability: str) -> None:
    """Set up predict vs register from one Gherkin capability phrase."""
    handlers = {
        "predict a cash-out fee": lambda: flow.assert_ready(),
        "register an IBAN cash-out": lambda: prepare_register(flow),
    }
    handler = handlers.get(capability)
    if handler is None:
        raise KeyError(f"No Nemo customer capability for {capability!r}; known: {sorted(handlers)}")
    handler()


def prepare_register(flow: NemoCashOutFlow) -> None:
    """API ready plus optional wallet cleanup before register."""
    flow.assert_ready()
    prepare_wallet_if_present(flow)


def prepare_wallet_if_present(flow: NemoCashOutFlow) -> None:
    """Close open settlements when Mongo is wired."""
    if flow.wallet is None:
        return
    flow.prepare_wallet()
