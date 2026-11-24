@ALPHA-15004 @e2e @dashboard @dashboard_bill_inquiry_weights
Feature: Dashboard bill inquiry provider configuration


  @ALPHA-T2200 @smoke @positive @high
  Scenario: Staff reaches dashboard services on the Super App page
    Given a logged-in staff user on the dashboard
    When the staff opens Super App settings
    Then dashboard services are shown on the Super App page


  @ALPHA-T2199 @smoke @positive @high
  Scenario: Staff can open bill inquiry and return to Super App
    Given a logged-in staff user on the dashboard
    And the staff is on the Super App page
    When the staff opens bill inquiry from the dashboard
    Then the bill inquiry picker is shown
    And the bill inquiry lists the utility bill types
    When the staff closes the bill inquiry picker
    Then dashboard services are shown on the Super App page


  @ALPHA-T2198 @regression @positive @high
  Scenario: Staff sees electricity inquiry provider distribution
    Given a logged-in staff user on the dashboard
    And the staff is on the Super App page
    When the staff opens electricity inquiry distribution
    Then the inquiry distribution is shown for electricity inquiry
    And the inquiry distribution shows providers finnotech and ghabzino


  @ALPHA-T2197 @regression @positive @high
  Scenario: Staff discards electricity weight changes with back
    Given a logged-in staff user on the dashboard
    And the staff is on the Super App page
    When the staff opens electricity inquiry distribution
    And the staff notes the current inquiry weights
    And the staff sets the first provider weight to 0
    Then the inquiry weights are 0 and 100
    When the staff goes back from inquiry distribution
    And the staff opens electricity inquiry distribution
    Then the inquiry weights match the noted values


  @ALPHA-T2196 @regression @positive @high
  Scenario: Staff saves electricity inquiry provider weights
    Given a logged-in staff user on the dashboard
    And the staff is on the Super App page
    When the staff opens electricity inquiry distribution
    And the staff notes the current inquiry weights
    And the staff notes the current electricity admin inquiry distributions
    And the staff sets the inquiry weight for finnotech to 30
    And the staff sets the inquiry weight for ghabzino to 70
    And the staff confirms inquiry distribution update
    Then a success toast is shown on the Super App page
    And the electricity admin inquiry weights are 30 and 70
    When the staff opens electricity inquiry distribution
    Then the inquiry weight for finnotech is 30
    And the inquiry weight for ghabzino is 70
    When the staff restores the noted electricity admin inquiry distributions
    Then the electricity admin inquiry distributions match the noted values


  @ALPHA-T2195 @regression @positive @high
  Scenario: Landline confirm stays disabled until weights total 100
    Given a logged-in staff user on the dashboard
    And the staff is on the Super App page
    When the staff opens landline inquiry distribution
    And the staff sets inquiry weights to 10, 10 and 10
    Then inquiry distribution confirm is disabled
    When the staff sets inquiry weights to 10, 10 and 80
    Then inquiry distribution confirm is enabled
