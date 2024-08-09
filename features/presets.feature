Feature: Creating a custom preset

    Scenario: Authenticated user creates and delete a custom preset
    Given user is authenticated
    When user visits the "/#presets" page
    And user fills out the preset form for new preset "selenium_preset"
    And user reloads the "/#presets" page
    Then user can see the preset "selenium_preset" that was created
    When user deletes the preset "selenium_preset"
    And user reloads the "/#presets" page
    Then user cannot see any preset on the page
