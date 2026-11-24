"""POST ``/bundles/{operatorId}`` — Platform app internet bundle catalog.

Called right after ``GET /top-ups/operators`` (``tests/api/super_app/internet/operators.py``)
once the customer's mobile operator is known, to list that operator's internet bundles.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from tests.api.client import ApiClient

# Category titles as returned by the API — kept here so steps/asserts share one source.
CATEGORY_DAILY = "روزانه"
CATEGORY_WEEKLY = "هفتگی"
CATEGORY_MONTHLY = "ماهانه"
CATEGORY_MIX = "ترکیبی"
CATEGORY_POPULAR = "پرطرفدار"
CATEGORY_ALL = "همه"


class CellNumberType(int, Enum):
    """SIM card type — the request's ``cellNumberType``.

    Also the value every ``Bundle.type`` in the response is expected to carry back
    (the catalog returned depends on which kind of SIM the cell number is).
    """

    POSTPAID = 1
    PREPAID = 2
    DATA = 3


class BundlesResult(BaseModel):
    """``result`` envelope on the bundles response."""

    model_config = ConfigDict(extra="ignore")

    title: str
    status: int | None = None
    message: str | None = None
    level: str | None = None


class InternetPackage(BaseModel):
    """One purchasable internet package."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    bundle_id: str = Field(alias="bundleId")
    amount: int
    raw_amount: int = Field(alias="rawAmount")
    duration: int
    description: str
    need_approval: bool = Field(alias="needApproval")
    pid: int
    image_id: str | None = Field(default=None, alias="imageId")
    approval_message: str | None = Field(default=None, alias="approvalMessage")


class Bundle(BaseModel):
    """One ``bundles[]`` entry — a typed group of internet packages."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    type: int
    internet_packages: list[InternetPackage] = Field(default_factory=list, alias="internetPackages")


class BundleSection(BaseModel):
    """One duration section (e.g. "یک روزه") inside a category."""

    model_config = ConfigDict(extra="ignore")

    title: str
    bundles: list[Bundle] = Field(default_factory=list)

    def package_ids(self) -> list[str]:
        """``bundleId`` of every package in this section."""
        return [pkg.bundle_id for bundle in self.bundles for pkg in bundle.internet_packages]

    def packages(self) -> list[InternetPackage]:
        """Every package in this section, flattened across ``bundles[].internetPackages``."""
        return [pkg for bundle in self.bundles for pkg in bundle.internet_packages]


class BundleCategory(BaseModel):
    """One ``bundleCategories[]`` entry (e.g. "روزانه", "پرطرفدار", "همه")."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    title: str
    bundle_sections: list[BundleSection] = Field(default_factory=list, alias="bundleSections")

    def package_ids(self) -> list[str]:
        """``bundleId`` of every package across every section in this category."""
        return [pid for section in self.bundle_sections for pid in section.package_ids()]

    def packages(self) -> list[InternetPackage]:
        """Every package across every section in this category."""
        return [pkg for section in self.bundle_sections for pkg in section.packages()]


class BundlesBody(BaseModel):
    """Full ``POST /bundles/{operatorId}`` success body."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    result: BundlesResult
    categories: list[BundleCategory] = Field(default_factory=list, alias="bundleCategories")

    def category_named(self, title: str) -> BundleCategory | None:
        """Return the category whose ``title`` matches, if present."""
        for category in self.categories:
            if category.title == title:
                return category
        return None

    def all_packages(self) -> list[InternetPackage]:
        """Every package across every category/section (duplicates included)."""
        return [pkg for category in self.categories for pkg in category.packages()]


def post_bundles(
    client: ApiClient,
    operator_id: int | str,
    cell_number: str,
    cell_number_type: CellNumberType | str = CellNumberType.POSTPAID,
) -> dict[str, Any]:
    """POST the internet bundle catalog for ``operator_id``. Returns ``{status_code, body}``."""
    if isinstance(cell_number_type, CellNumberType):
        type_value: int | str = cell_number_type.value
    else:
        type_value = cell_number_type
    result = client.post(
        f"/bundles/{operator_id}",
        json={"cellNumber": cell_number, "cellNumberType": str(type_value)},
    )
    body = result.get("body")
    if result["status_code"] == 200 and isinstance(body, dict) and "bundleCategories" in body:
        return {
            "status_code": result["status_code"],
            "body": BundlesBody.model_validate(body),
        }
    return result
