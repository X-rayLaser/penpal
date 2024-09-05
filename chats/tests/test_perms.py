from django.test import TestCase
from django.contrib.auth.models import User
from chats import models
from chats.tests.common import (
    default_system_msg_data, default_preset_data, default_configuration_data
)


class ConfigurationTestCase(TestCase):
    list_url = "/chats/configurations/"
    obj_url = "/chats/configurations/{}/"

    def setUp(self) -> None:
        self.credentials = dict(username="user", password="password")
        self.user = User.objects.create_user(**self.credentials)

        self.stranger_credentials = dict(username="stranger", password="stranger")
        self.stranger = User.objects.create_user(**self.stranger_credentials)


class ConfigurationCreationPermissionsTests(ConfigurationTestCase):
    def test_user_cannot_add_system_message_of_different_user(self):
        preset = prepare_preset(self.user)
        msg = prepare_msg(self.stranger)
        conf_data = prepare_conf_data(preset, msg)

        self.client.login(**self.credentials)
        resp = self.client.post(self.list_url, data=conf_data, content_type='application/json')

        self.assertEqual(403, resp.status_code)

    def test_user_cannot_add_preset_of_different_user(self):
        preset = prepare_preset(self.stranger)
        msg = prepare_msg(self.user)
        conf_data = prepare_conf_data(preset, msg)

        self.client.login(**self.credentials)
        resp = self.client.post(self.list_url, data=conf_data, content_type='application/json')

        self.assertEqual(403, resp.status_code)

    def test_user_attempts_to_add_both_preset_and_msg_they_do_not_own(self):
        preset = prepare_preset(self.stranger)
        msg = prepare_msg(self.stranger)
        conf_data = prepare_conf_data(preset, msg)

        self.client.login(**self.credentials)
        resp = self.client.post(self.list_url, data=conf_data, content_type='application/json')

        self.assertEqual(403, resp.status_code)


class ConfigurationWithOptionalFieldsTests(ConfigurationTestCase):
    def test_preset_is_optional_for_config_creation(self):
        msg = prepare_msg(self.user)
        conf_data = prepare_conf_data(preset=None, msg=msg)
        del conf_data["preset"]

        self.client.login(**self.credentials)
        resp = self.client.post(self.list_url, data=conf_data, content_type='application/json')

        self.assertEqual(201, resp.status_code)

    def test_system_msg_is_optional_for_config_creation(self):
        preset = prepare_preset(self.user)
        conf_data = prepare_conf_data(preset, msg=None)
        del conf_data["system_message"]

        self.client.login(**self.credentials)
        resp = self.client.post(self.list_url, data=conf_data, content_type='application/json')

        self.assertEqual(201, resp.status_code)

    def test_request_without_sys_msg_nor_preset(self):
        conf_data = prepare_conf_data(preset=None, msg=None)
        del conf_data["preset"]
        del conf_data["system_message"]

        self.client.login(**self.credentials)
        resp = self.client.post(self.list_url, data=conf_data, content_type='application/json')

        self.assertEqual(201, resp.status_code)


class ConfigurationUpdatePermissionTests(ConfigurationTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.conf_data = prepare_conf_data(preset=None, msg=None)
        owner = self.user
        conf = models.Configuration.objects.create(user=owner, **self.conf_data)
        self.request_data = dict(self.conf_data)

    def test_owner_cannot_update_config_with_system_msg_they_do_not_own(self):
        msg = prepare_msg(msg_owner=self.stranger)
        self.request_data.update(system_message=msg.id)
        self.assertUpdateForbidden(put_data=self.request_data, patch_data=dict(system_message=msg.id))

    def test_owner_cannot_update_config_with_preset_they_do_not_own(self):
        preset = prepare_preset(preset_owner=self.stranger)
        self.request_data.update(preset=preset.id)
        self.assertUpdateForbidden(put_data=self.request_data, patch_data=dict(preset=preset.id))

    def test_update_with_both_fields_being_offenders(self):
        msg = prepare_msg(msg_owner=self.stranger)
        preset = prepare_preset(preset_owner=self.stranger)

        patch_data = dict(preset=preset.id, system_message=msg.id)
        put_data = self.request_data
        put_data.update(**patch_data)

        self.assertUpdateForbidden(put_data=put_data, patch_data=patch_data)

    def assertUpdateForbidden(self, put_data, patch_data):
        obj_url = self.obj_url.format(1)
        self.client.login(**self.credentials)
        resp = self.client.put(obj_url, data=put_data, content_type='application/json')
        self.assertEqual(403, resp.status_code, resp.json())

        resp = self.client.patch(obj_url, data=patch_data, content_type='application/json')
        self.assertEqual(403, resp.status_code, resp.json())


def prepare_preset(preset_owner):
    preset_data = default_preset_data()
    return models.Preset.objects.create(user=preset_owner, **preset_data)

def prepare_msg(msg_owner):
    msg_data = default_system_msg_data()
    return models.SystemMessage.objects.create(user=msg_owner, **msg_data)

def prepare_conf_data(preset, msg):
    return {
        'name': 'myconf',
        'model_repo': 'myrepo',
        'file_name': 'myfile',
        'launch_params': {
            'p1': 10,
            'p2': 20
        },
        'system_message': msg and msg.id,
        'preset': preset and preset.id,
        'tools': [],
    }