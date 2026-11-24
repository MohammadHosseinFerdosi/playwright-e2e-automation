@WAL-362 @api @debit @debit_mellat_gateway
Feature: Mellat internal bank-transfer gateway

  @SET-T476 @smoke @positive @medium
  Scenario: Mellat QA environment is ready
    Given cash-out goes through Mellat
    When DSH runs the bank-transfer environment preflight
    Then the bank-transfer environment preflight succeeds


  @SET-T477 @smoke @positive @medium
  Scenario: Mellat internal gateway client is active in routing
    Given cash-out goes through Mellat
    When DSH checks that the Mellat internal gateway client is active
    Then the Mellat internal gateway client is active


  @SET-T478 @smoke @positive @medium
  Scenario: Customer route contract lands on Mellat internal
    Given cash-out goes through Mellat
    When a customer routes a safe-amount Mellat transfer
    Then the Mellat route contract includes a route journal


  @SET-T479 @regression @positive @high
  Scenario: Duplicate route keeps a single transfer row
    Given cash-out goes through Mellat
    When a customer routes the same Mellat tracking code twice
    Then duplicate Mellat routes keep a single transfer row


  @SET-T480 @smoke @positive @medium
  Scenario: Routed Mellat internal cash-out matches mongo
    Given cash-out goes through Mellat
    When a customer routes a safe-amount Mellat transfer
    Then the Mellat internal route matches mongo


  @SET-T481 @smoke @positive @medium
  Scenario: Marker amount route stays initiated
    Given cash-out goes through Mellat
    When a customer routes a marker-amount Mellat transfer only
    Then the marker Mellat route stays initiated


  @SET-T482 @smoke @positive @high
  Scenario: Internal Mellat route fee is zero
    Given cash-out goes through Mellat
    When a customer routes a safe-amount Mellat transfer
    Then the Mellat internal route fee is zero


  @SET-T483 @smoke @negative @medium
  Scenario: Zero amount Mellat route is rejected
    Given cash-out goes through Mellat
    When a customer routes a Mellat transfer with zero amount
    Then the call is rejected as invalid input


  @SET-T484 @smoke @negative @medium
  Scenario: Bad IBAN Mellat route is rejected
    Given cash-out goes through Mellat
    When a customer routes a Mellat transfer with bad iban
    Then the call is rejected as invalid input


  @SET-T485 @smoke @negative @medium
  Scenario: Injection-style owner name does not cause a server error
    Given cash-out goes through Mellat
    When a customer routes a Mellat transfer with injection owner
    Then the Mellat call does not return a server error


  @SET-T486 @smoke @negative @medium
  Scenario: Transfer without a prior route is rejected
    Given cash-out goes through Mellat
    When a customer executes a Mellat transfer without routing first
    Then the call is rejected because the transfer was not found


  @SET-T487 @smoke @negative @medium
  Scenario: Inquiry for an unknown tracking code is rejected
    Given cash-out goes through Mellat
    When a customer inquires an unknown Mellat tracking code
    Then the call is rejected because the transfer was not found


  @SET-T488 @smoke @negative @medium
  Scenario: Mellat route without tracking code is rejected
    Given cash-out goes through Mellat
    When a customer routes a Mellat transfer with missing tracking
    Then the call is rejected as invalid input


  @SET-T489 @smoke @positive @high
  Scenario: Mellat cash-out never selects ACH
    Given cash-out goes through Mellat
    When a customer routes several Mellat transfers
    Then none of the Mellat routes select ACH


  @SET-T490 @regression @positive @high
  Scenario: Duplicate tracking with a different IBAN stays one row
    Given cash-out goes through Mellat
    When a customer reuses a Mellat tracking code with a different IBAN
    Then the duplicate IBAN Mellat route keeps a single transfer row


  @SET-T491 @smoke @positive @medium
  Scenario: ACH scheduler test triggers return OK
    Given cash-out goes through Mellat
    When DSH triggers the ACH scheduler test endpoints
    Then the ACH scheduler test triggers succeed


  @SET-T492 @smoke @positive @medium
  Scenario: Same-bank IBAN stays internal on Mellat
    Given cash-out goes through Mellat
    When a customer routes a same-bank Mellat transfer
    Then the same-bank Mellat route stays internal
