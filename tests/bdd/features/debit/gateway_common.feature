@WAL-362 @api @smoke @debit @debit_gateway_common
Feature: Bank-transfer gateway routing

  @SET-T404 @positive @high
  Scenario: Zero weights block routing then succeed when Mellat is pinned
    Given cash-out goes through Mellat
    When DSH clears every cash-out gateway weight then pins Mellat
    Then routing is blocked with no gateway and then succeeds on Mellat


  @SET-T405 @negative @medium
  Scenario: An inactive bank client cannot be selected for routing
    Given cash-out goes through Mellat
    When DSH deactivates the bank client used for routing
    And a customer requests a bank transfer route
    Then the route is rejected because no gateway is available


  @SET-T406 @positive @medium
  Scenario: Inquiry after a successful route reports the active gateway
    Given cash-out goes through Mellat
    When a customer routes a bank transfer
    And the customer inquires that transfer
    Then the inquiry reports the active gateway


  @SET-T407 @positive @medium
  Scenario: Inquiry without executing the transfer leaves it initiated
    Given cash-out goes through Mellat
    When a customer routes a bank transfer
    And the customer inquires without executing the transfer
    Then the transfer remains initiated without a transfer journal
