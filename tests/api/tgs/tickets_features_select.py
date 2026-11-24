"""Port of src/apis/tgs/post-tickets-features-select.resource."""

from typing import Any

from tests.api.client import ApiClient
from tests.api.ms_paths import MS_TGS_PATH


def post_tickets_features_select(
    client: ApiClient,
    ticket: str,
    feature_name: int | str,
    agent: str,
    platform_version: str,
) -> dict[str, Any]:
    """Port of Post Tickets Features Select — choose wallet/IPG/DPG/… on a ticket."""
    path = client.ms_path("/tickets/features/select", MS_TGS_PATH)
    return client.post(
        path,
        headers={
            "Agent": agent,
            "Platform-Version": platform_version,
        },
        json={"ticket": ticket, "featureName": feature_name},
    )
