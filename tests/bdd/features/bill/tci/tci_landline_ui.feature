@e2e @regression @bill @tci @bill_tci_ui
Feature: Landline telephone bill inquiry in the app


  @ALPHA-T2184 @positive @high @smoke
  Scenario: Logged-in customer reaches landline bill inquiry from the hub
    Given a logged-in customer in the app
    When the customer opens landline bill inquiry from the hub
    Then the landline inquiry form is ready


  @ALPHA-T2183 @positive @high @smoke
  Scenario Outline: Payment period sheet reflects the landline debt mix
    Given a logged-in customer in the app
    And the telephone bill pool has a "<pool case>" case
    When the customer opens landline bill inquiry from the hub
    And the customer inquires the pooled landline on the app
    Then the payment period sheet is shown for the pooled landline
    And the mid period is <mid state>
    And the final period is <final state>

    Examples:
      | pool case       | mid state    | final state  |
      | both_terms_debt | payable      | payable      |
      | mid_only_debt   | payable      | without debt |


  @ALPHA-T2182 @positive @high
  Scenario Outline: Customer opens bill confirm from a payable period
    Given a logged-in customer in the app
    And the telephone bill pool has a "<pool case>" case
    When the customer opens landline bill inquiry from the hub
    And the customer inquires the pooled landline on the app
    And the customer opens the <period> payment period
    Then the bill confirm page shows the selected bill details

    Examples:
      | pool case       | period |
      | both_terms_debt | mid    |
      | both_terms_debt | final  |
      | mid_only_debt   | mid    |


  @ALPHA-T2181 @positive @medium
  Scenario: A period without debt is not actionable
    Given a logged-in customer in the app
    And the telephone bill pool has a "mid_only_debt" case
    When the customer opens landline bill inquiry from the hub
    And the customer inquires the pooled landline on the app
    Then the final payment period is not actionable


  @ALPHA-T2180 @positive @medium
  Scenario: Customer inquires a landline with no outstanding debt
    Given a logged-in customer in the app
    And the telephone bill pool has a "no_debt" case
    When the customer opens landline bill inquiry from the hub
    And the customer inquires the pooled landline on the app
    Then no payable payment period is offered for the pooled landline
