@api @regression @wallet @wallet_transfer
Feature: Customer wallet transfer


  @positive @high
  Scenario: Customer transfers wallet balance to another customer
    Given a funded source customer and a destination customer
    When the source customer transfers a valid amount to the destination
    Then the source wallet balance decreases by the transfer amount
    And the destination wallet balance increases by the transfer amount


  @negative @medium
  Scenario Outline: Customer wallet transfer is rejected for invalid input
    Given a funded source customer and a destination customer
    When the source customer attempts a transfer that is <condition>
    Then the transfer is rejected with <expected outcome>

    Examples:
      | condition                      | expected outcome             |
      | an invalid source              | incorrect member cell        |
      | an invalid destination         | incorrect member cell        |
      | under the minimum amount       | out of limit                 |
      | over the maximum amount        | insufficient balance         |
      | an invalid amount              | incorrect input data         |
      | the same wallet as destination | same wallet                  |
      | a non-cashoutable amount       | ticket rejection             |
