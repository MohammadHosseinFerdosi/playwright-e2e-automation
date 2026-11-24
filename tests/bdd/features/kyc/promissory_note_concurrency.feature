@KYC-2163 @api @regression @kyc @kyc_promissory @kyc_promissory_concurrency
Feature: Promissory note concurrent access

  @KYC-T1113 @positive @high
  Scenario: Parallel routing for one code does not create duplicates
    Given the customer has a new promissory tracking code
    When concurrent route requests are issued for that code
    Then each concurrent response is a known business result
    And exactly one promissory note exists for that tracking code


  @KYC-T1112 @positive @high
  Scenario: Parallel cancel requests settle on canceled
    Given a promissory note has been routed successfully
    When concurrent admin cancel requests are issued
    Then each concurrent response is a known business result
    And at least one cancel succeeds
    And the promissory note is canceled


  @KYC-T1111 @positive @medium
  Scenario: Parallel inquiry stays available under load
    Given an issued promissory note exists
    When concurrent inquiry requests are issued
    Then the concurrent inquiries remain available


  @KYC-T1110 @negative @medium
  Scenario: Parallel cancel of an unknown note is not found
    Given the customer has a new promissory tracking code
    When concurrent admin cancel requests are issued
    Then each concurrent response is note not found


  @KYC-T1109 @negative @medium
  Scenario: Parallel inquiry of a missing note is not found
    Given the customer has a new promissory tracking code
    When concurrent inquiry requests are issued
    Then each concurrent response is note not found
