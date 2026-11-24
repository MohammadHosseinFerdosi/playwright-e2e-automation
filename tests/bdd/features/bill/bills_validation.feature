@api @regression @bill @bill_validation
Feature: Utility bill identifier validation


  @negative @high
  Scenario Outline: Inquiry rejects invalid bill identifiers
    Given a customer identity for bill management
    When the customer inquires a bill with <bill case>
    Then the bill inquiry is rejected as <result title>

    Examples:
      | bill case                | result title            |
      | short identifiers        | INVALID_PARAMETER       |
      | long identifiers         | INVALID_PARAMETER       |
      | empty pay id             | INVALID_PARAMETER       |
      | broken checksum          | INVALID_UTILITY_BILL    |
      | type mismatch            | INVALID_UTILITY_BILL    |
      | amount too low           | BILL_AMOUNT_INVALID     |
      | inquiry id without type  | INVALID_UTILITY_BILL_TYPE |
      | invalid cell number      | INVALID_PARAMETER       |


  @negative @high
  Scenario Outline: Payment init rejects invalid bill payment requests
    Given a customer identity for bill management
    When the customer starts bill payment with <init case>
    Then the bill payment init is rejected as <result title>

    Examples:
      | init case      | result title        |
      | empty pay id   | INVALID_PARAMETER   |
      | amount too low | BILL_AMOUNT_INVALID |
