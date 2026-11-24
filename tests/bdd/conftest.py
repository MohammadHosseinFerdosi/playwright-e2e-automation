"""BDD-layer fixtures (not pytest-bdd step definitions).

Step functions that must be shared across ``tests/bdd/steps/*.py`` stay in
``tests/bdd/steps/conftest.py`` — pytest-bdd only reuses steps from that file.
"""

from collections.abc import Generator

import pytest

from tests.api.client import ApiClient
from tests.services.debit.bank_transfer import BankTransferContext, BankTransferFlow
from tests.services.debit.bank_transfer_routing import BankTransferRoutingDb
from tests.services.debit.bank_transfer_secrets import require_bank_transfer_secrets


@pytest.fixture
def bt_flow(microservice_client: ApiClient) -> Generator[BankTransferFlow, None, None]:
    """Snapshot CASH_OUT weights; restore on teardown."""
    secrets = CHANGE_ME
    routing = BankTransferRoutingDb(secrets)
    flow = BankTransferFlow(microservice_client, routing, secrets)
    flow.prepare()
    yield flow
    flow.teardown()


@pytest.fixture
def bt_ctx(bt_flow: BankTransferFlow) -> BankTransferContext:
    """Per-scenario bank-transfer envelopes."""
    return BankTransferContext(secrets=bt_flow.secrets)
