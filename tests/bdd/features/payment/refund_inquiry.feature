@api @regression @payment @payment_refund_inquiry @high
Feature: Purchase refund inquiry


  @positive
  Scenario Outline: A business can look up an existing refund by <id type>
    Given a Platform business access token
    When the refund inquiry <inquiry id> is looked up by <id type>
    Then the refund inquiry request succeeds
    And the returned <id type> matches <inquiry id>
    And the refund destination type is <destination>

    Examples:
      | id type      | inquiry id                           | destination |
      | providerId   | 7ecc14c8-336b-4bf1-a3d2-002a845aa194 | wallet      |
      | trackingCode | 8191843271728811026725               | wallet      |
      | trackingCode | 11988051571593929197689              | iban        |
      | providerId   | 0705103639                           | iban        |


  @negative
  Scenario Outline: Looking up a refund by an unknown <id type> is rejected
    Given a Platform business access token
    When the refund inquiry <inquiry id> is looked up by <id type>
    Then the refund inquiry request is rejected as invalid

    Examples:
      | id type      | inquiry id                                     |
      | providerId   | 1f8d08a1-3c12-4ece-a85c-5aa577575e655620f1d1c6 |
      | trackingCode | 19532rgtr728881673090528677258                 |


  @negative
  Scenario: A different business's token is rejected when looking up by providerId
    Given a Company business access token
    When the refund inquiry 7ecc14c8-336b-4bf1-a3d2-002a845aa194 is looked up by providerId
    Then the refund inquiry request is rejected as invalid


  @positive
  Scenario: A different business's token can still look up by trackingCode
    Given a Company business access token
    When the refund inquiry 11988051571593929197689 is looked up by trackingCode
    Then the refund inquiry request succeeds
