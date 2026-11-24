"""Port of src/apis/purchase-mng/moke-pay/mock-ipg-result-psp.resource."""

from typing import Any

from tests.api.client import ApiClient


def post_ipg_result_psp(
    client: ApiClient,
    token: CHANGE_ME
    status: int,
    trace_id: str,
    rrn: str,
    sale_order_id: str,
    psp_code: str = "999",
) -> dict[str, Any]:
    """Port of POST IPG Result PSP — complete mock IPG result on purchase-mng."""
    path = f"/purchases/ipg/result?pspCode={psp_code}&traceId={trace_id}"
    return client.post(
        path,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "token": token,
            "status": status,
            "rrn": rrn,
            "SaleOrderId": sale_order_id,
        },
    )
