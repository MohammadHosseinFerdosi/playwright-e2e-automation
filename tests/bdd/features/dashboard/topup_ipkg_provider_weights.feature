@ALPHA-15004 @e2e @dashboard @dashboard_topup_ipkg_provider_weights
Feature: Dashboard topup and internet package provider configuration


  @ALPHA-T2206 @smoke @positive @high
  Scenario Outline: Staff opens the operator picker from the dashboard
    Given a logged-in staff user on the dashboard
    And the staff is on the Super App page
    When the staff opens <product> from the dashboard
    Then the operator picker is shown for <product>
    And the operator picker lists the <product> operators

    Examples:
      | product          |
      | internet package |
      | topup            |


  @ALPHA-T2205 @smoke @positive @high
  Scenario Outline: Staff closes the operator picker and returns to Super App
    Given a logged-in staff user on the dashboard
    And the staff is on the Super App page
    When the staff opens <product> from the dashboard
    And the staff closes the operator picker
    Then dashboard services are shown on the Super App page

    Examples:
      | product          |
      | internet package |
      | topup            |


  @ALPHA-T2204 @regression @positive @high
  Scenario: Staff sees MCI internet package provider distribution
    Given a logged-in staff user on the dashboard
    And the staff is on the Super App page
    When the staff opens internet package from the dashboard
    And the staff opens the mci operator distribution
    Then the operator distribution is shown for internet package mci
    And the operator distribution shows providers eniac, rayan mehr, jiring and behsa


  @ALPHA-T2203 @regression @positive @high
  Scenario: Internet package confirm stays disabled until weights total 100
    Given a logged-in staff user on the dashboard
    And the staff is on the Super App page
    When the staff opens internet package from the dashboard
    And the staff opens the mci operator distribution
    And the staff sets operator distribution weights to 10, 10, 10 and 10
    Then operator distribution confirm is disabled
    When the staff sets operator distribution weights to 0, 10, 10 and 80
    Then operator distribution confirm is enabled


  @ALPHA-T2202 @regression @positive @high
  Scenario: Staff discards internet package weight changes with back
    Given a logged-in staff user on the dashboard
    And the staff is on the Super App page
    When the staff opens internet package from the dashboard
    And the staff opens the mci operator distribution
    And the staff notes the current operator distribution weights
    And the staff sets operator distribution weights to 0, 20, 30 and 50
    When the staff goes back from operator distribution
    And the staff opens the mci operator distribution
    Then the operator distribution weights match the noted values


  @ALPHA-T2201 @regression @positive @high
  Scenario: Staff saves internet package weights with enabled flags in admin config
    Given a logged-in staff user on the dashboard
    And the staff is on the Super App page
    When the staff opens internet package from the dashboard
    And the staff opens the mci operator distribution
    And the staff notes the current operator distribution weights
    And the staff notes the current internet package admin operator configs
    And the staff sets operator distribution weights to 0, 20, 30 and 50
    And the staff confirms operator distribution update
    Then a success toast is shown on the Super App page
    And the mci internet package admin weights are 0, 20, 30 and 50
    And the mci internet package admin enabled flags match the weights
    When the staff opens internet package from the dashboard
    And the staff opens the mci operator distribution
    Then the operator distribution weights are 0, 20, 30 and 50
    When the staff restores the noted internet package admin operator configs
    Then the mci internet package admin configs match the noted values
