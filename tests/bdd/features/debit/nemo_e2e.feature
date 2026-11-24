@WAL-362 @api @regression @debit @debit_nemo_e2e
Feature: Nemo cash-out live journeys

  @SET-T531 @positive @high
  Scenario: Register creates a bank-transfer row on the manual portal
    Given a Nemo customer can register an IBAN cash-out
    And cash-out goes through Manual
    When the customer registers an IBAN cash-out onto the manual portal
    Then the registered cash-out is a bank-transfer row on the manual portal


  @SET-T532 @positive @high
  Scenario: Crisis path stays in progress after register
    Given a Nemo customer can register an IBAN cash-out
    And cash-out goes through Manual
    When the customer registers a crisis-path cash-out on the manual portal
    Then the registered cash-out stays in progress on the crisis path


  @SET-T533 @positive @high
  Scenario: DSH settle aligns Nemo detail and bank-transfer inquiry
    Given a Nemo customer can register an IBAN cash-out
    And cash-out goes through Manual
    When DSH settles the manual cash-out and compares Nemo detail
    Then Nemo detail aligns with bank-transfer inquiry


  @SET-T534 @positive @high
  Scenario: Register creates a bank-transfer row on Mellat
    Given a Nemo customer can register an IBAN cash-out
    And cash-out goes through Mellat
    When the customer registers an IBAN cash-out onto Mellat
    Then the registered cash-out is a bank-transfer row on Mellat


  @SET-T535 @positive @high
  Scenario: Register polls to a terminal state on Mellat
    Given a Nemo customer can register an IBAN cash-out
    And cash-out goes through Mellat
    When the customer registers an IBAN cash-out onto Mellat and waits
    Then the registered cash-out reaches a terminal Mellat state


  @SET-T536 @positive @high
  Scenario: A reference cash-out journey audits clean
    Given a Nemo customer can register an IBAN cash-out
    When DSH audits a reference Mellat cash-out journey
    Then the reference cash-out journey audits clean
