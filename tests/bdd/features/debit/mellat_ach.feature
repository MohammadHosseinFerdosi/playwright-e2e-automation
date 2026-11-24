@WAL-362 @api @debit @debit_mellat_ach
Feature: Mellat ACH PAYA bank-transfer

  @SET-T433 @smoke @positive @high
  Scenario: Ordinary cross-bank PAYA routes as a single chunk
    Given cash-out goes through Mellat PAYA
    When a customer routes an ordinary cross-bank PAYA transfer
    Then the PAYA cash-out is a single ACH chunk


  @SET-T434 @smoke @positive @high
  Scenario: Ordinary PAYA inquiry stays routed before execute
    Given cash-out goes through Mellat PAYA
    When a customer routes an ordinary PAYA transfer and inquires it
    Then the PAYA cash-out inquiry stays routed


  @SET-T435 @regression @positive @high
  Scenario: Ordinary PAYA live transfer settles
    Given cash-out goes through Mellat PAYA
    When a customer executes an ordinary PAYA live transfer
    Then the PAYA cash-out live transfer has settled


  @SET-T436 @smoke @positive @high
  Scenario: Batch PAYA splits above the chunk limit
    Given cash-out goes through Mellat PAYA
    When a customer routes a batch cross-bank PAYA transfer
    Then the PAYA cash-out splits into the expected chunks


  @SET-T437 @smoke @positive @high
  Scenario: Batch PAYA inquiry lists split transactions
    Given cash-out goes through Mellat PAYA
    When a customer routes a batch PAYA transfer and inquires it
    Then the PAYA cash-out inquiry lists the split transactions


  @SET-T438 @regression @positive @high
  Scenario: Batch PAYA live transfer settles
    Given cash-out goes through Mellat PAYA
    When a customer executes a batch PAYA live transfer
    Then the PAYA cash-out live transfer has settled


  @SET-T440 @smoke @positive @high
  Scenario: Remainder batch splits into chunk plus one
    Given cash-out goes through Mellat PAYA
    When a customer routes a remainder batch PAYA transfer
    Then the PAYA cash-out splits into the expected chunks


  @SET-T441 @smoke @positive @medium
  Scenario: Ordinary PAYA route fee is zero
    Given cash-out goes through Mellat PAYA
    When a customer routes an ordinary cross-bank PAYA transfer
    Then the PAYA cash-out fee is zero


  @SET-T442 @smoke @positive @medium
  Scenario: Duplicate ACH route keeps a single transfer row
    Given cash-out goes through Mellat PAYA
    When a customer routes the same ACH tracking code twice
    Then duplicate Mellat routes keep a single transfer row


  @SET-T443 @smoke @positive @medium
  Scenario: Concurrent ACH routes keep a single transfer row
    Given cash-out goes through Mellat PAYA
    When customers concurrently route the same ACH tracking code
    Then duplicate Mellat routes keep a single transfer row


  @SET-T444 @smoke @negative @medium
  Scenario: Zero amount PAYA route is rejected
    Given cash-out goes through Mellat PAYA
    When a customer routes a zero-amount PAYA transfer
    Then the call is rejected as invalid input


  @SET-T445 @smoke @negative @high
  Scenario: Same-bank IBAN must not route as ACH
    Given cash-out goes through Mellat PAYA
    When a customer routes a same-bank IBAN on PAYA
    Then the PAYA cash-out same-bank route is not ACH


  @SET-T446 @smoke @positive @high
  Scenario: Triple batch splits into three chunks
    Given cash-out goes through Mellat PAYA
    When a customer routes a triple-chunk batch PAYA transfer
    Then the PAYA cash-out splits into the expected chunks


  @SET-T447 @smoke @positive @medium
  Scenario: Done PAYA inquiry reports transfer success
    Given cash-out goes through Mellat PAYA
    When a customer inquires a recently settled PAYA transfer
    Then the PAYA cash-out settled inquiry succeeds
