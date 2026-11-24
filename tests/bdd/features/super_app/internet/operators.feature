@api @regression @internet @internet_operators
Feature: Top-up operator list


  @ALPHA-T2243 @positive @high
  Scenario: Customer requests the top-up operator list
    Given a Platform business access token
    When the top-up operators list is requested
    Then the operator list is returned successfully


  @ALPHA-T2242 @positive @high
  Scenario Outline: Top-up operator list includes a known operator and operator id
    Given a Platform business access token
    When the top-up operators list is requested
    Then the operator list includes "<operator name>" with operator id "<operator id>"

    Examples:
      | operator name | operator id |
      | MCI            | 1           |
      | MTN            | 2           |
      | RIGHTEL        | 3           |
      | SHATEL         | 4           |


  @ALPHA-T2241 @positive @high
  Scenario Outline: Top-up operator with a given operator id includes a known prefix
    Given a Platform business access token
    When the top-up operators list is requested
    Then operator id "<operator id>" includes prefix "<prefix>"

    Examples:
      | operator id | prefix |
      | 1            | 0912   |
      | 2            | 0935   |
      | 3            | 0920   |
      | 4            | 0998   |


  @ALPHA-T2240 @positive @medium
  Scenario: Every top-up operator prefix declares a type
    Given a Platform business access token
    When the top-up operators list is requested
    Then every operator prefix has at least one type


  @ALPHA-T2239 @positive @high
  Scenario Outline: Operator id has a well-formed, non-empty prefix list
    Given a Platform business access token
    When the top-up operators list is requested
    Then operator id "<operator id>" exists
    And operator id "<operator id>" has a non-empty prefix list
    And every prefix of operator id "<operator id>" is a well-formed mobile prefix

    Examples:
      | operator id |
      | 1           |
      | 2           |
      | 3           |
      | 4           |


  @ALPHA-T2238 @positive @medium
  Scenario: Every operator prefix starts with "09"
    Given a Platform business access token
    When the top-up operators list is requested
    Then every operator prefix starts with "09"


  @ALPHA-T2237 @positive @medium
  Scenario: Every operator prefix is 4 or 5 characters long
    Given a Platform business access token
    When the top-up operators list is requested
    Then every operator prefix is 4 or 5 characters long


  @ALPHA-T2236 @positive @medium
  Scenario: Every operator prefix value is a non-empty string
    Given a Platform business access token
    When the top-up operators list is requested
    Then every operator prefix value is a non-empty string


  @ALPHA-T2235 @positive @medium
  Scenario Outline: Operator id has no duplicate prefixes
    Given a Platform business access token
    When the top-up operators list is requested
    Then operator id "<operator id>" lists no duplicate prefix

    Examples:
      | operator id |
      | 1           |
      | 2           |
      | 3           |
      | 4           |


  @ALPHA-T2234 @positive @medium
  Scenario: No prefix is listed under more than one operator
    Given a Platform business access token
    When the top-up operators list is requested
    Then no prefix is listed under more than one operator


  @ALPHA-T2233 @negative @medium
  Scenario: Top-up operator list request without a valid token is rejected
    Given no valid access token
    When the top-up operators list is requested without a valid token
    Then the request is rejected as unauthorized
