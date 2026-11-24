"""Unit tests for the internet bundle catalog client/models (no UAT, no DB)."""

from __future__ import annotations

from typing import Any

from tests.api.super_app.internet.bundles import BundlesBody, CellNumberType, post_bundles

SAMPLE: dict[str, Any] = {
    "result": {
        "title": "SUCCESS",
        "status": 0,
        "message": "عملیات با موفقیت انجام شد",
        "level": "INFO",
    },
    "bundleCategories": [
        {
            "title": "روزانه",
            "bundleSections": [
                {
                    "title": "یک روزه",
                    "bundles": [
                        {
                            "type": 1,
                            "internetPackages": [
                                {
                                    "bundleId": "1819",
                                    "amount": 75020,
                                    "rawAmount": 68200,
                                    "duration": 7,
                                    "description": "بسته اينترنت 1روزه 250مگابايت",
                                    "needApproval": False,
                                    "pid": 5,
                                }
                            ],
                        }
                    ],
                }
            ],
        },
        {
            "title": "پرطرفدار",
            "bundleSections": [
                {
                    "title": "یک روزه",
                    "bundles": [
                        {
                            "type": 1,
                            "internetPackages": [
                                {
                                    "bundleId": "1819",
                                    "amount": 75020,
                                    "rawAmount": 68200,
                                    "duration": 7,
                                    "description": "بسته اينترنت 1روزه 250مگابايت",
                                    "needApproval": False,
                                    "pid": 5,
                                }
                            ],
                        }
                    ],
                }
            ],
        },
    ],
}


def test_bundles_body_parses_known_fields() -> None:
    body = BundlesBody.model_validate(SAMPLE)

    daily = body.category_named("روزانه")
    assert daily is not None
    package = daily.packages()[0]
    assert package.bundle_id == "1819"
    assert package.amount == 75020
    assert package.raw_amount == 68200
    assert package.duration == 7
    assert package.description

    titles = {category.title for category in body.categories}
    assert "روزانه" in titles
    assert "پرطرفدار" in titles

    bundle_type = daily.bundle_sections[0].bundles[0].type
    assert isinstance(bundle_type, int)
    assert bundle_type == 1


class _StubClient:
    """Duck-typed stand-in for ``ApiClient.post`` — records the call, no network."""

    def __init__(self, response_body: dict[str, Any]) -> None:
        self._response_body = response_body
        self.last_path: str | None = None
        self.last_kwargs: dict[str, Any] = {}

    def post(self, path: str, **kwargs: Any) -> dict[str, Any]:
        self.last_path = path
        self.last_kwargs = kwargs
        return {"status_code": 200, "body": self._response_body}


def test_post_bundles_parses_success_body() -> None:
    stub = _StubClient(SAMPLE)

    result = post_bundles(
        stub,  # type: ignore[arg-type]
        operator_id=1,
        cell_number="09124445456",
        cell_number_type=CellNumberType.POSTPAID,
    )

    assert isinstance(result["body"], BundlesBody)
    assert stub.last_path == "/bundles/1"
    assert stub.last_kwargs["json"] == {"cellNumber": "09124445456", "cellNumberType": "1"}
