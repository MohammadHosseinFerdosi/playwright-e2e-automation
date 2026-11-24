@api @regression @bill @tci @bill_tci_validate
Feature: Landline telephone bill validate


  @ALPHA-T2194 @positive @high @smoke
  Scenario: Customer can see landline telephone in bill configuration
    Given a customer identity for bill management
    When the customer requests bill configuration
    Then the bill configuration request succeeds
    And the bill configuration includes active landline telephone


  @ALPHA-T2193 @positive @high @smoke
  Scenario: Customer validates a landline with debt on both mid and final terms
    Given a customer identity for bill management
    And the telephone bill pool has a "both_terms_debt" case
    When the customer validates the pooled landline
    Then the landline validate succeeds
    And the landline validate includes both mid and final terms
    And every landline bill info is telephone with zero fee
    And mid and final terms share a bill id and have distinct pay ids


  @ALPHA-T2192 @positive @high
  Scenario: Customer validates a landline with mid-term debt after final is paid
    Given a customer identity for bill management
    And the telephone bill pool has a "mid_only_debt" case
    When the customer validates the pooled landline
    Then the landline validate succeeds
    And the landline validate includes a payable mid term
    And the landline validate does not include a payable final term


  @ALPHA-T2191 @positive @high
  Scenario: Customer validates a landline from another region with both terms in debt
    Given a customer identity for bill management
    And the telephone bill pool has a "both_terms_debt_region" case
    When the customer validates the pooled landline
    Then the landline validate succeeds
    And the landline validate includes both mid and final terms
    And every landline bill info is telephone with zero fee


  @ALPHA-T2190 @positive @medium
  Scenario: Customer validates a landline with no outstanding debt
    Given a customer identity for bill management
    And the telephone bill pool has a "no_debt" case
    When the customer validates the pooled landline
    Then the landline validate completes without a payable bill


  @ALPHA-T2189 @negative @high
  Scenario Outline: Landline validate is rejected for invalid input
    Given a customer identity for bill management
    When the customer validates a landline with <inquiry case>
    Then the bill inquiry is rejected as <result title>

    Examples:
      | inquiry case      | result title              |
      | missing type      | INVALID_UTILITY_BILL_TYPE |
      | empty inquiry id  | INVALID_PARAMETER         |
      | short inquiry id  | FAILURE                   |
      | wrong type water  | INVALID_UTILITY_BILL      |


  @ALPHA-T2188 @negative @medium
  Scenario: Landline validate is rejected for an unsupported phone
    Given a customer identity for bill management
    And the telephone bill pool has an "invalid_phone" case
    When the customer validates the pooled landline
    Then the bill inquiry is rejected as BILL_PHONE_NUMBER_NOT_SUPPORTED


  @ALPHA-T2187 @negative @medium
  Scenario: Landline validate is rejected when the province is not allowed
    Given a customer identity for bill management
    And the telephone bill pool has a "province_blocked" case
    When the customer validates the pooled landline
    Then the landline validate is rejected for a disallowed province
