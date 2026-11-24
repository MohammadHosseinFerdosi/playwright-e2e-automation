"""Shared result envelope helpers for bill-mng responses."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class BillResult(BaseModel):
    """``result`` object on bill-mng success and business-error bodies."""

    model_config = ConfigDict(extra="ignore")

    title: str
    status: int | None = None
    message: str | None = None
    level: str | None = None


class BillResultBody(BaseModel):
    """Minimal body when only ``result.title`` is asserted."""

    model_config = ConfigDict(extra="ignore")

    result: BillResult


def result_title_from_body(body: Any) -> str | None:
    """Extract ``result.title`` from a raw or parsed bill response body."""
    if isinstance(body, BillResultBody):
        return body.result.title
    result_obj = getattr(body, "result", None)
    if result_obj is not None and hasattr(result_obj, "title"):
        title = result_obj.title
        return title if isinstance(title, str) else None
    if isinstance(body, dict):
        result = body.get("result")
        if isinstance(result, dict):
            title = result.get("title")
            return title if isinstance(title, str) else None
    return None


def parse_result_body(body: Any) -> BillResultBody | None:
    """Parse a dict body into ``BillResultBody`` when ``result`` is present."""
    if isinstance(body, dict) and isinstance(body.get("result"), dict):
        return BillResultBody.model_validate(body)
    return None
