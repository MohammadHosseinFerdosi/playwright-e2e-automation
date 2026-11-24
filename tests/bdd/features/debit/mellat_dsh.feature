@WAL-362 @api @debit @debit_mellat_dsh
Feature: Mellat DSH

  @SET-T448 @smoke @negative @high
  Scenario: Cross-bank IBANs are rejected on Mellat internal
    Given cash-out goes through Mellat
    When the customer requests Mellat cash-outs to IBANs from other banks
    Then the Mellat cash-out is rejected for a cross-bank IBAN


  @SET-T449 @smoke @negative @high
  Scenario: Hostile owner names do not cause a server error
    Given cash-out goes through Mellat
    When the customer requests Mellat cash-outs with hostile owner names
    Then the Mellat cash-out probes do not return a server error


  @SET-T450 @smoke @negative @high
  Scenario: SQL-like descriptions do not cause a server error
    Given cash-out goes through Mellat
    When the customer requests a Mellat cash-out with a SQL-like description
    Then the Mellat cash-out does not return a server error


  @SET-T451 @smoke @negative @high
  Scenario: Injection tracking codes do not leak on inquiry
    Given cash-out goes through Mellat
    When the customer inquires Mellat transfers with injection tracking codes
    Then the Mellat cash-out inquiries do not leak transfer data


  @SET-T453 @smoke @negative @high
  Scenario: An oversized route payload does not cause a server error
    Given cash-out goes through Mellat
    When the customer requests a Mellat cash-out with an oversized payload
    Then the Mellat cash-out does not return a server error


  @SET-T454 @smoke @negative @medium
  Scenario: A decimal amount is handled safely
    Given cash-out goes through Mellat
    When the customer requests a Mellat cash-out with a decimal amount
    Then the Mellat cash-out is handled


  @SET-T455 @smoke @negative @medium
  Scenario: A negative amount is rejected
    Given cash-out goes through Mellat
    When the customer requests a Mellat cash-out with a negative amount
    Then the Mellat cash-out is rejected


  @SET-T456 @smoke @negative @medium
  Scenario: An IBAN with spaces is handled
    Given cash-out goes through Mellat
    When the customer requests a Mellat cash-out to an IBAN with spaces
    Then the Mellat cash-out is handled


  @SET-T457 @regression @negative @high
  Scenario: Duplicate route with a different amount is rejected
    Given cash-out goes through Mellat
    When the customer reuses a Mellat tracking code with a different amount
    Then the Mellat cash-out is rejected


  @SET-T458 @regression @positive @high
  Scenario: Duplicate route keeps a single transfer
    Given cash-out goes through Mellat
    When the customer routes the same Mellat tracking code twice
    Then duplicate Mellat dashboard routes keep a single transfer row


  @SET-T459 @smoke @negative @medium
  Scenario: Cash-out without an IBAN is rejected
    Given cash-out goes through Mellat
    When the customer requests a Mellat cash-out without an IBAN
    Then the Mellat cash-out is rejected


  @SET-T460 @smoke @negative @medium
  Scenario: A string amount is handled
    Given cash-out goes through Mellat
    When the customer requests a Mellat cash-out with a string amount
    Then the Mellat cash-out is handled


  @SET-T461 @smoke @negative @medium
  Scenario: The minimum amount boundary is handled
    Given cash-out goes through Mellat
    When the customer requests a Mellat cash-out at the minimum amount
    Then the Mellat cash-out is handled


  @SET-T462 @regression @positive @high
  Scenario: Weight switch then live transfer settles
    Given cash-out goes through Mellat
    When DSH switches Mellat weights and the customer executes a live cash-out
    Then the Mellat cash-out settles


  @SET-T463 @regression @positive @high
  Scenario: Production route then transfer settles
    Given cash-out goes through Mellat
    When the customer executes a production-style Mellat cash-out
    Then the Mellat cash-out settles


  @SET-T464 @regression @negative @high
  Scenario: The max client amount is enforced
    Given cash-out goes through Mellat
    When the customer requests a Mellat cash-out above the client maximum
    Then the Mellat cash-out is enforced


  @SET-T465 @regression @negative @high
  Scenario: Concurrent duplicate execute does not double pay
    Given cash-out goes through Mellat
    When customers concurrently execute the same Mellat cash-out
    Then the Mellat cash-out concurrent executes do not double pay


  @SET-T466 @regression @negative @high
  Scenario: Duplicate transfer execute is rejected
    Given cash-out goes through Mellat
    When the customer executes the same Mellat cash-out twice
    Then the Mellat cash-out is rejected


  @SET-T467 @regression @positive @high
  Scenario: Transfer after route leaves the cash-out in progress
    Given cash-out goes through Mellat
    When the customer executes a Mellat cash-out after routing
    Then the Mellat cash-out is in progress after transfer


  @SET-T468 @smoke @positive @medium
  Scenario: Mellat statement APIs succeed
    Given cash-out goes through Mellat
    When DSH requests Mellat statement APIs
    Then the Mellat cash-out statement APIs succeed


  @SET-T469 @regression @positive @medium
  Scenario: Creditor PAYA statement rows have amounts
    Given cash-out goes through Mellat
    When DSH reads Mellat creditor PAYA statement rows
    Then the Mellat cash-out creditor PAYA statement rows have non-zero amounts


  @SET-T470 @regression @negative @medium
  Scenario: Invalid statement dates are rejected
    Given cash-out goes through Mellat
    When DSH requests Mellat statements with invalid dates
    Then the Mellat cash-out invalid statement dates are rejected


  @SET-T471 @regression @negative @medium
  Scenario: Invalid account-statement dates are rejected
    Given cash-out goes through Mellat
    When DSH requests Mellat account statements with invalid dates
    Then the Mellat cash-out invalid statement dates are rejected


  @SET-T472 @regression @positive @high
  Scenario: Live transfer appears on the provider statement
    Given cash-out goes through Mellat
    When the customer executes a live Mellat cash-out onto the provider statement
    Then the Mellat cash-out appears on the provider statement


  @SET-T473 @regression @positive @medium
  Scenario: Configured done transfer statement amounts hold
    Given cash-out goes through Mellat
    When DSH checks configured Mellat done-transfer statement amounts
    Then the Mellat cash-out configured done-transfer statement amounts hold


  @SET-T474 @regression @positive @medium
  Scenario: Statement pagination size and page are honoured
    Given cash-out goes through Mellat
    When DSH pages through Mellat statements
    Then the Mellat cash-out statement pagination is honoured


  @SET-T475 @regression @positive @high
  Scenario: Live transfer reconciles the ledger and inquiry
    Given cash-out goes through Mellat
    When the customer completes a live Mellat cash-out journey
    Then the Mellat cash-out reconciles across inquiry and the ledger
