@WAL-362 @api @debit @debit_manual_dsh
Feature: Manual portal DSH

  @SET-T408 @smoke @positive @high
  Scenario: Manual portal accepts IBANs from every bank
    Given cash-out goes through Manual
    When the customer requests manual cash-outs to IBANs from every bank
    Then the manual cash-out accepts IBANs from every bank


  @SET-T409 @smoke @positive @medium
  Scenario: Manual route writes a route journal
    Given cash-out goes through Manual
    When the customer requests a manual portal cash-out for the route journal
    Then the manual cash-out has a route journal


  @SET-T410 @smoke @positive @medium
  Scenario: Manual transfer writes a transfer journal
    Given cash-out goes through Manual
    When the customer executes a manual portal cash-out for the transfer journal
    Then the manual cash-out has a transfer journal


  @SET-T411 @smoke @positive @medium
  Scenario: Manual inquiry status matches the ledger
    Given cash-out goes through Manual
    When the customer inquires a manual cash-out after transfer
    Then the manual cash-out inquiry matches the ledger


  @SET-T412 @smoke @positive @medium
  Scenario: Manual transaction is accepted after transfer
    Given cash-out goes through Manual
    When the customer executes a manual portal cash-out for transaction status
    Then the manual cash-out is accepted after transfer


  @SET-T413 @smoke @positive @high
  Scenario: Manual transfer reconciles the ledger and inquiry
    Given cash-out goes through Manual
    When the customer completes a manual cash-out for reconcile
    Then the manual cash-out reconciles without a provider statement


  @SET-T414 @regression @positive @high
  Scenario: Duplicate manual route keeps a single transfer
    Given cash-out goes through Manual
    When the customer routes the same manual tracking code twice
    Then duplicate manual routes keep a single transfer row


  @SET-T415 @regression @negative @high
  Scenario: Duplicate manual transfer execute is rejected
    Given cash-out goes through Manual
    When the customer executes the same manual cash-out twice
    Then the manual cash-out duplicate execute is rejected


  @SET-T416 @regression @negative @high
  Scenario: Concurrent manual transfer does not double settle
    Given cash-out goes through Manual
    When customers concurrently execute the same manual cash-out
    Then the manual cash-out concurrent executes do not double settle


  @SET-T417 @smoke @positive @high
  Scenario: Manual production crisis checklist holds
    Given cash-out goes through Manual
    When DSH runs the manual production crisis checklist
    Then the manual cash-out production crisis checklist holds


  @SET-T418 @smoke @positive @high
  Scenario: DSH settle-done inquiry contract holds
    Given cash-out goes through Manual
    When DSH settles a done manual cash-out and inquires it
    Then the manual cash-out settle-done inquiry contract holds


  @SET-T420 @smoke @positive @medium
  Scenario: DSH done row schema holds
    Given cash-out goes through Manual
    When DSH inspects a done manual cash-out row
    Then the manual cash-out done-row schema holds


  @SET-T421 @regression @positive @medium
  Scenario: Nemo settlement on a reference row holds
    Given cash-out goes through Manual
    When DSH checks Nemo settlement on a reference manual row
    Then the manual cash-out Nemo settlement holds on the reference row
