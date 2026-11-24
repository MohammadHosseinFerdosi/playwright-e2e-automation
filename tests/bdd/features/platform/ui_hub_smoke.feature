@e2e @smoke @platform @platform_ui_hub
Feature: App hub after API session inject


  @positive @high
  Scenario: Fresh customer lands on the super app hub
    Given a logged-in customer in the app
    When the customer opens the app hub
    Then the customer is on the app hub
