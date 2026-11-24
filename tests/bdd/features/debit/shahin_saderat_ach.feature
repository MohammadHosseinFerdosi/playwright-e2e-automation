@WAL-3732 @api @debit @debit_shahin_saderat_ach
Feature: ft shahin PAYA cash-out

  @SET-T575 @smoke @positive @high
  Scenario: Cross-bank PAYA routes as a single chunk
    Given cash-out goes through ft shahin PAYA
    When the customer requests a ft shahin cash-out with PAYA
    Then the ft shahin cash-out is routed as PAYA


  @SET-T574 @smoke @positive @high
  Scenario: PAYA inquiry stays routed before execute
    Given cash-out goes through ft shahin PAYA
    When the customer requests a ft shahin cash-out with PAYA
    And the customer inquires that ft shahin cash-out
    Then the ft shahin cash-out PAYA inquiry stays routed


  @SET-T573 @smoke @positive @high
  Scenario: Zero weights block PAYA then succeed when pinned
    Given cash-out goes through ft shahin PAYA
    When DSH prepares a ft shahin cash-out with zero weights then PAYA
    Then the ft shahin cash-out is blocked then routes as PAYA


  @SET-T572 @smoke @positive @medium
  Scenario: Ordinary PAYA fee matches the ledger
    Given cash-out goes through ft shahin PAYA
    When the customer requests a ft shahin cash-out with PAYA
    Then the ft shahin cash-out PAYA fee matches the ledger


  @SET-T570 @smoke @negative @medium
  Scenario: Zero-amount PAYA cash-out is rejected
    Given cash-out goes through ft shahin PAYA
    When the customer requests a ft shahin cash-out with a zero amount PAYA
    Then the ft shahin cash-out is rejected without storing a transfer


  @SET-T569 @smoke @negative @medium
  Scenario: Invalid IBAN PAYA cash-out is rejected
    Given cash-out goes through ft shahin PAYA
    When the customer requests a ft shahin cash-out with PAYA to an invalid IBAN
    Then the ft shahin cash-out is rejected without storing a transfer


  @SET-T568 @smoke @positive @high @idempotency
  Scenario: Duplicate PAYA route keeps a single transfer
    Given cash-out goes through ft shahin PAYA
    When the customer routes the same ft shahin cash-out twice with PAYA
    Then duplicate ft shahin routes keep a single transfer row


  @SET-T614 @smoke @negative @high
  Scenario: Same-bank IBAN must not route as PAYA
    Given cash-out goes through ft shahin PAYA
    When the customer requests a ft shahin cash-out with PAYA to a same-bank IBAN
    Then the ft shahin cash-out is not routed as PAYA


  @SET-T612 @smoke @positive @high
  Scenario: Batch PAYA splits above the chunk limit
    Given cash-out goes through ft shahin PAYA
    When the customer requests a ft shahin cash-out with batch PAYA
    Then the ft shahin cash-out batch PAYA route splits into the expected chunks


  @SET-T611 @smoke @positive @high
  Scenario: Batch PAYA inquiry lists split transactions
    Given cash-out goes through ft shahin PAYA
    When the customer requests a ft shahin cash-out with batch PAYA and inquires it
    Then the ft shahin cash-out batch PAYA inquiry lists the split transactions


  @SET-T609 @smoke @positive @high
  Scenario: Remainder batch PAYA splits into chunk plus one
    Given cash-out goes through ft shahin PAYA
    When the customer requests a ft shahin cash-out with remainder batch PAYA
    Then the ft shahin cash-out remainder batch PAYA route splits correctly


  @SET-T608 @smoke @positive @high
  Scenario: Triple batch PAYA splits into three chunks
    Given cash-out goes through ft shahin PAYA
    When the customer requests a ft shahin cash-out with triple chunk batch PAYA
    Then the ft shahin cash-out triple batch PAYA route splits into three chunks


  @SET-T607 @smoke @negative @medium
  Scenario: Negative-amount PAYA cash-out is rejected
    Given cash-out goes through ft shahin PAYA
    When the customer requests a ft shahin cash-out with a negative amount PAYA
    Then the ft shahin cash-out is rejected without storing a transfer


  @SET-T606 @smoke @negative @medium
  Scenario: PAYA cash-out without an IBAN is rejected
    Given cash-out goes through ft shahin PAYA
    When the customer requests a ft shahin cash-out with PAYA without an IBAN
    Then the ft shahin cash-out is rejected without storing a transfer


  @SET-T605 @smoke @negative @medium
  Scenario: PAYA cash-out without a tracking code is rejected
    Given cash-out goes through ft shahin PAYA
    When the customer requests a ft shahin cash-out with PAYA without a tracking code
    Then the ft shahin cash-out is rejected without storing a transfer
