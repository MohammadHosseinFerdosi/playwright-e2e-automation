"""Port of src/apis/health-check/health-check-service.resource."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from tests.api.client import ApiClient


class HealthCheckBody(BaseModel):
    """Success body for payments gateway health status."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    status_info: int = Field(alias="statusInfo")


def get_user_health_check_status(client: ApiClient) -> dict[str, Any]:
    """Port of User Health Check Status."""
    result = client.get("/payments/gateway/status/0")
    body = result.get("body")
    if result["status_code"] == 200 and isinstance(body, dict) and "statusInfo" in body:
        result = {
            "status_code": result["status_code"],
            "body": HealthCheckBody.model_validate(body),
        }
    return result


def get_business_health_check_status(client: ApiClient, business_id: str) -> dict[str, Any]:
    """Port of Business Health Check Status."""
    result = client.get(f"/payments/gateway/status/0/{business_id}")
    body = result.get("body")
    if result["status_code"] == 200 and isinstance(body, dict) and "statusInfo" in body:
        result = {
            "status_code": result["status_code"],
            "body": HealthCheckBody.model_validate(body),
        }
    return result
