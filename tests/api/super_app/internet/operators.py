"""GET ``/top-ups/operators`` — Platform app top-up operator list."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from tests.api.client import ApiClient


class TopUpResult(BaseModel):
    """``result`` envelope on the top-ups operators response."""

    model_config = ConfigDict(extra="ignore")

    title: str
    status: int | None = None
    message: str | None = None
    level: str | None = None


class OperatorPrefix(BaseModel):
    """One prefix entry for an operator.

    ``value`` is intentionally untyped (``Any``, not ``str``) — some scenarios
    assert the API never sends a null/non-string prefix, which needs to surface
    as an ``AssertionReport`` FAIL, not a pydantic parse-time exception.
    """

    model_config = ConfigDict(extra="ignore")

    value: Any = None
    types: list[int] = Field(default_factory=list)


class TopUpOperator(BaseModel):
    """One entry in ``topUpOperators``."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    name: str
    operator_id: str = Field(alias="operatorId")
    operator: int
    prefixes: list[OperatorPrefix] = Field(default_factory=list)

    def prefix_values(self) -> list[Any]:
        """All ``prefixes[].value`` entries for this operator (raw, untyped)."""
        return [p.value for p in self.prefixes]

    def has_prefix(self, value: str) -> bool:
        """Whether ``value`` is one of this operator's listed prefixes."""
        return value in self.prefix_values()


class TopUpOperatorsBody(BaseModel):
    """Full ``GET /top-ups/operators`` success body."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    result: TopUpResult
    operators: list[TopUpOperator] = Field(default_factory=list, alias="topUpOperators")

    def operator_named(self, name: str) -> TopUpOperator | None:
        """Return the operator entry whose ``name`` matches, if present."""
        for item in self.operators:
            if item.name == name:
                return item
        return None

    def operator_with_id(self, operator_id: str) -> TopUpOperator | None:
        """Return the operator entry whose ``operatorId`` matches, if present."""
        for item in self.operators:
            if item.operator_id == operator_id:
                return item
        return None


def get_top_up_operators(client: ApiClient) -> dict[str, Any]:
    """GET the top-up operators list. Returns ``{status_code, body}``."""
    result = client.get("/top-ups/operators")
    body = result.get("body")
    if result["status_code"] == 200 and isinstance(body, dict) and "topUpOperators" in body:
        return {
            "status_code": result["status_code"],
            "body": TopUpOperatorsBody.model_validate(body),
        }
    return result
