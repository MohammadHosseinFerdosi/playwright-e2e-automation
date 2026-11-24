@WAL-362 @api @debit @debit_nemo_cash_out
Feature: Nemo IBAN cash-out register

  @SET-T518 @regression @positive @high
  Scenario: Register creates a cash-out and detail succeeds
    Given a Nemo customer can register an IBAN cash-out
    When the customer registers an IBAN cash-out
    Then the Nemo cash-out register succeeds


  @SET-T519 @regression @positive @high
  Scenario: Register succeeds at the minimum amount
    Given a Nemo customer can register an IBAN cash-out
    When the customer registers an IBAN cash-out at the minimum amount
    Then the Nemo cash-out register succeeds


  @SET-T520 @regression @positive @high
  Scenario: Register succeeds at the maximum amount
    Given a Nemo customer can register an IBAN cash-out
    When the customer registers an IBAN cash-out at the maximum amount
    Then the Nemo cash-out register succeeds


  @SET-T521 @regression @positive @high
  Scenario: Register reaches a terminal cash-out state
    Given a Nemo customer can register an IBAN cash-out
    When the customer registers an IBAN cash-out and waits for a terminal state
    Then the Nemo cash-out register reaches a terminal state


  @SET-T522 @smoke @negative @medium
  Scenario: Register rejects an unknown user
    Given a Nemo customer can register an IBAN cash-out
    When the customer registers an IBAN cash-out for an unknown user
    Then the Nemo cash-out register is rejected


  @SET-T523 @smoke @negative @medium
  Scenario: Register rejects an invalid IBAN
    Given a Nemo customer can register an IBAN cash-out
    When the customer registers a cash-out to an invalid IBAN
    Then the Nemo cash-out register is rejected


  @SET-T524 @smoke @negative @medium
  Scenario: Register rejects an IBAN with spaces
    Given a Nemo customer can register an IBAN cash-out
    When the customer registers a cash-out to an IBAN with spaces
    Then the Nemo cash-out register is rejected


  @SET-T525 @smoke @negative @medium
  Scenario: Register rejects a missing IBAN
    Given a Nemo customer can register an IBAN cash-out
    When the customer registers a cash-out without an IBAN
    Then the Nemo cash-out register is rejected


  @SET-T526 @smoke @negative @medium
  Scenario: Register rejects a missing birth date
    Given a Nemo customer can register an IBAN cash-out
    When the customer registers a cash-out without a birth date
    Then the Nemo cash-out register is rejected


  @SET-T527 @smoke @negative @medium
  Scenario: Register rejects an invalid birth date
    Given a Nemo customer can register an IBAN cash-out
    When the customer registers a cash-out with an invalid birth date
    Then the Nemo cash-out register is rejected


  @SET-T528 @smoke @negative @medium
  Scenario: Register rejects an amount below the minimum
    Given a Nemo customer can register an IBAN cash-out
    When the customer registers a cash-out below the minimum amount
    Then the Nemo cash-out register is rejected


  @SET-T529 @smoke @negative @medium
  Scenario: Register rejects an amount above the maximum
    Given a Nemo customer can register an IBAN cash-out
    When the customer registers a cash-out above the maximum amount
    Then the Nemo cash-out register is rejected


  @SET-T530 @smoke @negative @medium
  Scenario: Detail rejects an unknown tracking code
    Given a Nemo customer can register an IBAN cash-out
    When the customer asks for cash-out detail with an unknown tracking code
    Then the Nemo cash-out detail is rejected
