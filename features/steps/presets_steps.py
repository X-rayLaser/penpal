import time
from behave import given, when, then, step
from selenium.webdriver.common.by import By
from selenium.webdriver.common import keys
from selenium.webdriver.common.action_chains import ActionChains


@when('user fills out the preset form for new preset "selenium_preset"')
def step_impl(context):
    print( 'cookies in filling out:', context.browser.get_cookies())
    name_field = context.browser.find_element(by=By.ID, value="new_preset_name")
    name_field.send_keys("selenium_preset")
    name_field.send_keys(keys.Keys.ENTER)
    time.sleep(1)


@then('user can see the preset "selenium_preset" that was created')
def step_impl(context):
    buttons = context.browser.find_elements(by=By.CLASS_NAME, value="accordion-button")

    preset = None
    for btn in buttons:
        print(btn)

        if btn.text == "selenium_preset":
            preset = btn
    
    assert preset is not None


@when('user deletes the preset "selenium_preset"')
def step_impl(context):
    time.sleep(5)
    button = context.browser.find_element(by=By.CLASS_NAME, value="accordion-button")
    ActionChains(context.browser).move_to_element(button).click().perform()

    time.sleep(1)
    button = context.browser.find_element(by=By.CLASS_NAME, value="btn-danger")
    ActionChains(context.browser).move_to_element(button).click().perform()


@then('user cannot see any preset on the page')
def step_impl(context):
    buttons = context.browser.find_elements(by=By.CLASS_NAME, value="accordion-button")
    assert len(buttons) == 0
