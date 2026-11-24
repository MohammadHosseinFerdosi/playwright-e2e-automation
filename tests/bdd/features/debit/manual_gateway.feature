@WAL-362 @api @smoke @debit @debit_manual_gateway
Feature: Manual portal PAYA cash-out

  @SET-T422 @positive @medium
  Scenario: PAYA cash-out routes through the manual portal
    Given cash-out goes through Manual
    When the customer requests a manual portal cash-out
    Then the manual cash-out is routed through the portal


  @SET-T423 @negative @high
  Scenario: Manual portal cash-out stays on PAYA not internal
    Given cash-out goes through Manual
    When the customer requests a manual portal cash-out that must stay PAYA
    Then the manual cash-out is PAYA not internal


  @SET-T424 @positive @medium
  Scenario: Manual portal cash-out is stored with expected fields
    Given cash-out goes through Manual
    When the customer requests a manual portal cash-out for ledger fields
    Then the manual cash-out has the expected fields


  @SET-T425 @positive @medium
  Scenario: Manual portal transfer stays in progress
    Given cash-out goes through Manual
    When the customer executes a manual portal cash-out that stays in progress
    Then the manual cash-out stays in progress


  @SET-T426 @positive @medium
  Scenario: Inquiry does not change an in-progress manual cash-out
    Given cash-out goes through Manual
    When the customer inquires an in-progress manual cash-out
    Then the manual cash-out stays in progress after inquiry


  @SET-T427 @positive @medium
  Scenario: The scheduler does not change an in-progress manual cash-out
    Given cash-out goes through Manual
    When DSH runs the ACH scheduler against an in-progress manual cash-out
    Then the manual cash-out stays in progress after the scheduler


  @SET-T428 @positive @medium
  Scenario: Manual routing weights stay consistent
    Given cash-out goes through Manual
    When DSH checks manual portal routing weights
    Then the manual cash-out has consistent routing weights


  @SET-T429 @positive @medium
  Scenario: A Mellat split still routes to the manual portal
    Given cash-out goes through Manual
    When DSH splits cash-out weights evenly between Manual and Mellat
    And the customer requests a manual cash-out under that split
    Then the manual cash-out still routes through the portal on a split


  @SET-T430 @negative @high
  Scenario: Cross-bank IBAN is blocked when only Mellat is enabled
    Given cash-out goes through Mellat
    When the customer requests a cross-bank cash-out toward the manual portal
    Then the manual cash-out is rejected as blocked


  @SET-T431 @positive @medium
  Scenario: Manual SATNA service stays inactive
    Given cash-out goes through Manual
    When DSH checks the manual SATNA service
    Then the manual cash-out SATNA service stays inactive


  @SET-T432 @positive @medium
  Scenario: Manual portal cash-out fee is zero
    Given cash-out goes through Manual
    When the customer requests a manual portal cash-out for the fee
    Then the manual cash-out fee is zero
