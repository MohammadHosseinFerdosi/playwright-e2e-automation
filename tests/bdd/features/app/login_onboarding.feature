@ALPHA-15073 @ALPHA-15117 @e2e @regression @app @app_login_onboarding
Feature: Customer login onboarding


  @ALPHA-T2213 @positive @high
  Scenario: Login is ready and continue stays off until a valid phone
    Given the customer is on the app login page
    Then the welcome copy is shown
    And the phone instruction is shown
    And the mobile number hint is shown
    And the phone number is empty
    And accept and continue is shown
    And accept and continue is not clickable
    And terms of use is available
    And the referral code link is available
    When the customer enters a valid phone number
    Then accept and continue is clickable


  @ALPHA-T2212 @positive @high
  Scenario: Entered phone survives referral and terms
    Given the customer is on the app login page
    When the customer enters a valid phone number
    And the customer opens referral code
    Then the referral title is shown
    And the referral instruction is shown
    And the referral code preview is shown
    When the customer returns from referral code
    Then the entered phone number is still shown
    When the customer opens terms of use
    And the customer returns from terms of use
    Then the entered phone number is still shown


  @ALPHA-T2211 @positive @high
  Scenario: Activation code is shown and edit phone keeps the number
    Given the customer is on the app login page
    When the customer enters a valid phone number
    And the customer accepts terms and continues
    Then the activation code sent copy is shown
    And the activation code boxes are shown
    And confirm and continue is not clickable
    And the resend timer is shown
    And terms of use is available
    And the referral code link is not shown
    And edit phone is available
    When the customer edits the phone number
    Then the entered phone number is still shown
