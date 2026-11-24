@KYC-2206 @api @regression @kyc @kyc_promissory @kyc_promissory_renew
Feature: Promissory note Kuknos renew

  @KYC-T1146 @negative @high
  Scenario: Customer cannot renew a rejected note
    Given a Kuknos Tejarat note is rejected
    When the customer starts that promissory note
    Then the promissory start is rejected for the note status
    And the promissory note was not renewed

  @KYC-T1145 @negative @high
  Scenario: Customer cannot renew a paid note when renew is turned off
    Given a Kuknos Tejarat note is paid with renew turned off
    When the customer starts that promissory note
    Then the promissory start is rejected for the note status
    And the promissory note was not renewed
