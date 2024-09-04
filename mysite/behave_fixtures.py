from behave import fixture
import django
from django.test import override_settings
from django.test.runner import DiscoverRunner
from django.test.testcases import LiveServerThread, QuietWSGIRequestHandler
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


initial_port = 8000


class ServerThreadWithReusablePort(LiveServerThread):
    def _create_server(self, connections_override=None):
        global initial_port
        self.port = initial_port

        initial_port += 1
        return self.server_class(
            (self.host, self.port),
            QuietWSGIRequestHandler,
            allow_reuse_address=True,
            connections_override=connections_override,
        )


@override_settings(ALLOWED_HOSTS=['*'])
class MyTestCase(StaticLiveServerTestCase):
    host = '0.0.0.0'
    server_thread_class = ServerThreadWithReusablePort
    port = 8000


@fixture
def django_test_case(context):
    context.test_case = MyTestCase
    context.test_case.setUpClass()
    yield
    context.test_case.tearDownClass()
    del context.test_case