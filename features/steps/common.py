import time
from django.contrib.auth.models import User
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.auth import login, get_user
from django.http.request import HttpRequest
from behave import given, when, then, step
from django.test import Client
from django.conf import settings


@given('user is authenticated')
def step_impl(context):
    credentials = dict(username='user', password='password')
    user = User.objects.create_user(**credentials)
    client = Client()
    client.login(**credentials)

    cookie = client.cookies['sessionid']

    req = HttpRequest()
    req.session = SessionStore(cookie.value)
    user = get_user(req)
    assert user.username == 'user'
    context.browser.get(context.live_server_url)
    
    time.sleep(10)
    print('URL:', context.live_server_url)
    context.cookie = {
        'name': 'sessionid',
        'value': cookie.value,
        'secure': False,
        'path': '/',
    }

    context.browser.add_cookie(context.cookie)
    context.browser.refresh()


@when('user visits the "{path}" page')
def step_impl(context, path):
    url = f'{context.live_server_url}{path}'
    context.browser.get(url)

    for log in context.browser.get_log('browser'): print(log)
    context.browser.save_screenshot(f'/data/my-{path}.png')


@when('user reloads the "{path}" page')
def step_impl(context, path):
    context.execute_steps(f'when user visits the "{path}" page')
