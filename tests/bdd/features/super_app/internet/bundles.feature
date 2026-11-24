@api @regression @internet @internet_bundles
Feature: Internet bundle catalog


  @ALPHA-T2232 @positive @high
  Scenario: Customer requests the internet bundle catalog for MCI
    Given a Platform business access token
    And a random cell number for operator id "1"
    When the bundle catalog is requested for operator id "1" using the random cell number
    Then the bundle catalog is returned successfully


  @ALPHA-T2231 @positive @high
  Scenario Outline: Internet bundle catalog is available for every mobile operator
    Given a Platform business access token
    And a random cell number for operator id "<operator id>"
    When the bundle catalog is requested for operator id "<operator id>" using the random cell number
    Then the bundle catalog is returned successfully

    Examples:
      | operator id | operator name |
      | 1           | MCI            |
      | 2           | MTN            |
      | 3           | RIGHTEL        |
      | 4           | SHATEL         |


  @ALPHA-T2230 @positive @high
  Scenario Outline: Bundle catalog includes a guaranteed category
    Given a Platform business access token
    And a random cell number for any operator with a default catalog
    When the bundle catalog is requested using the random cell number
    Then the bundle catalog includes the "<category key>" category

    Examples:
      | category key |
      | DAILY         |
      | WEEKLY        |
      | MONTHLY       |


  @ALPHA-T2229 @positive @medium
  Scenario: Every internet package has a non-empty bundle id
    Given a Platform business access token
    And a random cell number for any operator
    When the bundle catalog is requested using the random cell number
    Then every internet package has a non-empty bundle id


  @ALPHA-T2228 @positive @medium
  Scenario: Every internet package has a positive amount
    Given a Platform business access token
    And a random cell number for any operator
    When the bundle catalog is requested using the random cell number
    Then every internet package has a positive amount


  @ALPHA-T2227 @positive @medium
  Scenario: Every internet package's raw amount is within its amount
    Given a Platform business access token
    And a random cell number for any operator
    When the bundle catalog is requested using the random cell number
    Then every internet package's raw amount is positive and does not exceed its amount


  @ALPHA-T2226 @positive @medium
  Scenario: Every internet package has a non-empty description
    Given a Platform business access token
    And a random cell number for any operator
    When the bundle catalog is requested using the random cell number
    Then every internet package has a non-empty description


  @ALPHA-T2225 @positive @medium
  Scenario: Every internet package has a positive duration
    Given a Platform business access token
    And a random cell number for any operator
    When the bundle catalog is requested using the random cell number
    Then every internet package has a positive duration


  @ALPHA-T2224 @positive @medium
  Scenario: No bundle section lists a duplicate package
    Given a Platform business access token
    And a random cell number for any operator
    When the bundle catalog is requested using the random cell number
    Then no bundle section lists a duplicate package


  @ALPHA-T2223 @positive @medium
  Scenario: Approval-required packages carry an approval message
    Given a Platform business access token
    And a random cell number for any operator
    When the bundle catalog is requested using the random cell number
    Then every package that needs approval carries an approval message


  @ALPHA-T2222 @positive @medium
  Scenario: Popular category only lists packages that exist elsewhere in the catalog
    Given a Platform business access token
    And a random cell number for any operator
    When the bundle catalog is requested using the random cell number
    Then the "POPULAR" category only lists packages that also exist in another category


  @ALPHA-T2221 @positive @medium
  Scenario: All category is the deduplicated union of the other categories
    Given a Platform business access token
    And a random cell number for any operator
    When the bundle catalog is requested using the random cell number
    Then the "ALL" category is the deduplicated union of the other categories


  @ALPHA-T2220 @positive @medium
  Scenario Outline: Bundle type reflects the requested SIM card type
    Given a Platform business access token
    And a random cell number for SIM type "<sim card type>"
    When the bundle catalog is requested using the random cell number
    Then every bundle type matches the requested SIM type

    Examples:
      | sim card type |
      | POSTPAID       |
      | PREPAID        |
      | DATA           |


  @ALPHA-T2219 @positive @high
  Scenario Outline: Bundle catalog succeeds for a random number per operator and SIM type
    Given a Platform business access token
    And a random cell number for operator id "<operator id>" and SIM type "<sim card type>"
    When the bundle catalog is requested using the random cell number
    Then the bundle catalog request succeeds for the random number

    Examples:
      | operator id | sim card type |
      | 1           | POSTPAID      |
      | 1           | PREPAID       |
      | 2           | POSTPAID      |
      | 2           | PREPAID       |
      | 2           | DATA          |
      | 3           | POSTPAID      |
      | 3           | PREPAID       |
      | 3           | DATA          |
      | 4           | PREPAID       |


  @ALPHA-T2218 @negative @medium
  Scenario: Bundle catalog request without a valid token is rejected
    Given no valid access token
    And a random cell number
    When the bundle catalog is requested without a valid token
    Then the bundle catalog request is rejected as unauthorized


  @ALPHA-T2217 @negative @medium
  Scenario Outline: Bundle catalog request with an unsupported operator id is rejected
    Given a Platform business access token
    And a random cell number for any operator
    When the bundle catalog is requested for operator id "<operator id>" using the random cell number
    Then the bundle catalog request does not succeed

    Examples:
      | operator id |
      | 0            |
      | 5            |
      | 999          |


  @ALPHA-T2216 @negative @medium
  Scenario Outline: Bundle catalog request with a mismatched operator id and cell number
    Given a Platform business access token
    When the bundle catalog is requested for operator id "<operator id>" cell "<cell number>"
    Then the bundle catalog request is handled gracefully

    Examples:
      | operator id | cell number |
      | 1           | 09300000000 |
      | 2           | 09212222222 |
      | 3           | 09981234567 |
      | 4           | 09905555555 |


  @ALPHA-T2215 @negative @medium
  Scenario Outline: Bundle catalog request rejects a malformed cell number
    Given a Platform business access token
    When the bundle catalog is requested for operator id "1" cell "<cell number>"
    Then the bundle catalog request is handled gracefully

    Examples:
      | cell number    |
      | 091244         |
      | 09124445456789 |
      | 9124445456     |
      | 0912abc5456    |
      | 02112345678    |
      |                |


  @ALPHA-T2214 @negative @medium
  Scenario Outline: Bundle catalog request handles edge-case SIM card type values
    Given a Platform business access token
    When the bundle catalog is requested with cellNumberType "<cell number type>"
    Then the bundle catalog request is handled gracefully

    Examples:
      | cell number type |
      | 0                 |
      | 4                 |
      | 99                |
      | abc               |
      |                   |
