@KYC-2163 @api @kyc @kyc_promissory @kyc_promissory_lifecycle
Feature: Promissory note lifecycle and provider assignment

  @KYC-T1096 @regression @positive @medium
  Scenario Outline: Customer inquiry shows the note lifecycle stage
    Given an issued promissory note is at stage <stage>
    When the customer asks for that promissory note
    Then the inquiry shows the note at that stage

    Examples:
      | stage     |
      | paid      |
      | signed    |
      | sealed    |
      | confirmed |


  @KYC-T1095 @regression @negative @high
  Scenario: Customer cannot start stamp payment on an ineligible note
    Given an issued promissory note exists
    When the customer starts stamp payment for the note
    Then the payment request is rejected


  @KYC-T1094 @regression @negative @medium
  Scenario: Customer cannot request a signature without a ticket
    Given an issued promissory note exists
    When the customer requests a signature without a ticket
    Then the promissory request signature without a ticket is rejected


  @KYC-T1093 @smoke @positive @high
  Scenario: Customer routing a Tejarat note is assigned to Kuknos and can start it
    Given routing is set to Kuknos for Tejarat
    And the customer has a new promissory tracking code
    When the customer routes that note to Tejarat
    Then the note is assigned to the Kuknos provider
    And renew is available for that note
    When the customer starts that promissory note
    Then the promissory action start succeeds
