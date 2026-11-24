@WAL-362 @api @regression @debit @debit_mellat_rtgs
Feature: Mellat SATNA cash-out

  @SET-T493 @positive @high
  Scenario: Large same-day cash-out routes on SATNA
    Given cash-out goes through Mellat SATNA
    When the customer requests a Mellat SATNA cash-out
    Then the cash-out is routed through Mellat SATNA


  @SET-T494 @positive @high
  Scenario: SATNA inquiry stays routed before execute
    Given cash-out goes through Mellat SATNA
    When the customer requests a Mellat SATNA cash-out
    And the customer inquires that SATNA cash-out
    Then the SATNA inquiry stays routed


  @SET-T495 @positive @high
  Scenario: Customer completes a live SATNA cash-out
    Given cash-out goes through Mellat SATNA
    When the customer executes a live Mellat SATNA cash-out
    Then the live SATNA cash-out settles


  @SET-T496 @positive @medium
  Scenario: A settled SATNA cash-out still inquires cleanly
    Given cash-out goes through Mellat SATNA
    When DSH looks up a settled Mellat SATNA cash-out
    Then the settled SATNA cash-out still inquires successfully
