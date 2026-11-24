@KYC-2163 @api @regression @kyc @kyc_promissory @kyc_promissory_mass
Feature: Promissory note protected attributes

  @KYC-T1108 @negative @high
  Scenario: Customer cannot force protected attributes while routing
    Given the customer has a new promissory tracking code
    When the customer routes that note with protected attributes set by the client
    Then the note does not keep those protected attributes from routing


  @KYC-T1107 @negative @high
  Scenario: Customer cannot force protected attributes while starting a note
    Given a promissory note has been routed successfully
    When the customer starts a promissory note with protected attributes set by the client
    Then the note does not keep those protected attributes from starting
