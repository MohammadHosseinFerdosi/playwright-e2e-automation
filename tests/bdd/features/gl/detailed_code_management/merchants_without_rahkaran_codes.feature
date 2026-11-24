@GL-3530 @api @regression @gl @gl_merchants_without_rahkaran_codes
Feature: GL merchants without Rahkaran codes


  @GL-T309 @positive @high
  Scenario: No merchant in the unassigned list has a Rahkaran code assigned
    Given the current merchants without Rahkaran codes
    Then none of them have a Rahkaran code assigned


  @GL-T308 @positive @medium
  Scenario: Merchants without Rahkaran codes can be filtered by business name
    Given the current merchants without Rahkaran codes
    When the merchants without Rahkaran codes are filtered by business name
    Then the filtered merchants without Rahkaran codes must contain the business name


  @GL-T307 @positive @high
  Scenario: Suspending a merchant removes it from the unassigned list and adds it to the suspended list
    Given the current merchants without Rahkaran codes
    And a merchant without a Rahkaran code
    When the merchant is suspended
    Then the merchant no longer appears in the unassigned merchants list
    And the merchant appears in the suspended merchants list
