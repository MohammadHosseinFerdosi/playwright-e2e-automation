@KYC-2163 @api @kyc @kyc_promissory @kyc_promissory_note
Feature: Promissory note issuance and refund

  @KYC-T1092 @smoke @negative @medium
  Scenario: Customer cannot look up a note that does not exist
    Given the customer has a new promissory tracking code
    When the customer asks for that promissory note
    Then the promissory note is not found


  @KYC-T1091 @smoke @positive @high
  Scenario: Customer routing a Saderat note is assigned to Saderat and can start it
    Given routing is set to Saderat
    And the customer has a new promissory tracking code
    When the customer routes that note to Saderat
    Then the note is assigned to the Saderat provider
    And renew is available for that note
    When the customer starts that promissory note
    Then the promissory action start succeeds


  @KYC-T1090 @smoke @positive @high
  Scenario: Administrator cancels an issued promissory note
    Given an issued promissory note exists
    When an administrator cancels the promissory note
    Then the promissory action cancel completes successfully
    And the promissory note is canceled


  @KYC-T1089 @regression @negative @medium
  Scenario: Customer cannot refund an unpaid issued note
    Given an issued promissory note exists
    When the customer requests a refund for the promissory note
    Then the refund is rejected for the note status


  @KYC-T1088 @regression @negative @medium
  Scenario: Customer cannot refund a paid note with no payment record
    Given an issued promissory note is marked paid without a payment
    When the customer requests a refund for the promissory note
    Then the refund is rejected because payment was not found
