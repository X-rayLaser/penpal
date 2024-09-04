import time
from django.contrib.auth.models import User
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.auth import login, get_user
from django.http.request import HttpRequest
from behave import given, when, then, step
from django.test import Client
from django.conf import settings


def get_base_url(test_case):
    url = test_case.live_server_url
    port = url.split(':')[-1]
    docker_bridge = '172.17.0.1'
    return f'http://{docker_bridge}:{port}'


@given('user is authenticated')
def step_impl(context):
    credentials = dict(username='user', password='password')
    user = User.objects.create_user(**credentials)
    client = Client()
    client.login(**credentials)

    cookie = client.cookies['sessionid']

    url = get_base_url(context.test_case)
    context.browser.get(url)
    
    time.sleep(10)
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
    base_url = get_base_url(context.test_case)
    url = f'{base_url}{path}'
    context.browser.get(url)


@when('user reloads the "{path}" page')
def step_impl(context, path):
    context.execute_steps(f'when user visits the "{path}" page')
