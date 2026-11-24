"""Native digital-signature flow helpers (liveness + initiate/generate/revoke)."""

from __future__ import annotations

import base64
import logging
import secrets as py_secrets
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import httpx

from tests.api.client import ApiClient
from tests.api.kyc.digital_signatures.generate import post_digital_signatures_generate
from tests.api.kyc.digital_signatures.initiate_basic import (
    post_digital_signatures_initiate_basic,
)
from tests.api.kyc.digital_signatures.models import InitiateBasicRequest
from tests.api.kyc.digital_signatures.revoke import post_digital_signatures_revoke
from tests.api.kyc.digital_signatures.validate_password import (
    post_digital_signatures_validate_password,
)
from tests.api.kyc.liveness.models import LivenessStatusBody, RegisterLivenessRequest
from tests.api.kyc.liveness.register import post_liveness_native_register
from tests.api.kyc.liveness.remove import post_liveness_native_remove
from tests.api.kyc.liveness.selfie import post_liveness_native_selfie
from tests.api.kyc.liveness.selfie_video import post_liveness_native_selfie_video
from tests.api.kyc.liveness.signature import post_liveness_native_signature
from tests.api.kyc.liveness.status import get_liveness_status
from tests.config.settings import REPO_ROOT
from tests.services.api_assert import ensure_ok
from tests.services.assert_report import assert_truthy, mask_pii
from tests.services.db.mongo_client import MongoDbClient
from tests.services.kyc.digital_signature_secrets import DigitalSignatureSecrets

logger = logging.getLogger(__name__)

FIXTURES_DIR = REPO_ROOT / "data" / "kyc" / "fixtures"

LIVENESS_VERIFY = 50

DSP_PENDING = 0
DSP_INITIATED = 1
DSP_REVOKED = 2

DSP_DB = "digital_signature_provider_db"
DSP_COLLECTION = "digital_signatures"
LIVENESS_DB = "kyc_liveness_db"
LIVENESS_COLLECTION = "liveness"

LIVENESS_POLL_INTERVAL_S = 10.0
LIVENESS_POLL_TIMEOUT_S = 300.0
LIVENESS_MEDIA_RETRIES = 2
LIVENESS_MEDIA_RETRY_WAIT_S = 3.0
LIVENESS_FLOW_RETRIES = 2
LIVENESS_FLOW_RETRY_WAIT_S = 3.0


def fixture_b64(name: str) -> str:
    """Read a KYC fixture file as base64."""
    path = FIXTURES_DIR / name
    if not path.is_file():
        raise FileNotFoundError(f"Missing KYC fixture: {path}")
    return base64.b64encode(path.read_bytes()).decode("ascii")


@dataclass
class DigitalSignatureContext:
    """Mutable per-scenario digital-signature state."""

    secrets: DigitalSignatureSecrets
    provider_tracking_code: str | None = None
    signature_tracking_code: str | None = None
    last_result: dict[str, Any] = field(default_factory=dict)


class DigitalSignatureFlow:
    """Orchestrates native liveness + digital-signature APIs."""

    def __init__(
        self,
        client: ApiClient,
        mongo: MongoDbClient,
        secrets: DigitalSignatureSecrets,
    ) -> None:
        self._client = client
        self._mongo = mongo
        self._secrets = secrets

    @property
    def secrets(self) -> DigitalSignatureSecrets:
        """Shared UAT secrets for this flow instance."""
        return self._secrets

    def prepare_clean_state(self) -> None:
        """Revoke/cancel leftover signature + liveness state."""
        self._revoke_active_if_any()
        self._cancel_pending_in_db()
        post_liveness_native_remove(
            self._client,
            self._secrets.user_id,
            signature_type=self._secrets.signature_type,
        )
        self._soft_delete_active_liveness()

    def prepare_clean_state_best_effort(self) -> None:
        """Teardown cleanup that never raises (UAT may drop connections)."""
        try:
            self.prepare_clean_state()
        except (httpx.HTTPError, RuntimeError, TimeoutError, OSError) as exc:
            logger.warning("digital-signature teardown cleanup failed: %s", exc)

    def setup_initiated(self, ctx: DigitalSignatureContext) -> None:
        """Complete initiate/basic setup and store provider tracking on ``ctx``."""
        from tests.services.kyc.digital_signature_asserts import store_ok_initiate

        store_ok_initiate(ctx, self.initiate_basic())

    def setup_generated(self, ctx: DigitalSignatureContext) -> None:
        """Complete liveness + initiate + generate and store tracking on ``ctx``."""
        from tests.services.kyc.digital_signature_asserts import store_ok_generate

        self.complete_liveness()
        self.setup_initiated(ctx)
        assert_truthy("provider tracking code", ctx.provider_tracking_code)
        store_ok_generate(ctx, self.generate(ctx.provider_tracking_code or ""))

    def store_initiate(self, ctx: DigitalSignatureContext) -> None:
        """Run initiate/basic and record the response on ``ctx``."""
        from tests.services.kyc.digital_signature_asserts import store_initiate_result

        store_initiate_result(ctx, self.initiate_basic())

    def store_initiate_without_password(self, ctx: DigitalSignatureContext) -> None:
        """Run initiate/basic without password and record the response."""
        ctx.last_result = self.initiate_basic(with_password=False)

    def store_generate(self, ctx: DigitalSignatureContext) -> None:
        """Generate using ``ctx.provider_tracking_code`` and record the response."""
        from tests.services.kyc.digital_signature_asserts import store_generate_result

        assert_truthy("provider tracking code", ctx.provider_tracking_code)
        store_generate_result(ctx, self.generate(ctx.provider_tracking_code or ""))

    def store_revoke(self, ctx: DigitalSignatureContext) -> None:
        """Revoke and record the response on ``ctx``."""
        ctx.last_result = self.revoke()

    def store_validate_password(self, ctx: DigitalSignatureContext) -> None:
        """Validate the correct password and record the response."""
        ctx.last_result = self.validate_password(self._secrets.password)

    def store_validate_wrong_password(self, ctx: DigitalSignatureContext) -> None:
        """Validate a wrong password and record the response."""
        wrong = "".join(py_secrets.choice("0123456789") for _ in range(6))
        while wrong == self._secrets.password:
            wrong = "".join(py_secrets.choice("0123456789") for _ in range(6))
        ctx.last_result = self.validate_password(wrong)

    def register_liveness(self) -> dict[str, Any]:
        """Register native liveness for the shared UAT user."""
        request = RegisterLivenessRequest.model_validate(
            {
                "type": self._secrets.signature_type,
                "name": {
                    "firstName": self._secrets.first_name_fa,
                    "lastName": self._secrets.last_name_fa,
                },
                "englishName": {
                    "firstName": self._secrets.first_name_en,
                    "lastName": self._secrets.last_name_en,
                },
                "nationalCard": {
                    "code": self._secrets.national_card_code,
                    "serial": self._secrets.national_card_serial,
                },
                "birthDate": self._secrets.birth_date_register,
                "postalCode": self._secrets.postal_code,
                "nationalCardExpirationDate": self._secrets.national_card_expiration_date,
                "fatherName": self._secrets.father_name,
                "address": self._secrets.address,
                "city": self._secrets.city,
                "province": self._secrets.province,
                "gender": self._secrets.gender,
                "customVideoText": self._secrets.custom_video_text,
            }
        )
        result = post_liveness_native_register(
            self._client,
            self._secrets.user_id,
            self._secrets.requester_app_name,
            request,
        )
        return ensure_ok(result, context="liveness register")

    def post_signature(self) -> dict[str, Any]:
        """Upload signature image into the open liveness session."""
        return self._post_liveness_media(
            "liveness signature",
            lambda: post_liveness_native_signature(
                self._client,
                self._secrets.user_id,
                self._secrets.requester_app_name,
                signature_type=self._secrets.signature_type,
                signature_file_name="signature.png",
                signature_file_content=fixture_b64("signature.png"),
            ),
        )

    def post_selfie(self) -> dict[str, Any]:
        """Upload selfie image into the open liveness session."""
        return self._post_liveness_media(
            "liveness selfie",
            lambda: post_liveness_native_selfie(
                self._client,
                self._secrets.user_id,
                signature_type=self._secrets.signature_type,
                selfie_file_name="selfie.jpg",
                selfie_file_content=fixture_b64("selfie.jpg"),
            ),
        )

    def post_selfie_video(self) -> dict[str, Any]:
        """Upload selfie video into the open liveness session."""
        return self._post_liveness_media(
            "liveness selfie-video",
            lambda: post_liveness_native_selfie_video(
                self._client,
                self._secrets.user_id,
                signature_type=self._secrets.signature_type,
                selfie_video_file_name="video.mp4",
                selfie_video_file_content=fixture_b64("video.mp4"),
            ),
        )

    def _post_liveness_media(
        self,
        label: str,
        call: Callable[[], dict[str, Any]],
    ) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(1, LIVENESS_MEDIA_RETRIES + 1):
            try:
                return ensure_ok(call(), context=f"{label} ({attempt})")
            except RuntimeError as exc:
                last_error = exc
                msg = str(exc)
                if "KYC_LIVENESS_NOT_FOUND" in msg or "KYC_LIVENESS_INVALID_LIVENESS_STATUS" in msg:
                    raise
                if attempt < LIVENESS_MEDIA_RETRIES:
                    time.sleep(LIVENESS_MEDIA_RETRY_WAIT_S)
        raise RuntimeError(
            f"{label} failed after {LIVENESS_MEDIA_RETRIES} attempts"
        ) from last_error

    def wait_until_liveness_status(
        self,
        expected: int,
        *,
        timeout_s: float = LIVENESS_POLL_TIMEOUT_S,
        interval_s: float = LIVENESS_POLL_INTERVAL_S,
    ) -> None:
        """Poll liveness status until the expected value."""
        deadline = time.monotonic() + timeout_s
        last: Any = None
        while time.monotonic() < deadline:
            result = get_liveness_status(
                self._client,
                self._secrets.user_id,
                signature_type=self._secrets.signature_type,
            )
            body = result.get("body")
            last = body
            if result["status_code"] == 200 and isinstance(body, LivenessStatusBody):
                if body.effective_status == expected:
                    return
            time.sleep(interval_s)
        raise TimeoutError(
            mask_pii(f"liveness status did not reach {expected} within {timeout_s}s; last={last!r}")
        )

    def complete_liveness(self) -> None:
        """Run full liveness with media retries until verify."""
        last_error: Exception | None = None
        for attempt in range(1, LIVENESS_FLOW_RETRIES + 1):
            try:
                self.register_liveness()
                self.post_signature()
                self.post_selfie()
                self.post_selfie_video()
                self.wait_until_liveness_status(LIVENESS_VERIFY)
                return
            except (RuntimeError, TimeoutError) as exc:
                last_error = exc
                if attempt >= LIVENESS_FLOW_RETRIES:
                    break
                self.prepare_clean_state()
                time.sleep(LIVENESS_FLOW_RETRY_WAIT_S)
        raise RuntimeError(
            f"complete liveness failed after {LIVENESS_FLOW_RETRIES} attempts"
        ) from last_error

    def apply_incomplete_liveness_prep(self, prep: str) -> None:
        """Build a partial liveness journey for negative generate cases."""
        normalized = prep.strip().lower()
        last_error: Exception | None = None
        for attempt in range(1, LIVENESS_FLOW_RETRIES + 1):
            try:
                if normalized == "only registered liveness":
                    self.register_liveness()
                    return
                if normalized == "signature without selfie":
                    self.register_liveness()
                    self.post_signature()
                    return
                if normalized == "selfie without video":
                    self.register_liveness()
                    self.post_signature()
                    self.post_selfie()
                    return
                raise ValueError(f"Unknown liveness prep: {prep!r}")
            except RuntimeError as exc:
                last_error = exc
                if attempt >= LIVENESS_FLOW_RETRIES:
                    break
                self.prepare_clean_state()
                time.sleep(LIVENESS_FLOW_RETRY_WAIT_S)
        raise RuntimeError(
            f"liveness prep {prep!r} failed after {LIVENESS_FLOW_RETRIES} attempts"
        ) from last_error

    def wait_until_dsp_status(
        self,
        *,
        expected_status: int,
        provider_tracking_code: str | None = None,
        signature_tracking_code: str | None = None,
        timeout_s: float = 60.0,
        interval_s: float = 2.0,
    ) -> dict[str, Any]:
        """Poll DSP mongo until signature status matches."""
        if not provider_tracking_code and not signature_tracking_code:
            raise ValueError("pass provider_tracking_code or signature_tracking_code")
        deadline = time.monotonic() + timeout_s
        last: dict[str, Any] | None = None
        while time.monotonic() < deadline:
            if provider_tracking_code:
                found = self.find_dsp_by_provider_tracking(provider_tracking_code)
            else:
                found = self.find_dsp_by_tracking(signature_tracking_code or "")
            last = found
            body = found.get("body") or {}
            if found.get("status_code") == 0 and body.get("status") == expected_status:
                return found
            time.sleep(interval_s)
        raise TimeoutError(
            mask_pii(
                f"DSP status did not reach {expected_status} within {timeout_s}s; last={last!r}"
            )
        )

    def initiate_basic(self, *, with_password: bool = True) -> dict[str, Any]:
        """Call initiate/basic for the shared UAT user."""
        payload: dict[str, Any] = {
            "birthDate": self._secrets.birth_date_initiate,
            "name": {
                "firstName": self._secrets.first_name_fa,
                "lastName": self._secrets.last_name_fa,
            },
            "englishName": {
                "firstName": self._secrets.first_name_en,
                "lastName": self._secrets.last_name_en,
            },
            "nationalCard": {
                "code": self._secrets.national_card_code,
                "serial": self._secrets.national_card_serial,
            },
            "postalCode": self._secrets.postal_code,
            "type": self._secrets.signature_type,
            "livenessType": self._secrets.signature_type,
            "gender": self._secrets.gender,
            "customVideoText": self._secrets.custom_video_text,
        }
        if with_password:
            payload["password"] = self._secrets.password
        request = InitiateBasicRequest.model_validate(payload)
        return post_digital_signatures_initiate_basic(
            self._client,
            self._secrets.user_id,
            self._secrets.requester_app_name,
            request,
        )

    def generate(self, provider_tracking_code: str) -> dict[str, Any]:
        """Generate the certificate for a provider tracking code."""
        return post_digital_signatures_generate(
            self._client,
            self._secrets.user_id,
            self._secrets.requester_app_name,
            password=self._secrets.password,
            signature_type=self._secrets.signature_type,
            provider_tracking_code=provider_tracking_code,
        )

    def revoke(self) -> dict[str, Any]:
        """Revoke the active digital signature."""
        return post_digital_signatures_revoke(
            self._client,
            self._secrets.user_id,
            self._secrets.requester_app_name,
            signature_type=self._secrets.signature_type,
        )

    def validate_password(self, password: str) -> dict[str, Any]:
        """Validate a password against the active signature."""
        return post_digital_signatures_validate_password(
            self._client,
            self._secrets.user_id,
            self._secrets.requester_app_name,
            password=self._secrets.password,
        )

    def find_dsp_by_provider_tracking(self, provider_tracking_code: str) -> dict[str, Any]:
        """Find DSP row by provider tracking code."""
        return self._mongo.find_one(
            DSP_DB,
            DSP_COLLECTION,
            {
                "owner.userId": self._secrets.user_id,
                "providerInfo.trackingCode": provider_tracking_code,
            },
            sort=[("lastModificationDate", -1)],
        )

    def find_dsp_by_tracking(self, tracking_code: str) -> dict[str, Any]:
        """Find DSP row by signature tracking code."""
        return self._mongo.find_one(
            DSP_DB,
            DSP_COLLECTION,
            {"trackingCode": tracking_code},
            sort=[("lastModificationDate", -1)],
        )

    def _revoke_active_if_any(self) -> None:
        found = self._mongo.find_one(
            DSP_DB,
            DSP_COLLECTION,
            {
                "owner.userId": self._secrets.user_id,
                "status": DSP_INITIATED,
            },
            sort=[("lastModificationDate", -1)],
        )
        body = found.get("body") or {}
        if found.get("status_code") != 0 or not body.get("trackingCode"):
            return
        result = post_digital_signatures_revoke(
            self._client,
            self._secrets.user_id,
            self._secrets.requester_app_name,
            signature_type=self._secrets.signature_type,
        )
        title = None
        raw = result.get("body")
        result_obj = getattr(raw, "result", None)
        if result_obj is not None:
            title = getattr(result_obj, "title", None)
        elif isinstance(raw, dict):
            title = (raw.get("result") or {}).get("title")
        if result.get("status_code") == 200:
            return
        if title in {"DIGITAL_SIGNATURE_NOT_FOUND", "SUCCESS"}:
            return
        raise RuntimeError(
            mask_pii(f"cleanup revoke failed: status={result.get('status_code')} body={raw!r}")
        )

    def _cancel_pending_in_db(self) -> None:
        while True:
            result = self._mongo.update_one(
                DSP_DB,
                DSP_COLLECTION,
                {
                    "owner.userId": self._secrets.user_id,
                    "status": DSP_PENDING,
                },
                {"$set": {"status": DSP_REVOKED}},
            )
            if result.get("status_code") != 0:
                raise RuntimeError(mask_pii(f"DSP pending cancel failed: {result!r}"))
            if (result.get("body") or {}).get("matched_count", 0) == 0:
                break

    def _soft_delete_active_liveness(self) -> None:
        while True:
            result = self._mongo.update_one(
                LIVENESS_DB,
                LIVENESS_COLLECTION,
                {"userId": self._secrets.user_id, "deleted": False},
                {"$set": {"deleted": True}},
            )
            if result.get("status_code") != 0:
                return
            if (result.get("body") or {}).get("matched_count", 0) == 0:
                break
