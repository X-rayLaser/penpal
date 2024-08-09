Feature: Creating a custom configuration

    Scenario: Authenticated users can create and delete custom configuration
    Given user is authenticated
    When user visits the "/#configurations" page
    And user fills out the form for new configuration "selenium_configuration"
    And user reloads the "/#configurations" page
    Then user can see the configuration "selenium_configuration" that was created
    When user deletes the configuration "selenium_configuration"
    And user reloads the "/#configurations" page
    Then user cannot see any configurations on the page