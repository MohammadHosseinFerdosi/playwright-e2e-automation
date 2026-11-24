@KYC-2163 @api @regression @kyc @kyc_promissory @kyc_promissory_admin
Feature: Promissory note administration

  @KYC-T1119 @positive @medium
  Scenario: Administrator can view provider routing settings
    Given promissory provider routing is configured
    When an administrator opens promissory provider settings
    Then the provider settings include the current configuration


  @KYC-T1118 @positive @medium
  Scenario: Administrator can search settings by recipient
    Given promissory provider routing is configured
    When an administrator searches promissory settings recipients
    Then the settings search includes a recipient list


  @KYC-T1117 @positive @low
  Scenario: Administrator can view provider success rates
    Given promissory provider routing is configured
    When an administrator opens promissory success rates
    Then the success rates are listed


  @KYC-T1116 @positive @low
  Scenario: Administrator can browse success-rate history
    Given promissory provider routing is configured
    When an administrator searches promissory success-rate history
    Then the success-rate history can be browsed page by page


  @KYC-T1115 @negative @medium
  Scenario: Administrator cannot revert status on an unknown note
    Given the customer has a new promissory tracking code
    When an administrator reverts status for that unknown promissory note
    Then the promissory note is not found


  @KYC-T1114 @positive @medium
  Scenario: Administrator can notify a batch that includes unknown codes
    Given the customer has a new promissory tracking code
    When an administrator notifies a generated batch with that unknown code
    Then the promissory action notify request succeeds
