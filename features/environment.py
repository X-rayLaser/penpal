from selenium import webdriver
import subprocess
from selenium.webdriver.chrome.options import Options
options = Options()
options.binary_location = "chrome-linux64/chrome"


def before_all(context):
    pass


def before_scenario(context, scenario):
    start_app()
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(2)
    context.browser = driver


def after_scenario(context, scenario):
    import time
    time.sleep(5)
    context.browser.close()
    stop_app()


def start_app():
    run_cmd("export ENV=TEST && docker-compose up -d")
    import time
    time.sleep(28)


def stop_app():
    run_cmd("docker-compose stop")


def run_cmd(cmd):
    res = subprocess.run(cmd, shell=True, check=True, capture_output=True)
    if res.stdout:
        print(res.stdout)
    if res.stderr:
        print(res.stderr)
