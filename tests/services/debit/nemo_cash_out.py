"""Nemo cash-out predict + register orchestration for Debit BDD."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import pytest

from tests.api.client import ApiClient
from tests.api.debit.nemo.cash_out_detail import get_cash_out_detail
from tests.api.debit.nemo.cash_out_predict import post_cash_out_predict
from tests.api.debit.nemo.cash_out_register import post_cash_out_register
from tests.api.debit.nemo.models import (
    CashOutPredictRequest,
    CashOutRegisterRequest,
    TargetPan,
    result_title,
    tracking_code_from_body,
)
from tests.services.debit.nemo_secrets import (
    NEGATIVE_IBAN_SPACES,
    NEGATIVE_INVALID_IBAN,
    REGISTER_KYC_BLOCK_TITLES,
    UNKNOWN_USER,
    NemoSecrets,
    require_live_cash_out,
)
from tests.services.debit.nemo_wallet_db import NemoWalletDb

logger = logging.getLogger(__name__)


@dataclass
class NemoCashOutContext:
    """Per-scenario envelopes and flags for Nemo cash-out."""

    secrets: CHANGE_ME
    last_result: dict[str, Any] = field(default_factory=dict)
    detail_result: dict[str, Any] = field(default_factory=dict)
    tracking_code: str | None = None
    flags: dict[str, Any] = field(default_factory=dict)


class NemoCashOutFlow:
    """Predict / register / detail helpers with optional wallet_db cleanup."""

    def __init__(
        self,
        client: ApiClient,
        secrets: CHANGE_ME
        wallet: NemoWalletDb | None = None,
    ) -> None:
        self._client = client
        self._secrets = CHANGE_ME
        self._wallet = wallet

    @property
    def secrets(self) -> NemoSecrets:
        """UAT secrets."""
        return self._secrets

    @property
    def wallet(self) -> NemoWalletDb | None:
        """Optional wallet Mongo."""
        return self._wallet

    def prepare_wallet(self) -> None:
        """Close open settlements so register is not blocked."""
        if self._wallet is None:
            return
        self._wallet.close_open_settlements()
        if self._wallet.latest_cash_out_kyc_blocked():
            self._secrets.register_kyc_blocked = CHANGE_ME
        self._wallet.assert_no_blocking_settlement()

    def assert_ready(self) -> None:
        """Confirm secrets loaded (predict does not need Mongo)."""
        _ = self._secrets.user_id

    def predict(
        self,
        *,
        amount: int | None = None,
        target_pan: dict[str, str] | None = None,
        user_id: str | None = None,
        omit_pan: bool = False,
    ) -> dict[str, Any]:
        """POST cash-out predict."""
        pan_model: TargetPan | None
        if omit_pan:
            pan_model = None
        elif target_pan is None:
            pan_model = TargetPan.model_validate(self._secrets.configured_pan())
        else:
            pan_model = TargetPan.model_validate(target_pan)
        payload: dict[str, Any] = {
            "amount": self._secrets.safe_amount if amount is None else amount,
        }
        if pan_model is not None:
            payload["targetPan"] = pan_model.to_payload()
        request = CashOutPredictRequest.model_validate(payload)
        return post_cash_out_predict(
            self._client,
            request,
            user_id=user_id or self._secrets.user_id,
            forwarded_for=self._secrets.forwarded_for,
        )

    def register(
        self,
        *,
        amount: int | None = None,
        iban: str | None = None,
        birth_date: str | None = None,
        user_id: str | None = None,
        omit_iban: bool = False,
        omit_birth: bool = False,
    ) -> dict[str, Any]:
        """POST cash-out register."""
        payload_iban = None if omit_iban else (iban or self._secrets.require_target_iban())
        payload_birth = None if omit_birth else (birth_date or self._secrets.birth_date)
        request = CashOutRegisterRequest.model_validate(
            {
                "amount": self._secrets.safe_amount if amount is None else amount,
                "iban": payload_iban,
                "birthDate": payload_birth,
            }
        )
        return post_cash_out_register(
            self._client,
            request,
            user_id=user_id or self._secrets.user_id,
            forwarded_for=self._secrets.forwarded_for,
        )

    def detail(self, tracking_code: str, *, user_id: str | None = None) -> dict[str, Any]:
        """GET cash-out detail."""
        return get_cash_out_detail(
            self._client,
            tracking_code,
            user_id=user_id or self._secrets.user_id,
            forwarded_for=self._secrets.forwarded_for,
        )

    def register_or_skip_kyc(self, result: dict[str, Any], *, label: str) -> str:
        """Return tracking code or skip on known KYC / balance blocks."""
        title = result_title(result.get("body"))
        if result.get("status_code") == 200 and title == "SUCCESS":
            tracking = tracking_code_from_body(result.get("body"))
            if not tracking:
                raise AssertionError(f"{label}: SUCCESS but no trackingCode")
            return tracking
        if title in REGISTER_KYC_BLOCK_TITLES:
            self._secrets.register_kyc_blocked = CHANGE_ME
            pytest.skip(
                f"POST /wallets/cash-out/register blocked (title={title}). "
                "Use detail on settled reference rows instead."
            )
        raise AssertionError(
            f"{label}: unexpected register response "
            f"HTTP={result.get('status_code')} title={title}"
        )


def store_predict_case(
    flow: NemoCashOutFlow, ctx: NemoCashOutContext, case: str
) -> None:
    """Dispatch predict When."""
    {
        "configured card fee": _predict_success,
        "marker amount fee": _predict_marker,
        "min boundary fee": _predict_min,
        "max boundary fee": _predict_max,
        "unknown user rejected": _predict_unknown,
        "missing target pan rejected": _predict_no_pan,
        "zero amount rejected": _predict_zero,
        "negative amount rejected": _predict_negative,
        "empty pan value rejected": _predict_empty_pan,
        "missing pan value field rejected": _predict_missing_pan_value,
        "invalid pan type rejected": _predict_invalid_type,
        "huge amount not amount range": _predict_huge,
        "card secure store diagnostic": _predict_secure_store,
    }[case](flow, ctx)


def store_register_case(
    flow: NemoCashOutFlow, ctx: NemoCashOutContext, case: str
) -> None:
    """Dispatch register When."""
    {
        "success and detail": _register_success,
        "min amount boundary": _register_min,
        "max amount boundary": _register_max,
        "poll to terminal": _register_poll_terminal,
        "unknown user rejected": _register_unknown,
        "invalid iban rejected": _register_bad_iban,
        "iban with spaces rejected": _register_iban_spaces,
        "missing iban rejected": _register_missing_iban,
        "missing birth date rejected": _register_missing_birth,
        "invalid birth date rejected": _register_bad_birth,
        "amount below min rejected": _register_below_min,
        "amount above max rejected": _register_above_max,
        "detail unknown tracking": _detail_unknown,
    }[case](flow, ctx)


def _remember(ctx: NemoCashOutContext, result: dict[str, Any], **extra: Any) -> None:
    ctx.last_result = result
    ctx.flags["status_code"] = result.get("status_code")
    ctx.flags["title"] = result_title(result.get("body"))
    body = result.get("body")
    fee = None
    if isinstance(body, dict):
        fee = body.get("fee")
    elif body is not None and hasattr(body, "fee"):
        fee = getattr(body, "fee", None)
    ctx.flags["fee"] = fee
    ctx.flags.update(extra)


def _predict_success(flow: NemoCashOutFlow, ctx: NemoCashOutContext) -> None:
    _remember(ctx, flow.predict())


def _predict_marker(flow: NemoCashOutFlow, ctx: NemoCashOutContext) -> None:
    _remember(ctx, flow.predict(amount=flow.secrets.marker_amount))


def _predict_min(flow: NemoCashOutFlow, ctx: NemoCashOutContext) -> None:
    _remember(ctx, flow.predict(amount=flow.secrets.min_cash_out_amount))


def _predict_max(flow: NemoCashOutFlow, ctx: NemoCashOutContext) -> None:
    _remember(ctx, flow.predict(amount=flow.secrets.max_cash_out_amount))


def _predict_unknown(flow: NemoCashOutFlow, ctx: NemoCashOutContext) -> None:
    pan = flow.secrets.configured_pan()
    _remember(ctx, flow.predict(target_pan=pan, user_id=UNKNOWN_USER))


def _predict_no_pan(flow: NemoCashOutFlow, ctx: NemoCashOutContext) -> None:
    _remember(ctx, flow.predict(omit_pan=True, amount=flow.secrets.safe_amount))


def _predict_zero(flow: NemoCashOutFlow, ctx: NemoCashOutContext) -> None:
    _remember(ctx, flow.predict(amount=0, target_pan=flow.secrets.configured_pan()))


def _predict_negative(flow: NemoCashOutFlow, ctx: NemoCashOutContext) -> None:
    _remember(ctx, flow.predict(amount=-1, target_pan=flow.secrets.configured_pan()))


def _predict_empty_pan(flow: NemoCashOutFlow, ctx: NemoCashOutContext) -> None:
    pan = flow.secrets.configured_pan()
    pan["value"] = ""
    pan["prefix"] = ""
    pan["postfix"] = ""
    _remember(ctx, flow.predict(target_pan=pan))


def _predict_missing_pan_value(flow: NemoCashOutFlow, ctx: NemoCashOutContext) -> None:
    pan = flow.secrets.configured_pan()
    del pan["value"]
    _remember(ctx, flow.predict(target_pan=pan))


def _predict_invalid_type(flow: NemoCashOutFlow, ctx: NemoCashOutContext) -> None:
    pan = flow.secrets.configured_pan()
    pan["type"] = "99"
    _remember(ctx, flow.predict(target_pan=pan))


def _predict_huge(flow: NemoCashOutFlow, ctx: NemoCashOutContext) -> None:
    pan = flow.secrets.configured_pan()
    _remember(
        ctx,
        flow.predict(amount=999_999_999_999, target_pan=pan, user_id=UNKNOWN_USER),
    )


def _predict_secure_store(flow: NemoCashOutFlow, ctx: NemoCashOutContext) -> None:
    _remember(ctx, flow.predict())


def _register_success(flow: NemoCashOutFlow, ctx: NemoCashOutContext) -> None:
    require_live_cash_out(flow.secrets)
    flow.prepare_wallet()
    wallet = flow.wallet
    if wallet is None:
        pytest.skip("Nemo wallet Mongo required for live register")
    before = wallet.count_cash_outs_for_user()
    result = flow.register()
    tracking = flow.register_or_skip_kyc(result, label="register")
    wallet.assert_cash_out_persisted(tracking, amount=flow.secrets.safe_amount)
    after = wallet.count_cash_outs_for_user()
    detail = flow.detail(tracking)
    ctx.tracking_code = tracking
    ctx.last_result = result
    ctx.detail_result = detail
    ctx.flags["cash_out_delta"] = after - before
    ctx.flags["detail_status_code"] = detail.get("status_code")
    ctx.flags["detail_title"] = result_title(detail.get("body"))


def _register_min(flow: NemoCashOutFlow, ctx: NemoCashOutContext) -> None:
    _register_boundary(flow, ctx, flow.secrets.min_cash_out_amount, is_max=False)


def _register_max(flow: NemoCashOutFlow, ctx: NemoCashOutContext) -> None:
    _register_boundary(flow, ctx, flow.secrets.max_cash_out_amount, is_max=True)


def _register_boundary(
    flow: NemoCashOutFlow,
    ctx: NemoCashOutContext,
    amount: int,
    *,
    is_max: bool,
) -> None:
    require_live_cash_out(flow.secrets)
    flow.prepare_wallet()
    result = flow.register(amount=amount)
    tracking = None
    if not (is_max and result.get("status_code") != 200):
        tracking = flow.register_or_skip_kyc(result, label=f"register {amount}")
    ctx.tracking_code = tracking
    _remember(ctx, result, is_max=is_max, tracking=tracking)


def _register_poll_terminal(flow: NemoCashOutFlow, ctx: NemoCashOutContext) -> None:
    require_live_cash_out(flow.secrets)
    flow.prepare_wallet()
    wallet = flow.wallet
    if wallet is None:
        pytest.skip("Nemo wallet Mongo required for live register")
    result = flow.register()
    tracking = flow.register_or_skip_kyc(result, label="register poll")
    wallet.assert_cash_out_persisted(tracking, amount=flow.secrets.safe_amount)
    detail_body = _poll_detail_until_progress(flow, tracking)
    co = wallet.find_cash_out(tracking) or {}
    status = detail_body.get("status")
    if status is None:
        status = co.get("status")
    terminal = frozenset({4, 5, 6, 20, 21, 22, 23, 24, 25})
    ctx.tracking_code = tracking
    ctx.last_result = result
    ctx.flags["detail_title"] = (detail_body.get("result") or {}).get("title")
    ctx.flags["cash_out_status"] = status
    ctx.flags["terminal_ok"] = status in terminal or status in (4, 5, 21)


def _poll_detail_until_progress(
    flow: NemoCashOutFlow, tracking: str, *, timeout_sec: float = 180.0
) -> dict[str, Any]:
    """Poll cash-out detail until status leaves the initial (0/1) window."""
    deadline = time.time() + timeout_sec
    last: dict[str, Any] = {}
    while time.time() < deadline:
        detail = flow.detail(tracking)
        body = detail.get("body")
        if isinstance(body, dict):
            last = body
        elif body is not None and hasattr(body, "model_dump"):
            last = body.model_dump(by_alias=True)
        if detail.get("status_code") == 200:
            status = str(last.get("status", ""))
            if status and status not in ("0", "1"):
                return last
        time.sleep(5.0)
    return last


def _register_unknown(flow: NemoCashOutFlow, ctx: NemoCashOutContext) -> None:
    iban = flow.secrets.require_target_iban()
    _remember(ctx, flow.register(iban=iban, user_id=UNKNOWN_USER))


def _register_bad_iban(flow: NemoCashOutFlow, ctx: NemoCashOutContext) -> None:
    _remember(ctx, flow.register(iban=NEGATIVE_INVALID_IBAN))


def _register_iban_spaces(flow: NemoCashOutFlow, ctx: NemoCashOutContext) -> None:
    _remember(ctx, flow.register(iban=NEGATIVE_IBAN_SPACES))


def _register_missing_iban(flow: NemoCashOutFlow, ctx: NemoCashOutContext) -> None:
    _remember(ctx, flow.register(omit_iban=True))


def _register_missing_birth(flow: NemoCashOutFlow, ctx: NemoCashOutContext) -> None:
    _remember(ctx, flow.register(omit_birth=True))


def _register_bad_birth(flow: NemoCashOutFlow, ctx: NemoCashOutContext) -> None:
    _remember(
        ctx,
        flow.register(
            iban=flow.secrets.require_target_iban(),
            birth_date="not-a-date",
        ),
    )


def _register_below_min(flow: NemoCashOutFlow, ctx: NemoCashOutContext) -> None:
    _remember(ctx, flow.register(amount=flow.secrets.amount_below_min))


def _register_above_max(flow: NemoCashOutFlow, ctx: NemoCashOutContext) -> None:
    _remember(ctx, flow.register(amount=flow.secrets.amount_above_max))


def _detail_unknown(flow: NemoCashOutFlow, ctx: NemoCashOutContext) -> None:
    _remember(
        ctx,
        flow.detail("QA-NEMO-NOT-FOUND-001", user_id=UNKNOWN_USER),
    )
