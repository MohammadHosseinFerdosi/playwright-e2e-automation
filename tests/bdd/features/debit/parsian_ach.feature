@WAL-362 @api @debit @debit_parsian_ach
Feature: Parsian PAYA cash-out

  @SET-T497 @smoke @positive @high
  Scenario: Cross-bank PAYA cash-out routes through Parsian
    Given cash-out goes through Parsian PAYA
    When the customer requests a Parsian PAYA cash-out
    Then the cash-out is routed through Parsian PAYA


  @SET-T498 @smoke @positive @high
  Scenario: PAYA inquiry stays routed before execute
    Given cash-out goes through Parsian PAYA
    When the customer requests a Parsian PAYA cash-out
    And the customer inquires that Parsian cash-out
    Then the Parsian PAYA inquiry stays routed


  @SET-T499 @smoke @positive @high
  Scenario: Zero weights block PAYA then succeed when Parsian is pinned
    Given cash-out goes through Parsian PAYA
    When DSH clears every cash-out gateway weight then enables Parsian PAYA
    Then PAYA is blocked with no gateway and then routes through Parsian


  @SET-T500 @smoke @positive @medium
  Scenario: Parsian PAYA route reports a fee
    Given cash-out goes through Parsian PAYA
    When the customer requests a Parsian PAYA cash-out
    Then the Parsian PAYA route reports a non-negative fee


  @SET-T501 @regression @positive @high
  Scenario: Customer completes a live Parsian PAYA cash-out
    Given cash-out goes through Parsian PAYA
    When the customer executes a live Parsian PAYA cash-out
    Then the live Parsian PAYA cash-out settles


  @SET-T502 @smoke @negative @medium
  Scenario: Zero-amount PAYA cash-out is rejected
    Given cash-out goes through Parsian PAYA
    When the customer requests a zero-amount Parsian PAYA cash-out
    Then the cash-out is rejected without storing a transfer


  @SET-T503 @smoke @negative @medium
  Scenario: Invalid IBAN PAYA cash-out is rejected
    Given cash-out goes through Parsian PAYA
    When the customer requests a Parsian PAYA cash-out to an invalid IBAN
    Then the cash-out is rejected without storing a transfer
