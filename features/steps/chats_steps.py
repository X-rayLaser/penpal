import time
from behave import given, when, then, step
from selenium.webdriver.common.by import By
from selenium.webdriver.common import keys
from selenium.webdriver.common.action_chains import ActionChains


@when('user creates a new chat')
def step_impl(context):
    button = context.browser.find_element(by=By.XPATH, value='//button[contains(text(), "Create")]')
    button.click()
    time.sleep(2)


@then('user can see a new chat appearing')
def step_impl(context):
    p = context.browser.find_element(by=By.XPATH, value='//div/p[contains(text(), "**No data yet**")]')
    assert p.text == "**No data yet**"


@when('user deletes the chat')
def step_impl(context):
    time.sleep(5)
    button = context.browser.find_element(by=By.XPATH, value='//button[contains(text(), "Delete")]')
    ActionChains(context.browser).move_to_element(button).click().perform()


@then('user cannot see any chats on the page')
def step_impl(context):
    time.sleep(1)
    items = context.browser.find_elements(by=By.XPATH, value='//div/p[contains(text(), "**No data yet**")]')
    assert len(items) == 0


@when('user sends a text message "{message}" to AI')
def step_impl(context, message):
    text_area = context.browser.find_element(by=By.ID, value="exampleForm.ControlTextarea1")
    text_area.send_keys(message)

    button = context.browser.find_element(by=By.XPATH, value='//button[@type="submit"]')
    button.click()
    context.message = message


@when('user waits for "{secs}" seconds')
def step_impl(context, secs):
    secs = int(secs)
    time.sleep(secs)


@then('user can see their text message')
def step_impl(context):
    p = context.browser.find_element(by=By.XPATH, value=f'//div//p[contains(text(), "{context.message}")]')
    assert p.text == context.message


@then('user can see a response from an AI')
def step_impl(context):
    header = context.browser.find_element(by=By.XPATH, value='//div[@class="card-header"][contains(text(), "AI")]')
    assert header.text == 'AI'

    p = context.browser.find_element(by=By.XPATH, value='//div[@class="card-header"][contains(text(), "AI")]/..//p')
    assert p.text != ''


@when('user clicks "Regenerate" button')
def step_impl(context):
    button = context.browser.find_element(by=By.XPATH, value='//button[contains(text(), "Regenerate")]')
    button.click()


@then('user can see two responses from AI')
def step_impl(context):
    context.response2 = ""
    xpath = '//div[@class="card-header"][contains(text(), "AI")]/..//ul[contains(@class, "pagination")]/li'
    list_items = context.browser.find_elements(by=By.XPATH, value=xpath)
    assert len(list_items) == 2
