"""Nemo app-gateway route-prediction + transfer fee orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from tests.api.client import ApiClient
from tests.api.debit.nemo.models import (
    TransferFeeRequest,
    TransferGatewayBody,
    TransferRoutePredictionRequest,
    result_title,
)
from tests.api.debit.nemo.transfer_gateway import (
    post_transfer_fee,
    post_transfer_route_prediction,
)
from tests.services.debit.bank_transfer import BankTransferFlow
from tests.services.debit.bank_transfer_routing import BankTransferRoutingDb
from tests.services.debit.bank_transfer_secrets import BankTransferSecrets
from tests.services.debit.nemo_app_auth import login_nemo_app_pin
from tests.services.debit.nemo_secrets import NemoSecrets

GATEWAY_EXPECT = {
    "mellat": ("bn_mellat", "012"),
    "shahin": ("shahin", "019"),
    "manual": ("bn_manual", "MANUAL"),
}

NEMO_CASH_OUT_THROUGH_STEP = (
    r"^the Nemo app will cash out through (?P<gateway>Mellat|Shahin|Manual)$"
)


@dataclass
class NemoGatewayContext:
    """Per-scenario gateway prediction / fee envelopes."""

    nemo: NemoSecrets
    bt: BankTransferSecrets
    last_result: dict[str, Any] = field(default_factory=dict)
    fee_result: dict[str, Any] = field(default_factory=dict)
    route_result: dict[str, Any] = field(default_factory=dict)
    flags: dict[str, Any] = field(default_factory=dict)


class NemoGatewayFlow:
    """Pin BT weights and call Nemo app-gateway transfer APIs."""

    def __init__(
        self,
        app_client: ApiClient,
        ms_client: ApiClient,
        nemo: NemoSecrets,
        bt: BankTransferSecrets,
        routing: BankTransferRoutingDb,
    ) -> None:
        self._app = app_client
        self._ms = ms_client
        self._nemo = nemo
        self._bt = bt
        self._routing = routing
        self._token: str | None = None
        self._weight_snapshot: list[dict[str, Any]] | None = None

    @property
    def nemo(self) -> NemoSecrets:
        """Nemo secrets."""
        return self._nemo

    @property
    def bt(self) -> BankTransferSecrets:
        """Bank-transfer secrets (IBANs / mongo)."""
        return self._bt

    def prepare(self) -> None:
        """Snapshot CASH_OUT weights."""
        self._routing.open()
        self._weight_snapshot = self._routing.snapshot_all_weights()

    def teardown(self) -> None:
        """Restore CASH_OUT weights and close Mongo."""
        try:
            if self._weight_snapshot is not None:
                self._routing.restore_all_weights(self._weight_snapshot)
        finally:
            self._weight_snapshot = None
            self._routing.close()

    def assert_ready(self) -> None:
        """Require PIN + routing snapshot."""
        _ = login_nemo_app_pin(self._app, self._nemo)
        if not self._weight_snapshot:
            raise RuntimeError("cash-out routing weights were not snapshotted")

    def access_token(self) -> str:
        """Cached app Bearer token."""
        if self._token is None:
            self._token = login_nemo_app_pin(self._app, self._nemo)
        return self._token

    def _target_iban(self, gateway: str) -> str:
        mapping = {
            "mellat": self._bt.mellat_target_iban,
            "shahin": self._bt.shahin_target_iban,
            "manual": self._bt.mellat_cross_bank_iban,
        }
        return mapping[gateway]

    def _pin(self, gateway: str) -> None:
        if gateway == "mellat":
            self._routing.pin_mellat_internal(100)
        elif gateway == "shahin":
            self._routing.pin_shahin_internal(100)
        elif gateway == "manual":
            self._routing.pin_manual_ach(100)
        else:
            raise KeyError(gateway)

    def pin_named_gateway(self, gateway: str) -> None:
        """Sign in if needed, then pin CASH_OUT routing from a Gherkin name."""
        self.assert_ready()
        self._routing.pin_named_gateway(gateway)

    def split_manual_mellat(self) -> None:
        """Manual 50 / Mellat 50 CASH_OUT weights."""
        self._routing.split_gateway_weights({"manual": 50, "mellat": 50})

    def predict_route(self, *, gateway: str, amount: int | None = None) -> dict[str, Any]:
        """Pin gateway and POST route-prediction."""
        self._pin(gateway)
        return self._post_predict(gateway, amount)

    def _post_predict(self, gateway: str, amount: int | None) -> dict[str, Any]:
        return post_transfer_route_prediction(
            self._app,
            TransferRoutePredictionRequest(
                amount=amount if amount is not None else self._nemo.marker_amount,
                agenda=self._nemo.transfer_agenda,
                targetIban=self._target_iban(gateway),
            ),
            access_token=self.access_token(),
            user_id=self._nemo.user_id,
            forwarded_for=self._nemo.forwarded_for,
        )

    def predict_split_manual_mellat(self) -> dict[str, Any]:
        """Manual 50 / mellat 50 prediction."""
        self._routing.split_gateway_weights({"manual": 50, "mellat": 50})
        return post_transfer_route_prediction(
            self._app,
            TransferRoutePredictionRequest(
                amount=self._nemo.marker_amount,
                agenda=self._nemo.transfer_agenda,
                targetIban=self._bt.mellat_cross_bank_iban,
            ),
            access_token=self.access_token(),
            user_id=self._nemo.user_id,
            forwarded_for=self._nemo.forwarded_for,
        )

    def transfer_fee(self) -> dict[str, Any]:
        """POST transfer fee."""
        return post_transfer_fee(
            self._app,
            TransferFeeRequest(amount=self._nemo.safe_amount),
            access_token=self.access_token(),
            user_id=self._nemo.user_id,
            forwarded_for=self._nemo.forwarded_for,
        )

    def bank_transfer_route_mellat(self) -> dict[str, Any]:
        """MS bank-transfer route after Nemo gateway prep."""
        self._routing.pin_mellat_internal(100)
        flow = BankTransferFlow(self._ms, self._routing, self._bt)
        tc = flow.new_tracking_code("NEMO", prefix="QA-NEMO")
        return flow.route(
            tc,
            amount=self._bt.safe_amount,
            iban=self._bt.mellat_target_iban,
            preferred_type="2",
            description=f"QA|NEMO|PREP|{tc}",
        )


def _as_dict(body: Any) -> dict[str, Any]:
    """Typed or raw JSON body as a dict."""
    if isinstance(body, TransferGatewayBody):
        return body.model_dump(by_alias=True)
    if isinstance(body, dict):
        return body
    return {}


def _client_code(body: Any) -> str | None:
    """``clientCode`` or nested ``client.code`` from a prediction body."""
    raw = _as_dict(body)
    code = raw.get("clientCode")
    if isinstance(code, str):
        return code
    client = raw.get("client")
    if isinstance(client, dict):
        nested = client.get("code")
        if isinstance(nested, str):
            return nested
    return None


def _bank_code(body: Any) -> str | None:
    """``bankCode`` from a prediction body."""
    val = _as_dict(body).get("bankCode")
    return val if isinstance(val, str) else None


def store_gateway_case(flow: NemoGatewayFlow, ctx: NemoGatewayContext, case: str) -> None:
    """Dispatch gateway When."""
    {
        "mellat pin prediction": lambda: _store_pin(flow, ctx, "mellat"),
        "shahin pin prediction": lambda: _store_pin(flow, ctx, "shahin"),
        "manual pin prediction": lambda: _store_pin(flow, ctx, "manual"),
        "manual mellat split prediction": lambda: _store_split(flow, ctx),
        "transfer route prediction": lambda: _store_route_ok(flow, ctx),
        "transfer fee": lambda: _store_fee(flow, ctx),
        "gateway prep then mellat route": lambda: _store_prep_route(flow, ctx),
    }[case]()


def _store_pin(flow: NemoGatewayFlow, ctx: NemoGatewayContext, gateway: str) -> None:
    result = flow.predict_route(gateway=gateway)
    body = result.get("body")
    exp_cc, exp_bc = GATEWAY_EXPECT[gateway]
    ctx.last_result = result
    ctx.flags = {
        "status_code": result.get("status_code"),
        "title": result_title(body),
        "client_code": _client_code(body),
        "bank_code": _bank_code(body),
        "expected_client_code": exp_cc,
        "expected_bank_code": exp_bc,
        "gateway": gateway,
    }


def _store_split(flow: NemoGatewayFlow, ctx: NemoGatewayContext) -> None:
    result = flow.predict_split_manual_mellat()
    body = result.get("body")
    ctx.last_result = result
    ctx.flags = {
        "status_code": result.get("status_code"),
        "title": result_title(body),
        "client_code": _client_code(body),
        "expected_client_code": "bn_manual",
    }


def _store_route_ok(flow: NemoGatewayFlow, ctx: NemoGatewayContext) -> None:
    _store_pin(flow, ctx, "mellat")


def _store_fee(flow: NemoGatewayFlow, ctx: NemoGatewayContext) -> None:
    result = flow.transfer_fee()
    ctx.fee_result = result
    ctx.last_result = result
    ctx.flags = {
        "status_code": result.get("status_code"),
        "title": result_title(result.get("body")),
    }


def _store_prep_route(flow: NemoGatewayFlow, ctx: NemoGatewayContext) -> None:
    _store_route_ok(flow, ctx)
    _store_fee(flow, ctx)
    route = flow.bank_transfer_route_mellat()
    ctx.route_result = route
    ctx.flags["bt_status"] = route.get("status_code")
    ctx.flags["bt_title"] = result_title(route.get("body"))
