"""Gherkin regex and dispatch for the operator+cell internet bundle-catalog request.

Pattern conventions: ``.cursor/rules/step-patterns.mdc``.
"""

from __future__ import annotations

from typing import Any

from tests.api.client import ApiClient
from tests.api.super_app.internet.bundles import CellNumberType, post_bundles

BUNDLE_CATALOG_OPERATOR_CELL_STEP = (
    r'^the bundle catalog is requested for operator id "(?P<operator_id>[^"]*)" '
    r'cell "(?P<cell_number>[^"]*)"'
    r'(?: SIM type "(?P<sim_card_type>[^"]*)")?$'
)


def request_bundle_catalog(
    client: ApiClient,
    operator_id: str,
    cell_number: str,
    sim_card_type: str | None,
) -> dict[str, Any]:
    """POST the bundle catalog; SIM type defaults to POSTPAID when not captured.

    Raises:
        KeyError: If ``sim_card_type`` is captured but not a known ``CellNumberType``.
    """
    cell_number_type = (
        CellNumberType.POSTPAID if sim_card_type is None else CellNumberType[sim_card_type]
    )
    return post_bundles(client, operator_id, cell_number, cell_number_type=cell_number_type)
