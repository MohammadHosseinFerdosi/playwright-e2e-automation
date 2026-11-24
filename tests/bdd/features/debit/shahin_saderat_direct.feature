@WAL-3732 @api @debit @debit_shahin_saderat_direct
Feature: ft shahin treasury direct payout

  @SET-T584 @smoke @negative @high
  Scenario Outline: Treasury rejects a zero-amount <rail> direct payout
    Given ft shahin treasury can pay out over <rail>
    When treasury requests a ft shahin payout with a zero amount <rail>
    Then the ft shahin payout is rejected

    Examples:
      | rail     |
      | ACH      |
      | internal |


  @SET-T583 @smoke @negative @high
  Scenario Outline: Treasury rejects an invalid <rail> source account
    Given ft shahin treasury can pay out over <rail>
    When treasury requests a ft shahin payout with an invalid source <rail>
    Then the ft shahin payout is rejected

    Examples:
      | rail     |
      | ACH      |
      | internal |


  @SET-T582 @smoke @negative @high
  Scenario Outline: Treasury rejects a <rail> payout without a source
    Given ft shahin treasury can pay out over <rail>
    When treasury requests a ft shahin payout with no source <rail>
    Then the ft shahin payout is rejected

    Examples:
      | rail     |
      | ACH      |
      | internal |


  @SET-T581 @smoke @negative @high
  Scenario: Same-bank destination stays off the PAYA path
    Given ft shahin treasury can pay out over ACH
    When treasury requests a ft shahin payout with ACH to the same bank
    Then the ft shahin payout stays off PAYA for a same-bank destination


  @SET-T579 @smoke @positive @high @idempotency
  Scenario Outline: Duplicate <rail> tracking keeps a single ledger row
    Given ft shahin treasury can pay out over <rail>
    When treasury requests a ft shahin payout with duplicate <rail>
    Then the ft shahin payout keeps a single ledger row on duplicate

    Examples:
      | rail     |
      | ACH      |
      | internal |
