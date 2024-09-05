from django.test import TestCase
from chats import models


class ConfigurationPermissionsTests(TestCase):
    def test_owner_cannot_add_system_message_of_different_user(self):
        assert False