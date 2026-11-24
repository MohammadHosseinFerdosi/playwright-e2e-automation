@api @regression @payment @payment_health_check @positive @high
Feature: Payment gateway health check

  Scenario: A business token can access the health check service
    Given a Platform business access token
    When the health check service is called with that token
    Then the health check reports the service as active
