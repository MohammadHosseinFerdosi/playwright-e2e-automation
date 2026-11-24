@GL-3530 @api @regression @gl @gl_incoming_transactions
Feature: GL incoming financial transactions


  @GL-T311 @positive @high
  Scenario Outline: An incoming transaction is saved in the ledger
    Given a GL administrator is logged in
    When a <transaction type> transaction is created
    Then the transaction must be present in the Transaction table
    And the transaction must be present in the Voucher table
    And the transaction must be present in the Article table

    Examples:
      | transaction type  |
      | credit purchase   |
      | credit prepayment |
      | refund            |


  @GL-T310 @positive @high
  Scenario Outline: An incoming transaction is saved with the requested amount
    Given a GL administrator is logged in
    When a <transaction type> transaction is created
    Then the transaction amount must match the requested amount

    Examples:
      | transaction type  |
      | credit purchase   |
      | credit prepayment |
      | refund            |
