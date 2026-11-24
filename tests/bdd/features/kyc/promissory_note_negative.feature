@KYC-2163 @api @regression @kyc @kyc_promissory @kyc_promissory_negative
Feature: Promissory note rejected requests

  @KYC-T1106 @negative @medium
  Scenario: Routing without a requesting business is rejected
    Given the customer has a new promissory tracking code
    When the customer routes that note without a requesting business
    Then the promissory request routing without a requesting business is rejected


  @KYC-T1105 @negative @medium
  Scenario: Routing to an unsupported recipient is rejected
    Given the customer has a new promissory tracking code
    When the customer routes that note to an unsupported recipient
    Then the promissory request routing to an unsupported recipient is rejected


  @KYC-T1104 @negative @medium
  Scenario Outline: Starting a note without a required detail is rejected
    Given the customer has a new promissory tracking code
    When the customer starts a promissory note without <detail>
    Then starting without <detail> is rejected

    Examples:
      | detail        |
      | tracking code |
      | owner         |
      | iban          |
      | amount        |


  @KYC-T1103 @negative @medium
  Scenario: Starting a note with a non-numeric amount is rejected
    Given the customer has a new promissory tracking code
    When the customer starts a promissory note with a non-numeric amount
    Then the promissory request starting with a non-numeric amount is rejected


  @KYC-T1101 @negative @medium
  Scenario: Customer cannot cancel an unknown note
    Given the customer has a new promissory tracking code
    When the customer cancels that promissory note
    Then the promissory note is not found


  @KYC-T1100 @negative @medium
  Scenario: Customer cannot sign an unknown note without a ticket
    Given the customer has a new promissory tracking code
    When the customer requests a signature without a ticket
    Then the promissory request signature without a ticket is rejected


  @KYC-T1099 @negative @medium
  Scenario: Customer cannot seal a note without a sign reference
    Given the customer has a new promissory tracking code
    When the customer seals that note without a sign reference
    Then the request is rejected as invalid


  @KYC-T1098 @negative @medium
  Scenario: Customer cannot refund an unknown note
    Given the customer has a new promissory tracking code
    When the customer requests a refund for the promissory note
    Then the promissory note is not found


  @KYC-T1097 @positive @low
  Scenario: Starting a routed note with an oversized description succeeds
    Given a promissory note has been routed successfully
    When the customer starts a promissory note with an oversized description
    Then the promissory action start with an oversized description succeeds
