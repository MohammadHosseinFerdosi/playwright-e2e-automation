@ALPHA-15004 @ALPHA-15015 @dashboard @dashboard_bill_admin_weights_api
Feature: Admin bill inquiry provider weight API


  @ALPHA-T2209 @api @smoke @positive @high
  Scenario Outline: Admin can set valid electricity inquiry weights via API
    Given the admin notes the current electricity inquiry distributions
    When the admin sets electricity inquiry weights to <weights> via the admin API
    Then the admin bills config update succeeds
    And the electricity admin inquiry weights are <weights>
    When the admin restores the noted electricity inquiry distributions
    Then the electricity admin inquiry distributions match the noted values

    Examples:
      | weights   |
      | 20 and 80 |
      | 0 and 100 |
      | 60 and 40 |


  @ALPHA-T2208 @api @regression @negative @high
  Scenario Outline: Admin electricity weight update is rejected for invalid weights
    Given the admin notes the current electricity inquiry distributions
    When the admin sets electricity inquiry weights to <weights> via the admin API
    Then the admin bills config update is rejected as INVALID_PARAMETER

    Examples:
      | weights      |
      | 6 and 4      |
      | 100 and 100  |
      | -100 and 200 |
      | 101 and -1   |
      | 150 and 0    |


  @ALPHA-T2207 @e2e @regression @positive @high
  Scenario: Electricity weights set via admin API appear on the dashboard UI
    Given a logged-in staff user on the dashboard
    And the staff is on the Super App page
    And the admin notes the current electricity inquiry distributions
    When the admin sets electricity inquiry weights to 25 and 75 via the admin API
    Then the admin bills config update succeeds
    And the electricity admin inquiry weights are 25 and 75
    When the staff opens electricity inquiry distribution
    Then the inquiry weight for finnotech is 25
    And the inquiry weight for ghabzino is 75
    When the admin restores the noted electricity inquiry distributions
    Then the electricity admin inquiry distributions match the noted values
