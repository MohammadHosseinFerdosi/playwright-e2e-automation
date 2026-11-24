@WAL-362 @api @debit @debit_melli_direct
Feature: Melli treasury ACH direct payout

  @SET-T394 @regression @positive @high
  Scenario: Treasury completes a Melli ACH direct payout
    Given Melli treasury can pay out over ACH
    When treasury requests a Melli ACH direct payout
    Then the Melli payout settles on inquiry


  @SET-T395 @smoke @negative @high
  Scenario: Treasury rejects a zero-amount direct payout
    Given Melli treasury can pay out over ACH
    When treasury requests a zero-amount Melli ACH direct payout
    Then the Melli payout is rejected


  @SET-T396 @smoke @negative @high
  Scenario: Treasury rejects an invalid source account
    Given Melli treasury can pay out over ACH
    When treasury requests a Melli ACH direct payout from an invalid source
    Then the Melli payout is rejected


  @SET-T397 @smoke @negative @high
  Scenario: Treasury rejects a non-Melli source
    Given Melli treasury can pay out over ACH
    When treasury requests a Melli ACH direct payout from a non-Melli source
    Then the Melli payout does not attach from a non-Melli source


  @SET-T398 @smoke @negative @high
  Scenario: Same-bank destination stays off the PAYA path
    Given Melli treasury can pay out over ACH
    When treasury requests a Melli ACH direct payout to the same bank
    Then the Melli payout stays off PAYA for a same-bank destination


  @SET-T399 @smoke @positive @high
  Scenario: Duplicate tracking keeps a single ledger row
    Given Melli treasury can pay out over ACH
    When treasury reuses a Melli ACH tracking code
    Then the Melli payout keeps a single ledger row on duplicate


  @SET-T400 @smoke @negative @high
  Scenario: An inactive client blocks direct payout
    Given Melli treasury can pay out over ACH
    When treasury requests a Melli ACH direct payout with the client inactive
    Then the Melli payout is rejected


  @SET-T401 @smoke @negative @high
  Scenario: Wrong agenda is not the treasury path
    Given Melli treasury can pay out over ACH
    When treasury requests a Melli payout with the wrong agenda
    Then the Melli payout is not the treasury path for a wrong agenda


  @SET-T402 @smoke @negative @high
  Scenario: Missing source account is rejected
    Given Melli treasury can pay out over ACH
    When treasury requests a Melli ACH direct payout without a source account
    Then the Melli payout is rejected


  @SET-T403 @regression @positive @high
  Scenario: Treasury waits until the ACH direct payout settles
    Given Melli treasury can pay out over ACH
    When treasury waits for a Melli ACH direct payout to settle
    Then the Melli payout eventually settles
