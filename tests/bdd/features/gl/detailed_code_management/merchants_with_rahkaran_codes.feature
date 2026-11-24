@GL-3530 @api @regression @gl @gl_merchants_rahkaran_codes
Feature: GL merchants with Rahkaran codes


  @GL-T306 @positive @high
  Scenario: All Rahkaran codes must consist of exactly six digits
    Given the current merchants with Rahkaran codes
    Then all Rahkaran codes must consist of exactly six digits


  @GL-T305 @positive @high @pii
  Scenario: Merchants with the same national code must have identical Rahkaran codes
    Given the current merchants with Rahkaran codes
    Then merchants with the same national code must have identical Rahkaran codes


  @GL-T304 @positive @medium
  Scenario Outline: Merchants with Rahkaran codes can be filtered
    Given the current merchants with Rahkaran codes
    When the merchants with Rahkaran codes are filtered by <filter field>
    Then the filtered merchants with Rahkaran codes must contain the <filter field>

    Examples:
      | filter field    |
      | business name   |
      | rahkaran code   |
      | account number  |


  @GL-T303 @positive @high @pii
  Scenario: All merchants must have a national code
    Given the current merchants with Rahkaran codes
    Then all merchants must have a national code
