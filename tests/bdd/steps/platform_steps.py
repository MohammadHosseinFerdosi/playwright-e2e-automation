"""Step definitions for the foundation pilot smoke test.

See tests/bdd/features/platform/create_business_smoke.feature.
"""

from pytest_bdd import given, scenarios, then, when

from tests.services.assert_report import assert_truthy
from tests.services.factories import Business, BusinessFactory

scenarios("../features/platform/create_business_smoke.feature")


@given("valid business creation data", target_fixture="factory")
def _(business_factory: BusinessFactory) -> BusinessFactory:
    return business_factory


@when("the business is created", target_fixture="business")
def _(factory: BusinessFactory) -> Business:
    return factory.create()


@then("the business has a valid business id")
def _(business: Business) -> None:
    assert_truthy("Business has a valid business_id", business.business_id)
