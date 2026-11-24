@WAL-3732 @api @debit @debit_shahin_saderat_internal
Feature: ft shahin same-bank cash-out

  @SET-T595 @smoke @positive @high
  Scenario: Same-bank cash-out routes internally
    Given cash-out goes through ft shahin
    When the customer requests a ft shahin cash-out with same bank
    Then the ft shahin cash-out is routed internally


  @SET-T594 @smoke @negative @medium
  Scenario: Invalid IBAN cash-out is rejected
    Given cash-out goes through ft shahin
    When the customer requests a ft shahin cash-out with an invalid IBAN
    Then the ft shahin cash-out is rejected without storing a transfer


  @SET-T593 @smoke @negative @high
  Scenario: Hostile owner names do not cause a server error
    Given cash-out goes through ft shahin
    When the customer requests a ft shahin cash-out with hostile owner names
    Then the ft shahin cash-out routes do not return a server error


  @SET-T590 @smoke @positive @high
  Scenario: Cash-out stays on the internal rail
    Given cash-out goes through ft shahin
    When the customer requests a ft shahin cash-out with same bank
    Then the ft shahin cash-out is routed internally
    And the ft shahin cash-out is not routed as PAYA


  @SET-T589 @smoke @positive @medium
  Scenario: Marker-amount cash-out is stored
    Given cash-out goes through ft shahin
    When the customer requests a ft shahin cash-out with a marker amount
    Then the ft shahin cash-out is routed internally
    And the ft shahin cash-out stored amount is the marker amount


  @SET-T588 @smoke @positive @medium
  Scenario: Internal cash-out fee is zero
    Given cash-out goes through ft shahin
    When the customer requests a ft shahin cash-out with same bank
    Then the ft shahin cash-out fee is zero


  @SET-T586 @smoke @positive @high @idempotency
  Scenario: Duplicate route keeps a single transfer
    Given cash-out goes through ft shahin
    When the customer routes the same ft shahin cash-out twice with internal
    Then duplicate ft shahin routes keep a single transfer row


  @SET-T619 @smoke @positive @high
  Scenario: Internal inquiry stays routed before execute
    Given cash-out goes through ft shahin
    When the customer requests a ft shahin cash-out with same bank
    And the customer inquires that ft shahin cash-out
    Then the ft shahin cash-out internal inquiry stays routed


  @SET-T618 @smoke @negative @medium
  Scenario: Zero-amount same-bank cash-out is rejected
    Given cash-out goes through ft shahin
    When the customer requests a ft shahin cash-out with a zero amount
    Then the ft shahin cash-out is rejected without storing a transfer
