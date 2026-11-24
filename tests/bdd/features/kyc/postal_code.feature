@KYC-2202 @api @kyc @kyc_postal_code @pii
Feature: Postal-code address inquiry


  @KYC-T1128 @smoke @positive @high
  Scenario: A valid postal code returns the Jibit address
    Given the address provider is jibit
    When the customer inquires a valid postal code
    Then the postal-code inquiry succeeds
    And the live journal matches the provider address


  @KYC-T1127 @regression @positive @high
  Scenario: An unknown postal code is not found
    Given the address provider is jibit
    When the customer inquires an unknown postal code
    Then the postal-code inquiry is not found
    And the live journal is a not-found failure


  @KYC-T1126 @regression @negative @medium
  Scenario Outline: An invalid postal code is rejected
    Given the address provider is <provider>
    When the customer inquires an invalid postal code
    Then the postal-code inquiry is rejected

    Examples:
      | provider |
      | jibit    |
      | sitaad   |


  @KYC-T1125 @regression @positive @high
  Scenario: A repeat postal-code inquiry is served from cache
    Given the address provider is jibit
    When the customer inquires a valid postal code twice
    Then the postal-code inquiry succeeds
    And the first postal-code journal was live and the latest was cached


  @KYC-T1124 @regression @negative @medium
  Scenario Outline: Address provider weights that break the rules are rejected
    Given the live address provider weights are recorded
    When staff submit invalid address provider weights for <rule>
    Then the address provider settings are rejected as <title>

    Examples:
      | rule               | title                        |
      | a weight above one | INVALID_PARAMETER            |
      | a weight below one | KYC_SETTING_VALIDATION_ERROR |
      | a sum below one    | KYC_SETTING_VALIDATION_ERROR |
      | a sum above one    | KYC_SETTING_VALIDATION_ERROR |
      | all weights zero   | KYC_SETTING_VALIDATION_ERROR |
