"""HTTP client for Platform TCI landline provider proxy."""

from __future__ import annotations

from typing import Any

import httpx

from tests.api.tci.models import (
    SERVICE_FINAL_TERM,
    SERVICE_MID_TERM,
    TciProxyResponse,
    TciServiceRequest,
)
from tests.services.telephone_pool import TciCredentials


class TciClient:
    """One reusable ``httpx.Client`` for TCI proxy calls (xdist-safe via fixture)."""

    def __init__(self, credentials: TciCredentials, *, timeout: float = 60.0) -> None:
        self._credentials = credentials
        base = credentials.base_url.rstrip("/") + "/"
        self._client = httpx.Client(
            base_url=base,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=timeout,
        )

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self) -> TciClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def post_service(self, request: TciServiceRequest) -> dict[str, Any]:
        """POST TCI service body.

        Returns:
            ``{status_code, body}`` with a pydantic ``TciProxyResponse`` body when
            the response JSON validates; otherwise a raw/fall-back body.
        """
        response = self._client.post(
            "",
            json=request.model_dump(by_alias=True),
        )
        body: Any
        try:
            raw = response.json()
            body = TciProxyResponse.model_validate(raw) if isinstance(raw, dict) else raw
        except Exception:
            body = {"_raw": response.text}
        return {"status_code": response.status_code, "body": body}

    def inquire_final(self, tel_number: str) -> dict[str, Any]:
        """Inquire the final-term landline bill for ``tel_number``."""
        return self._inquire(tel_number, SERVICE_FINAL_TERM)

    def inquire_mid(self, tel_number: str) -> dict[str, Any]:
        """Inquire the mid-term landline bill for ``tel_number``."""
        return self._inquire(tel_number, SERVICE_MID_TERM)

    def inquire_final_with_password(self, tel_number: str, *, password: str) -> dict[str, Any]:
        """Final-term inquiry using an explicit password (auth-failure paths)."""
        request = TciServiceRequest.for_tel_inquiry(
            code=self._credentials.code,
            password=CHANGE_ME
            tel_number=tel_number,
            service=SERVICE_FINAL_TERM,
        )
        return self.post_service(request)

    def _inquire(self, tel_number: str, service: str) -> dict[str, Any]:
        request = TciServiceRequest.for_tel_inquiry(
            code=self._credentials.code,
            password=CHANGE_ME
            tel_number=tel_number,
            service=service,
        )
        return self.post_service(request)
