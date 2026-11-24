@KYC-2050 @api @kyc @kyc_digital_signature
Feature: Native digital signature after liveness


  @KYC-T1087 @smoke @positive @high
  Scenario: Customer initiates a digital signature after completed liveness
    Given the customer has completed native liveness
    When the customer initiates a basic digital signature
    Then the digital signature initiate succeeds with a provider tracking code
    And the provider signature record is pending for that provider tracking code


  @KYC-T1086 @smoke @positive @high
  Scenario: Customer generates a certificate after a successful initiate
    Given the customer has completed native liveness
    And the customer has initiated a basic digital signature
    When the customer generates the digital signature certificate
    Then the digital signature generate succeeds
    And the provider signature record is initiated for that signature tracking code


  @KYC-T1085 @regression @positive @high
  Scenario: Customer revokes a generated digital signature
    Given the customer has a generated digital signature
    When the customer revokes the digital signature
    Then the digital signature revoke succeeds
    And the provider signature record is revoked for that signature tracking code


  @KYC-T1084 @regression @positive @high
  Scenario: Customer validates the password after generate
    Given the customer has a generated digital signature
    When the customer validates the digital signature password
    Then the digital signature validate password succeeds


  @KYC-T1083 @regression @negative @high
  Scenario Outline: Generate is rejected when liveness is incomplete
    Given the customer has <liveness prep> for digital signature
    And the customer has initiated a basic digital signature
    When the customer generates the digital signature certificate
    Then the digital signature generate reports incomplete liveness

    Examples:
      | liveness prep              |
      | only registered liveness   |
      | signature without selfie   |
      | selfie without video       |


  @KYC-T1082 @regression @negative @high
  Scenario: Initiate basic without a password is rejected
    Given the customer has completed native liveness
    When the customer initiates a basic digital signature without a password
    Then the digital signature initiate reports a bad request


  @KYC-T1081 @regression @negative @high
  Scenario: Validate password without a generated signature is rejected
    Given the customer has completed native liveness
    And the customer has initiated a basic digital signature
    When the customer validates the digital signature password
    Then the digital signature validate password reports signature not found


  @KYC-T1080 @regression @negative @high
  Scenario: Validate password with a wrong password is rejected
    Given the customer has a generated digital signature
    When the customer validates a wrong digital signature password
    Then the digital signature validate password reports a password mismatch
