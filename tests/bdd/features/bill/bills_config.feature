@api @smoke @bill @bill_config @positive @high
Feature: Utility bill configuration


  Scenario: Customer can load bill service configuration
    Given a customer identity for bill management
    When the customer requests bill configuration
    Then the bill configuration request succeeds
    And the bill configuration lists active bill types
