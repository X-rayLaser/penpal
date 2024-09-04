import os
import time
import subprocess
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from behave import use_fixture
from mysite.behave_fixtures import django_test_runner, django_test_case
service = Service(executable_path="/app/chromedriver-linux64/chromedriver")
os.environ["DJANGO_SETTINGS_MODULE"] = "mysite.test_settings"

options = Options()
options.binary_location = "/app/chrome-linux64/chrome"
options.add_argument('--headless=new')
options.add_argument('--no-sandbox')


def before_scenario(context, scenario):
    use_fixture(django_test_runner, context)
    use_fixture(django_test_case, context)

    driver = webdriver.Chrome(options=options, service=service)
    driver.implicitly_wait(2)
    context.browser = driver


def after_scenario(context, scenario):
    context.browser.save_screenshot(f'/data/{scenario.name}.png')
    time.sleep(5)
    context.browser.close()


def after_step(context, step):
    for log in context.browser.get_log('browser'):
        print(log)

    name = clean_name(step.name)
    context.browser.save_screenshot(f'/data/{name}.png')


def clean_name(name):
    name = name.replace(' ', '-').replace('-', '_')
    return ''.join([ch for ch in name if ch == '_' or ch.isalpha()])
