@api @regression @wallet @wallet_balance
Feature: Customer aggregated wallet balance


  @positive @high
  Scenario Outline: Aggregated balance reflects the customer's wallet mix
    Given a logged-in customer with <wallet mix>
    When the customer requests their aggregated balance
    Then the aggregated balances match the expected amounts

    Examples:
      | wallet mix                            |
      | default and time-bound wallets        |
      | only time-bound wallets               |
      | only an expired time-bound wallet     |
      | only a default wallet                 |
      | only a cashoutable default wallet     |
      | only a non-cashoutable default wallet |


  @positive @medium
  Scenario: Aggregated balance is zero when the customer has no wallet
    Given a logged-in customer without any wallet
    When the customer requests their aggregated balance
    Then the aggregated balances match the expected amounts


  @negative @low
  Scenario: Aggregated balance for an unknown user is rejected
    Given an unknown user identity
    When the aggregated balance is requested for an unknown user
    Then the aggregated balance response reports that the user was not found
