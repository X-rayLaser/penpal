import time
from behave import given, when, then, step
from selenium.webdriver.common.by import By
from selenium.webdriver.common import keys
from selenium.webdriver.common.action_chains import ActionChains



@when('user fills out and sends the form for a new system message "selenium_message"')
def step_impl(context):
    text_field = context.browser.find_element(by=By.ID, value="formSystemMessageText")
    text_field.send_keys("some text for system message")
    name_field = context.browser.find_element(by=By.ID, value="formSystemMessageName")
    name_field.send_keys("selenium_message")
    name_field.send_keys(keys.Keys.ENTER)
    time.sleep(1)


@then('user can see the system message "selenium_message" that was created')
def step_impl(context):
    headers = context.browser.find_elements(by=By.CLASS_NAME, value="card-header")

    obj = None
    for header in headers:
        print(header, header.text)

        if header.text == "selenium_message":
            obj = header
    
    assert obj is not None
