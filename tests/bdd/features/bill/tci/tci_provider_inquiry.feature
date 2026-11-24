@api @regression @bill @tci @bill_tci_provider
Feature: TCI landline provider inquiry


  @positive @high
  Scenario Outline: TCI returns account info for a curated landline
    Given the telephone bill pool has a "<pool case>" case
    And TCI provider credentials are available
    When the operator requests a TCI <term> inquiry for the pooled landline
    Then the TCI inquiry reports tel status <tel status>

    Examples:
      | pool case | term  | tel status |
      | no_debt   | final | 4          |
      | no_debt   | mid   | 4          |
      | with_debt | final | 1          |
      | with_debt | mid   | 1          |


  @negative @high
  Scenario: TCI rejects invalid provider credentials
    Given the telephone bill pool has a "no_debt" case
    And TCI provider credentials are available
    When the operator requests a TCI final inquiry with invalid credentials
    Then the TCI inquiry fails authentication


  @negative @medium
  Scenario: TCI rejects a landline when the province is not allowed
    Given the telephone bill pool has a "province_blocked" case
    And TCI provider credentials are available
    When the operator requests a TCI final inquiry for the pooled landline
    Then the TCI inquiry reports that the province is not allowed


  @negative @medium
  Scenario: TCI inquiry with a leading zero is handled for the pooled landline
    Given the telephone bill pool has a "no_debt" case
    And TCI provider credentials are available
    When the operator requests a TCI final inquiry with a leading zero
    Then the TCI inquiry completes with a definitive tel status or province error
