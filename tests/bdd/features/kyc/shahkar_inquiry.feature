@KYC-2201 @api @regression @kyc @kyc_shahkar_inquiry
Feature: Shahkar cell-number ownership


  @KYC-T1123 @smoke @positive @high
  Scenario: Customer with a matching cell number is verified
    Given the customer has a matching cell number
    When the customer inquires Shahkar
    Then the Shahkar inquiry is verified


  @KYC-T1122 @positive @high
  Scenario: Cell number that does not belong to the customer is unverified
    Given the customer has a cell number that does not belong to them
    When the customer inquires Shahkar
    Then the Shahkar inquiry is unverified


  @KYC-T1121 @positive @high
  Scenario: A repeat matching inquiry is served from cache
    Given the customer has a matching cell number
    When the customer inquires Shahkar twice
    Then the first Shahkar journal was live and the latest was cached


  @KYC-T1120 @negative @medium
  Scenario Outline: Inquiry is rejected when identity is incomplete or invalid
    Given the customer has a national identity
    When the customer submits a Shahkar inquiry with <fault>
    Then the Shahkar inquiry is rejected

    Examples:
      | fault                    |
      | a missing national code  |
      | a missing cell number    |
      | an invalid national code |
      | an invalid cell number   |
