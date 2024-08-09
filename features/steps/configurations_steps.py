import time
from behave import given, when, then, step
from selenium.webdriver.common.by import By
from selenium.webdriver.common import keys
from selenium.webdriver.common.action_chains import ActionChains


@when('user fills out the form for new configuration "selenium_configuration"')
def step_impl(context):
    name_field = context.browser.find_element(by=By.ID, value="new_configuration_name")
    name_field.send_keys("selenium_configuration")
    name_field.send_keys(keys.Keys.ENTER)
    time.sleep(2)


@then('user can see the configuration "selenium_configuration" that was created')
def step_impl(context):
    headers = context.browser.find_elements(by=By.CLASS_NAME, value="card-header")

    obj = None
    for h in headers:

        if h.text == "selenium_configuration":
            obj = h
    
    assert obj is not None


@when('user deletes the configuration "selenium_configuration"')
def step_impl(context):
    time.sleep(5)
    button = context.browser.find_element(by=By.CLASS_NAME, value="btn-danger")

    ActionChains(context.browser).move_to_element(button).click().perform()


@then('user cannot see any configurations on the page')
def step_impl(context):
    time.sleep(1)
    buttons = context.browser.find_elements(by=By.CLASS_NAME, value="card-header")
    assert len(buttons) == 0
