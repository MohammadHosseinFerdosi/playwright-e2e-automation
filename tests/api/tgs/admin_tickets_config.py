"""Port of src/apis/tgs/post-admin-tickets-config.resource."""

from typing import Any

from tests.api.client import ApiClient
from tests.api.ms_paths import MS_TGS_PATH


def post_admin_tickets_config(
    client: ApiClient,
    business_id: str,
    landing_url: str,
    ttl: int,
    ticket_type: int,
    transaction_types: list[int],
    feature_orders: dict[Any, Any],
) -> dict[str, Any]:
    """Port of Post admin ticket config."""
    path = client.ms_path("/admin/tickets/config", MS_TGS_PATH)
    # JSON object keys must be strings
    orders = {str(k): v for k, v in feature_orders.items()}
    return client.post(
        path,
        json={
            "businessId": business_id,
            "featureOrders": orders,
            "landingUrl": landing_url,
            "transactionTypes": transaction_types,
            "ttl": ttl,
            "type": ticket_type,
        },
    )
