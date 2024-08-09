Feature: Creating a custom system messages

    Scenario: Authenticated user creates
    Given user is authenticated
    When user visits the "/#my-system-messages" page
    And user fills out and sends the form for a new system message "selenium_message"
    And user reloads the "/#my-system-messages" page
    Then user can see the system message "selenium_message" that was created
