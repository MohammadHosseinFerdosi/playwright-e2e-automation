@KYC-2203 @api @kyc @kyc_registration_inquiry @pii
Feature: Identity registration inquiry


  @KYC-T1135 @smoke @positive @high
  Scenario: A live person is returned for a full Hafezsaman inquiry
    Given the registration provider is hafezsaman for a full inquiry
    When the customer submits a full inquiry forcing a live lookup with strong validation
    Then the registration inquiry returns the person
    And the live journal matches the person


  @KYC-T1134 @regression @positive @high
  Scenario: A live person is returned without forcing a live lookup
    Given the registration provider is hafezsaman for a full inquiry
    When the customer submits a full inquiry with strong validation
    Then the registration inquiry returns the person
    And the live journal matches the person


  @KYC-T1133 @regression @positive @high
  Scenario: A repeat registration inquiry is served from cache
    Given the registration provider is hafezsaman for a full inquiry
    When the customer submits a full inquiry twice
    Then the registration inquiry returns the person
    And the first registration journal was live and the latest was cached


  @KYC-T1132 @regression @positive @high
  Scenario: A deceased person is returned for a Hafezsaman inquiry
    Given the registration provider is hafezsaman for a full inquiry
    When the customer submits a full inquiry for a deceased person
    Then the registration inquiry returns the person
    And the live journal matches the person


  @KYC-T1131 @regression @negative @medium
  Scenario Outline: Registration inquiry is rejected for a bad identity
    Given the registration provider is <provider> for a <kind> inquiry
    When the customer submits a <kind> inquiry using <fault>
    Then the registration inquiry is rejected as <title>

    Examples:
      | kind  | provider   | fault                     | title                  |
      | basic | jibit      | a malformed national code | INVALID_PARAMETER      |
      | full  | jibit      | a malformed national code | INVALID_PARAMETER      |
      | full  | hafezsaman | an unknown national code  | KYC_IDENTITY_NOT_FOUND |
      | full  | hafezsaman | an unknown birth date     | KYC_IDENTITY_NOT_FOUND |
      | full  | hafezsaman | a malformed national code | INVALID_PARAMETER      |


  @KYC-T1130 @regression @positive @medium
  Scenario: A full inquiry succeeds for the alternate live person
    Given the registration provider is hafezsaman for a full inquiry
    When the customer submits a full inquiry for the alternate live person
    Then the registration inquiry returns the person
    And the live journal matches the person


  @KYC-T1129 @regression @negative @medium
  Scenario Outline: Registration provider weights that break the rules are rejected
    Given the live registration provider weights are recorded
    When staff submit invalid registration weights for <rule>
    Then the registration provider settings are rejected as <title>

    Examples:
      | rule                   | title                        |
      | a weight above one     | INVALID_PARAMETER            |
      | a weight below one     | KYC_SETTING_VALIDATION_ERROR |
      | a sum below one        | KYC_SETTING_VALIDATION_ERROR |
      | a sum above one        | KYC_SETTING_VALIDATION_ERROR |
      | all weights zero       | KYC_SETTING_VALIDATION_ERROR |
      | all providers inactive | KYC_SETTING_VALIDATION_ERROR |
