@e2e @smoke @wealth @wealth_silver_trade
Feature: Customer buys and sells silver


  @positive @high
  Scenario: Customer cancels a silver purchase at the payment gateway
    Given a logged-in customer with an existing silver wallet
    When the customer opens the app hub
    And the customer opens the silver trading screen from the hub
    And the customer views the silver purchase detail
    And the customer opens the silver amount screen
    And the customer submits a silver purchase amount
    And the customer confirms and pays for the silver purchase
    And the customer cancels the payment at the gateway
    Then the customer is redirected to the silver purchase receipt
    And the receipt shows the operation failed
    And the receipt shows the silver purchase description


  @positive @high
  Scenario: Customer sells silver and the sale is pending settlement
    Given a logged-in customer with an existing silver wallet
    When the customer opens the app hub
    And the customer opens the silver trading screen from the hub
    And the customer opens the silver sell amount screen
    And the customer submits a silver sale amount
    And the customer confirms the default bank account
    And the customer confirms the silver sale
    Then the customer is redirected to the silver sale receipt
    And the receipt shows the operation pending


  @positive @medium
  Scenario: Customer sees the silver tab's available actions
    Given a logged-in customer in the app
    When the customer opens the app hub
    And the customer opens the silver trading screen from the hub
    Then the buy action is available on the silver tab
    And the transactions action is available on the silver tab
    And the request credit action is available on the silver tab
    And the silver wealth bag action is available on the silver tab
    And the convert action is available on the silver tab
    And the convert action is disabled while the customer holds no silver
    And the sell action is available on the silver tab
    And the sell action is disabled while the customer holds no silver


  @positive @medium
  Scenario Outline: Customer opens an action from the silver tab
    Given a logged-in customer in the app
    When the customer opens the app hub
    And the customer opens the silver trading screen from the hub
    And the customer opens <silver tab action> from the silver tab
    Then the customer is redirected to the destination for <silver tab action>

    Examples:
      | silver tab action |
      | buy               |
      | transactions      |
      | request credit    |
      | silver wealth bag |
