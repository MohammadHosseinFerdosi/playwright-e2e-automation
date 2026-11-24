@api @smoke @platform @platform_create_business @positive @high
Feature: Business creation

  Scenario: Create a business successfully
    Given valid business creation data
    When the business is created
    Then the business has a valid business id
