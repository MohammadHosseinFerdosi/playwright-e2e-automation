@WAL-362 @api @debit @debit_mellat_direct
Feature: Mellat treasury ACH direct payout

  @SET-T559 @regression @positive @high
  Scenario: Treasury completes a Mellat ACH direct payout
    Given Mellat treasury can pay out over ACH
    When treasury requests a Mellat ACH direct payout
    Then the Mellat payout settles on inquiry


  @SET-T560 @smoke @negative @high
  Scenario: Treasury rejects a zero-amount direct payout
    Given Mellat treasury can pay out over ACH
    When treasury requests a zero-amount Mellat ACH direct payout
    Then the Mellat payout is rejected


  @SET-T561 @smoke @negative @high
  Scenario: Treasury rejects an invalid source account
    Given Mellat treasury can pay out over ACH
    When treasury requests a Mellat ACH direct payout from an invalid source
    Then the Mellat payout is rejected


  @SET-T562 @smoke @negative @high
  Scenario: Treasury rejects a payout without a source account
    Given Mellat treasury can pay out over ACH
    When treasury requests a Mellat ACH direct payout without a source account
    Then the Mellat payout is rejected


  @SET-T566 @smoke @negative @high
  Scenario: Same-bank destination stays off the PAYA path
    Given Mellat treasury can pay out over ACH
    When treasury requests a Mellat ACH direct payout to the same bank
    Then the Mellat payout stays off PAYA for a same-bank destination


  @SET-T567 @smoke @negative @high
  Scenario: A non-Mellat source does not attach Mellat
    Given Mellat treasury can pay out over ACH
    When treasury requests a Mellat ACH direct payout from a non-Mellat source
    Then the Mellat payout does not attach from a non-Mellat source


  @SET-T563 @smoke @positive @high
  Scenario: Duplicate tracking keeps a single ledger row
    Given Mellat treasury can pay out over ACH
    When treasury reuses a Mellat ACH tracking code
    Then the Mellat payout keeps a single ledger row on duplicate


  @SET-T564 @smoke @negative @high
  Scenario: Wrong client ids block ACH direct payout
    Given Mellat treasury can pay out over ACH
    When treasury requests a Mellat ACH direct payout with the wrong client ids
    Then the Mellat payout is rejected


  @SET-T565 @regression @positive @high
  Scenario: Treasury waits until the ACH direct payout settles
    Given Mellat treasury can pay out over ACH
    When treasury waits for a Mellat ACH direct payout to settle
    Then the Mellat payout eventually settles
