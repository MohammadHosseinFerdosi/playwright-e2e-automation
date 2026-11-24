@WAL-3732 @api @debit @debit_shahin_saderat_statements
Feature: ft shahin provider statements

  @SET-T604 @smoke @positive @high
  Scenario: Provider statements return a page
    Given cash-out goes through ft shahin
    When DSH prepares a ft shahin cash-out with provider statements
    Then the ft shahin cash-out provider statement page is returned


  @SET-T603 @smoke @positive @high
  Scenario: Cash-out reconciles inquiry and the ledger
    Given cash-out goes through ft shahin
    When the customer requests a ft shahin cash-out with same bank
    And the customer inquires that ft shahin cash-out
    Then the ft shahin cash-out reconciles across inquiry and the ledger
