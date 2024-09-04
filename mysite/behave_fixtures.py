from behave import fixture
import django
from django.test.runner import DiscoverRunner
from django.test.testcases import LiveServerTestCase
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

@fixture
def django_test_runner(context):
    django.setup()
    context.test_runner = DiscoverRunner()
    context.test_runner.setup_test_environment()
    context.old_db_config = context.test_runner.setup_databases()
    yield
    context.test_runner.teardown_databases(context.old_db_config)
    context.test_runner.teardown_test_environment()


class MyTestCase(StaticLiveServerTestCase):
    port = 9000


@fixture
def django_test_case(context):
    context.test_case = MyTestCase
    context.test_case.setUpClass()
    context.live_server_url = context.test_case.live_server_url
    yield
    context.test_case.tearDownClass()
    del context.test_case