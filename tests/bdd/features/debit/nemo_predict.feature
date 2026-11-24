@WAL-362 @api @debit @debit_nemo_predict
Feature: Nemo cash-out fee prediction


  @SET-T539 @smoke @positive @high
  Scenario: Predict fee succeeds with the configured card
    Given a Nemo customer can predict a cash-out fee
    When the customer predicts a cash-out fee for the configured card
    Then the cash-out fee prediction succeeds


  @SET-T540 @regression @positive @high
  Scenario: Predict fee succeeds for the marker amount
    Given a Nemo customer can predict a cash-out fee
    When the customer predicts a cash-out fee at the marker amount
    Then the cash-out fee prediction succeeds


  @SET-T541 @regression @positive @high
  Scenario: Predict fee succeeds at the minimum amount
    Given a Nemo customer can predict a cash-out fee
    When the customer predicts a cash-out fee at the minimum amount
    Then the cash-out fee prediction succeeds


  @SET-T542 @regression @positive @high
  Scenario: Predict fee succeeds at the maximum amount
    Given a Nemo customer can predict a cash-out fee
    When the customer predicts a cash-out fee at the maximum amount
    Then the cash-out fee prediction succeeds


  @SET-T543 @smoke @negative @medium
  Scenario: Predict rejects an unknown user
    Given a Nemo customer can predict a cash-out fee
    When the customer predicts a cash-out fee for an unknown user
    Then the cash-out fee prediction is rejected


  @SET-T544 @smoke @negative @medium
  Scenario: Predict rejects a missing destination card
    Given a Nemo customer can predict a cash-out fee
    When the customer predicts a cash-out fee without a destination card
    Then the cash-out fee prediction is rejected


  @SET-T545 @smoke @negative @medium
  Scenario: Predict rejects a zero amount
    Given a Nemo customer can predict a cash-out fee
    When the customer predicts a cash-out fee of zero
    Then the cash-out fee prediction is rejected


  @SET-T546 @smoke @negative @medium
  Scenario: Predict rejects a negative amount
    Given a Nemo customer can predict a cash-out fee
    When the customer predicts a cash-out fee with a negative amount
    Then the cash-out fee prediction is rejected


  @SET-T547 @smoke @negative @medium
  Scenario: Predict rejects an empty card number
    Given a Nemo customer can predict a cash-out fee
    When the customer predicts a cash-out fee with an empty card number
    Then the cash-out fee prediction is rejected


  @SET-T548 @smoke @negative @medium
  Scenario: Predict rejects a missing card-number field
    Given a Nemo customer can predict a cash-out fee
    When the customer predicts a cash-out fee with the card-number field omitted
    Then the cash-out fee prediction is rejected


  @SET-T549 @smoke @negative @medium
  Scenario: Predict rejects an invalid card type
    Given a Nemo customer can predict a cash-out fee
    When the customer predicts a cash-out fee with an invalid card type
    Then the cash-out fee prediction is rejected


  @SET-T550 @smoke @negative @medium
  Scenario: Predict huge amount is not an amount-range error
    Given a Nemo customer can predict a cash-out fee
    When the customer predicts a cash-out fee with a huge amount
    Then the cash-out fee prediction is not an amount-range error


  @SET-T551 @regression @negative @low
  Scenario: Predict card secure-store diagnostic
    Given a Nemo customer can predict a cash-out fee
    When DSH runs the cash-out fee secure-store diagnostic
    Then the secure-store diagnostic is recorded
