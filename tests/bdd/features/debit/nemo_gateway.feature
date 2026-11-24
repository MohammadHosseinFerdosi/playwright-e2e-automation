@WAL-362 @api @debit @debit_nemo_gateway
Feature: Nemo app cash-out route prediction

  @SET-T552 @regression @positive @medium
  Scenario: Route prediction follows Mellat
    Given the Nemo app will cash out through Mellat
    When the customer asks which cash-out route Mellat will use
    Then the predicted cash-out route is Mellat internal


  @SET-T553 @regression @positive @medium
  Scenario: Route prediction follows Shahin
    Given the Nemo app will cash out through Shahin
    When the customer asks which cash-out route Shahin will use
    Then the predicted cash-out route is Shahin internal


  @SET-T554 @regression @positive @medium
  Scenario: Route prediction follows the manual portal
    Given the Nemo app will cash out through Manual
    When the customer asks which cash-out route the manual portal will use
    Then the predicted cash-out route is the manual portal


  @SET-T555 @regression @positive @medium
  Scenario: Route prediction uses Manual on a fifty-fifty split
    Given the customer is signed in to the Nemo app
    When DSH splits Nemo cash-out weights evenly between Manual and Mellat
    And the customer asks which cash-out route the split will use
    Then the predicted cash-out route prefers the manual portal on a split


  @SET-T556 @smoke @positive @medium
  Scenario: Transfer route prediction succeeds via the app
    Given the customer is signed in to the Nemo app
    When the customer asks the app which cash-out route will be used
    Then the app cash-out route prediction succeeds


  @SET-T557 @smoke @positive @medium
  Scenario: Transfer fee succeeds via the app
    Given the customer is signed in to the Nemo app
    When the customer asks the app for the cash-out fee
    Then the app cash-out fee succeeds


  @SET-T558 @regression @positive @high
  Scenario: App prediction then bank-transfer route succeeds
    Given the customer is signed in to the Nemo app
    When the customer prepares a Mellat cash-out via the app then routes it
    Then the app-prepared Mellat cash-out routes successfully
