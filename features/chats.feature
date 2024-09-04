Feature: Creating a chat and chatting

    Scenario: Authenticated user creates and delete a chat
    Given user is authenticated
    When user visits the "/#configurations" page
    And user fills out the form for new configuration "selenium_configuration"
    And user visits the "/#my-chats" page
    And user creates a new chat
    And user visits the "/#my-chats" page
    Then user can see a new chat appearing
    When user deletes the chat
    And user reloads the "/#my-chats" page
    Then user cannot see any chats on the page

    @ws
    Scenario: Authenticated user creates chat, sends text message to AI and receives a response
    Given user is authenticated
    When user visits the "/#configurations" page
    And user fills out the form for new configuration "selenium_configuration"
    And user visits the "/#my-chats" page
    And user creates a new chat
    And user sends a text message "hello world!" to AI
    And user waits for "1" seconds
    Then user can see their text message
    When user waits for "5" seconds
    Then user can see a response from an AI

    @ws
    Scenario: Authenticated user creates chat, sends text message to AI and receives a response and regenerates it
    
    Given user is authenticated
    When user visits the "/#configurations" page
    And user fills out the form for new configuration "selenium_configuration"
    And user visits the "/#my-chats" page
    And user creates a new chat
    And user sends a text message "hello world!" to AI
    And user waits for "5" seconds
    And user clicks "Regenerate" button
    And user waits for "5" seconds
    Then user can see their text message
    And user can see two responses from AI