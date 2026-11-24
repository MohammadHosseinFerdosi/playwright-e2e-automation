@WAL-3732 @api @debit @debit_shahin_saderat_rtgs
Feature: ft shahin SATNA cash-out

  @SET-T602 @regression @positive @high
  Scenario: Large same-day cash-out routes on SATNA
    Given cash-out goes through ft shahin SATNA
    When the customer requests a ft shahin cash-out with SATNA
    Then the ft shahin cash-out is routed as SATNA
