import unittest
from dataclasses import dataclass
from django.test import TestCase
from django.contrib.auth.models import User
from tools.api_calls import TaggedApiCallBackend, ApiFunctionCall, ApiCallNotFoundError
from chats import models, serializers
from django.db.models import Model
from rest_framework.serializers import BaseSerializer


class FindApiCallTests(unittest.TestCase):
    def setUp(self):
        self.backend = TaggedApiCallBackend({})

    def test_could_not_find(self):
        text = ''
        self.assertRaises(ApiCallNotFoundError, self.backend.find_api_call, text)
    
        text = '    '
        self.assertRaises(ApiCallNotFoundError, self.backend.find_api_call, text)
    
        text = 'hello world'
        self.assertRaises(ApiCallNotFoundError, self.backend.find_api_call, text)
    
    def test_can_find_empty_api_call(self):
        text = '<api></api>'
        api_call, offset = self.backend.find_api_call(text)
        self.assertEqual(api_call, ApiFunctionCall('', []))
        self.assertEqual(0, offset)

        text = ' <api></api>'
        api_call, offset = self.backend.find_api_call(text)
        self.assertEqual(api_call, ApiFunctionCall('', []))
        self.assertEqual(1, offset)

        text = 'abc<api></api>afa'
        api_call, offset = self.backend.find_api_call(text)
        self.assertEqual(api_call, ApiFunctionCall('', []))
        self.assertEqual(3, offset)

    def test_can_find_valid_api_call(self):
        text = 'abc<api>CalculatOR(AdD, 3, 9)</api>afa'
        api_call, offset = self.backend.find_api_call(text)
        self.assertEqual(api_call, ApiFunctionCall('calculator', ['add', '3', '9']))
        self.assertEqual(3, offset)

        text = 'abc<api>CalculatOR(AdD,3,   9)</api>afa'
        api_call, offset = self.backend.find_api_call(text)
        self.assertEqual(api_call, ApiFunctionCall('calculator', ['add', '3', '9']))
        self.assertEqual(3, offset)

        text = 'abc<api>CalculatOR(add)</api>afa'
        api_call, offset = self.backend.find_api_call(text)
        self.assertEqual(api_call, ApiFunctionCall('calculator', ['add']))
        self.assertEqual(3, offset)

        text = 'abc<api>CalculatOR()</api>afa'
        api_call, offset = self.backend.find_api_call(text)
        self.assertEqual(api_call, ApiFunctionCall('calculator', []))
        self.assertEqual(3, offset)

    def test_can_find_malformed_api_call(self):
        text = 'abc<apiCalculatOR(add, 3, 9)</api>def'
        api_call, offset = self.backend.find_api_call(text)
        self.assertEqual(api_call, ApiFunctionCall('calculator', ['add', '3', '9']))
        self.assertEqual(3, offset)

        text = 'abcapi>CalculatOR(add, 3, 9)</api>def'
        api_call, offset = self.backend.find_api_call(text)
        self.assertEqual(api_call, ApiFunctionCall('calculator', ['add', '3', '9']))
        self.assertEqual(3, offset)

        text = 'abc<api>CalculatOR(add, 3, 9)/api>def'
        api_call, offset = self.backend.find_api_call(text)
        self.assertEqual(api_call, ApiFunctionCall('calculator', ['add', '3', '9']))
        self.assertEqual(3, offset)

        text = 'abc<api>CalculatOR(add, 3, 9)</apidef'
        api_call, offset = self.backend.find_api_call(text)
        self.assertEqual(api_call, ApiFunctionCall('calculator', ['add', '3', '9']))
        self.assertEqual(3, offset)


class ViewSetTestGroup:
    # creation tests
    def test_anonymous_user_cannot_create_object(self):
        test = NoObjectsBeforeAndAfterRequest(self.test_context, request_data=self.request_data)
        test.post(self.list_url, expected_status=403)

    def test_logged_in_user_can_create_object(self):
        test = OneObjectCreatedAfterHttpRequest(self.test_context,
                                                request_data=self.request_data, 
                                                expected_object_fields=dict(id=1, **self.response_data))
        test.post(self.list_url, expected_status=201, credentials=self.credentials, content_type='application/json')

    def test_logged_in_user_cannot_create_object_with_malformed_data(self):
        test = NoObjectsBeforeAndAfterRequest(self.test_context, request_data=b'mybytes')
        test.post(self.list_url, expected_status=415, credentials=self.credentials, 
                  content_type='application/octet-stream')

    def test_logged_in_user_cannot_create_object_with_invalid_data(self):
        test = NoObjectsBeforeAndAfterRequest(self.test_context, request_data={"foo": "bar"})
        test.post(self.list_url, expected_status=400, credentials=self.credentials, 
                  content_type='application/json')

    # retrieval tests
    def test_anonymous_user_cannot_get_created_object(self):
        test = OneObjectExistsBeforeAndAfterRequest(self.test_context,
                                                    object_data=dict(user=self.user, **self.object_data))
        test.get(url=self.obj_url.format(1), expected_status=403)

    def test_logged_in_stranger_cannot_retrieve_other_user_object(self):
        test = OneObjectExistsBeforeAndAfterRequest(self.test_context,
                                                    object_data=dict(user=self.user, **self.object_data))
        test.get(url=self.obj_url.format(1), expected_status=404, credentials=self.stranger_credentials)

    def test_logged_in_owner_can_get_created_object(self):
        object_data = dict(user=self.user, **self.object_data)
        test = OneObjectExistsBeforeAndAfterRequest(self.test_context,
                                                    object_data=object_data,
                                                    expected_response=dict(id=1, **self.response_data))
        test.get(url=self.obj_url.format(1), expected_status=200, credentials=self.credentials)

    def test_cannot_get_non_existing_object(self):
        test = OneObjectExistsBeforeAndAfterRequest(self.test_context,
                                                    object_data=dict(user=self.user, **self.object_data))
        test.get(url=self.obj_url.format(4), expected_status=404, credentials=self.credentials)

    def test_anonymous_user_cannot_get_non_existing_object(self):
        test = OneObjectExistsBeforeAndAfterRequest(self.test_context,
                                                    object_data=dict(user=self.user, **self.object_data))
        test.get(url=self.obj_url.format(4), expected_status=403)

    def test_no_objects_initially(self):
        test = NoObjectsBeforeAndAfterRequest(self.test_context, expected_response=[])
        test.get(self.list_url, expected_status=200, credentials=self.credentials)

    def test_anonymous_user_cannot_list_objects(self):
        test = OneObjectExistsBeforeAndAfterRequest(self.test_context,
                                                    object_data=dict(user=self.user, **self.object_data))
        test.get(self.list_url, expected_status=403)

    def test_logged_user_can_only_list_their_objects(self):
        object_data = [
            dict(user=self.user, **self.object_data),
            dict(user=self.stranger, **self.alt_object_data)
        ]
        test = TwoObjectsExistBeforeAndAfterRequest(self.test_context,
                                                    object_data=object_data,
                                                    expected_response=[dict(id=1, **self.response_data)])

        test.get(self.list_url, expected_status=200, credentials=self.credentials)

    # deletion tests
    def test_cannot_delete_non_existing_object(self):
        test = OneObjectExistsBeforeAndAfterRequest(self.test_context,
                                                    object_data=dict(user=self.user, **self.object_data))
        test.delete(url=self.obj_url.format(12), credentials=self.credentials, expected_status=404)

    def test_anonymous_user_cannot_delete_object(self):
        test = OneObjectExistsBeforeAndAfterRequest(self.test_context,
                                                    object_data=dict(user=self.user, **self.object_data))
        test.delete(url=self.obj_url.format(12), expected_status=403)

    def test_owner_can_delete_their_object(self):
        test = OneObjectBeforeRequestNoObjectAfterRequest(self.test_context,
                                                          object_data=dict(user=self.user, **self.object_data))
        test.delete(url=self.obj_url.format(1), credentials=self.credentials, expected_status=204)

    def test_stranger_cannot_delete_other_user_objects(self):
        test = OneObjectExistsBeforeAndAfterRequest(self.test_context,
                                                    object_data=dict(user=self.user, **self.object_data))
        test.delete(url=self.obj_url.format(1), credentials=self.stranger_credentials,
                    expected_status=404)

    def test_correct_objects_get_deleted(self):
        object_data = [
            dict(user=self.user, **self.object_data),
            dict(user=self.stranger, **self.alt_object_data)
        ]
        expected_object_fields = dict(id=1, **self.response_data)
        test = TwoObjectsBeforeRequestAndOneObjectAfterRequest(self.test_context,
                                                               object_data=object_data,
                                                               expected_object_fields=expected_object_fields)
        test.delete(url=self.obj_url.format(2), expected_status=204, credentials=self.stranger_credentials)


class VieweSetUpdateTestGroup:
    http_method = ""

    def test_logged_in_user_cannot_patch_non_existing_objects(self):
        test = OneObjectExistsBeforeAndAfterRequest(self.test_context,
                                                    object_data=dict(user=self.user, **self.object_data))

        self.run_test(test, url=self.obj_url.format(12), expected_status=404,
                      credentials=self.credentials, content_type='application/json')

    def test_owner_can_patch_their_object(self):
        expected_resp = dict(id=1, **self.alt_response_data)
        object_data = dict(user=self.user, **self.object_data)

        test = OneObjectExistsBeforeAndAfterRequest(self.test_context,
                                                    object_data=object_data,
                                                    request_data=self.alt_data,
                                                    expected_response=expected_resp,
                                                    expected_object_fields=expected_resp)
        self.run_test(test, url=self.obj_url.format(1), expected_status=200,
                      credentials=self.credentials, content_type='application/json')

    def test_patching_updates_correct_object(self):
        data1 = dict(self.object_data)
        data1["name"] = "different_name"

        object_data = [dict(user=self.user, **data1), dict(user=self.user, **self.object_data)]
        expected_objects = [
            dict(id=1, **self.alt_response_data), dict(id=2, **self.response_data)
        ]
        test = TwoObjectsExistBeforeAndAfterRequest(self.test_context,
                                                    object_data=object_data,
                                                    request_data=self.alt_data,
                                                    expected_response=dict(id=1, **self.alt_response_data),
                                                    expected_object_fields=expected_objects)
        method = getattr(test, self.http_method)
        method(self.obj_url.format(1), credentials=self.credentials, expected_status=200,
               content_type='application/json')

    def test_anonymous_user_cannot_patch_object(self):
        test = OneObjectExistsBeforeAndAfterRequest(self.test_context,
                                                    object_data=dict(user=self.user, **self.object_data))
        
        self.run_test(test, url=self.obj_url.format(1), expected_status=403, 
                      content_type='application/json')

    def test_stranger_cannot_patch_objects_of_other_users(self):
        test = OneObjectExistsBeforeAndAfterRequest(self.test_context,
                                                    object_data=dict(user=self.user, **self.object_data))
        self.run_test(test, url=self.obj_url.format(1), credentials=self.stranger_credentials,
                      expected_status=404, content_type='application/json')

    def run_test(self, test, *args, **kwargs):
        runner = getattr(test, self.http_method)
        runner(*args, **kwargs)


class ViewSetPutTestGroup(VieweSetUpdateTestGroup):
    http_method = "put"


class ViewSetPatchTestGroup(VieweSetUpdateTestGroup):
    http_method = "patch"


class AbstractViewSetTestCase(TestCase):
    @property
    def response_data(self):
        return dict(user=self.user.username, **self.request_data)

    @property
    def alt_response_data(self):
        return dict(user=self.user.username, **self.alt_data)

    @property
    def test_context(self):
        return TestContext(test_case=self, model_class=self.model_class,
                           serializer_class=self.serializer_class)


class PresetsTestCase(AbstractViewSetTestCase):
    list_url = "/chats/presets/"
    obj_url = "/chats/presets/{}/"
    model_class = models.Preset
    serializer_class = serializers.PresetSerializer

    def setUp(self):
        self.object_data = {'name': 'default',
                             'temperature': 0.1,
                             'top_k': 40,
                             'top_p': 0.95,
                             'min_p': 0.05,
                             'repeat_penalty': 1.1,
                             'n_predict': 512}
        self.request_data = dict(self.object_data)

        alt_data = dict(self.request_data)
        alt_data['name'] = "other object"
        alt_data['temperature'] = 0.9
        self.alt_data = alt_data

        self.alt_object_data = dict(self.alt_data)

        self.credentials = dict(username="user", password="password")
        self.user = User.objects.create_user(**self.credentials)

        self.stranger_credentials = dict(username="stranger", password="stranger")
        self.stranger = User.objects.create_user(**self.stranger_credentials)


class SystemMessageTestCase(AbstractViewSetTestCase):
    list_url = "/chats/system_messages/"
    obj_url = "/chats/system_messages/{}/"
    model_class = models.SystemMessage
    serializer_class = serializers.SystemMessageSerializer

    def setUp(self) -> None:
        self.object_data = {
            "name": "assistant",
            "text": "You are a helpful assistant"
        }

        self.request_data = self.object_data

        self.alt_data = {
            "name": "agent",
            "text": "You are an agent"
        }

        self.alt_object_data = dict(self.alt_data)

        self.credentials = dict(username="user", password="password")
        self.user = User.objects.create_user(**self.credentials)

        self.stranger_credentials = dict(username="stranger", password="stranger")
        self.stranger = User.objects.create_user(**self.stranger_credentials)


class ConfigurationTestCase(AbstractViewSetTestCase):
    list_url = "/chats/configurations/"
    obj_url = "/chats/configurations/{}/"
    model_class = models.Configuration
    serializer_class = serializers.ConfigurationSerializer

    def setUp(self) -> None:
        self.credentials = dict(username="user", password="password")
        self.user = User.objects.create_user(**self.credentials)

        self.stranger_credentials = dict(username="stranger", password="stranger")
        self.stranger = User.objects.create_user(**self.stranger_credentials)

        preset = models.Preset.objects.create(user=self.user, **default_preset_data())
        system_msg = models.SystemMessage.objects.create(user=self.user, **default_system_msg_data())

        self.object_data = {
            'name': 'myconf',
            'model_repo': 'myrepo',
            'file_name': 'myfile',
            'launch_params': {
                'p1': 10,
                'p2': 20
            },
            'system_message': system_msg,
            'preset': preset,
            'tools': [],
        }

        self.request_data = {
            'name': 'myconf',
            'model_repo': 'myrepo',
            'file_name': 'myfile',
            'launch_params': {
                'p1': 10,
                'p2': 20
            },
            'system_message': system_msg.id,
            'preset': preset.id,
            'tools': [],
        }

        self.alt_data = dict(self.request_data)
        self.alt_data.update({
            "name": "other conf",
            "model_repo": "other repo"
        })

        self.alt_object_data = dict(self.object_data)
        self.alt_object_data.update({
            "name": "other conf",
            "model_repo": "other repo"
        })

    @property
    def response_data(self):
        sys_msg = dict(id=1, user=self.user.username, **default_system_msg_data())
        preset = dict(id=1, user=self.user.username, **default_preset_data())
        return dict(user=self.user.username,
                    system_message_ro=sys_msg,
                    preset_ro=preset,
                    template_spec=None,
                    voice_id=None,
                    **self.request_data)

    @property
    def alt_response_data(self):
        sys_msg = dict(id=1, user=self.user.username, **default_system_msg_data())
        preset = dict(id=1, user=self.user.username, **default_preset_data())
        return dict(user=self.user.username,
                    system_message_ro=sys_msg,
                    preset_ro=preset,
                    template_spec=None,
                    voice_id=None,
                    **self.alt_data)


class PresetRemainingMethodsTestCase(PresetsTestCase, ViewSetTestGroup):
    pass


class SystemMessageRemainingMethodsTestCase(SystemMessageTestCase, ViewSetTestGroup):
    pass


class ConfigurationRemainingMethodsTestCase(ConfigurationTestCase, ViewSetTestGroup):
    pass


class PresetPutTestCase(PresetsTestCase, ViewSetPutTestGroup):
    pass


class PresetPatchTestCase(PresetsTestCase, ViewSetPatchTestGroup):
    pass


class SystemMessagePutTestCase(SystemMessageTestCase, ViewSetPutTestGroup):
    pass


class SystemMessagePatchTestCase(SystemMessageTestCase, ViewSetPatchTestGroup):
    pass


class ConfigurationPutTestCase(ConfigurationTestCase, ViewSetPutTestGroup):
    pass


class ConfigurationPatchTestCase(ConfigurationTestCase, ViewSetPatchTestGroup):
    pass


def default_preset_data():
    return {
        'name': 'default',
        'temperature': 0.1,
        'top_k': 40,
        'top_p': 0.95,
        'min_p': 0.05,
        'repeat_penalty': 1.1,
        'n_predict': 512
    }


def default_system_msg_data():
    return {
        "name": "assistant",
        "text": "You are a helpful assistant"
    }


@dataclass
class TestContext:
    test_case: TestCase
    model_class: Model
    serializer_class: BaseSerializer


@dataclass
class BaseTestTemplate:
    context: TestContext
    object_data: dict = None
    request_data: dict = None
    expected_object_fields: dict = None
    expected_response: dict = None

    def get(self, url, expected_status=200, credentials=None, **method_kwargs):
        self._run_test("get", url, expected_status, credentials, **method_kwargs)

    def post(self, url, expected_status=200, credentials=None, **method_kwargs):
        self._run_test("post", url, expected_status, credentials, **method_kwargs)

    def put(self, url, expected_status=200, credentials=None, **method_kwargs):
        self._run_test("put", url, expected_status, credentials, **method_kwargs)

    def patch(self, url, expected_status=200, credentials=None, **method_kwargs):
        self._run_test("patch", url, expected_status, credentials, **method_kwargs)

    def delete(self, url, expected_status=200, credentials=None, **method_kwargs):
        self._run_test("delete", url, expected_status, credentials, **method_kwargs)

    def _run_test(self, method, url, expected_status=200, credentials=None, **method_kwargs):
        if self.object_data:
            self.prepare_env()

        test_case = self.context.test_case
        if credentials:
            test_case.client.login(**credentials)

        method = getattr(test_case.client, method)
        request_data = self.request_data or {}
        if isinstance(request_data, dict) and request_data.get("user"):
            request_data = dict(request_data)
            del request_data["user"]
        resp = method(url, request_data, **method_kwargs)
        test_case.assertEqual(expected_status, resp.status_code, msg=f"{resp.content}")
        expected_response = self.get_expected_response()

        if resp.status_code in [200, 201]:
            test_case.assertEqual(expected_response, resp.json())

        self.make_assertions()

    def get_expected_response(self):
        if self.expected_response is None:
            return self.expected_object_fields
        return self.expected_response


class CreateSingleObjectMixin:
    def prepare_env(self):
        model_class = self.context.model_class
        serializer_class = self.context.serializer_class
        self.first_instance = model_class.objects.create(**self.object_data)
        self.first_instance_fields = serializer_class(instance=self.first_instance).data


class CreateTwoObjectsMixin:
    def prepare_env(self):
        model_class = self.context.model_class
        serializer_class = self.context.serializer_class
        self.first_instance = model_class.objects.create(**self.object_data[0])
        self.first_instance_fields = serializer_class(instance=self.first_instance).data

        self.second_instance = model_class.objects.create(**self.object_data[1])
        self.second_instance_fields = serializer_class(instance=self.second_instance).data


class AssertNoObjectsMixin:
    def make_assertions(self):
        self.context.test_case.assertEqual(0, self.context.model_class.objects.count())


class AssertOneObjectExistsWithFieldsMixin:
    def make_assertions(self):
        model_class = self.context.model_class
        serializer_class = self.context.serializer_class

        expected_fields = self.expected_object_fields or self.first_instance_fields
        self.context.test_case.assertEqual(1, model_class.objects.count())
        
        obj = model_class.objects.first()
        ser = serializer_class(instance=obj)
        self.context.test_case.assertEqual(expected_fields, ser.data)


class AssertTwoObjectsExistWithCorrectFieldsMixin:
    def make_assertions(self):
        if self.expected_object_fields:
            expected_fields1, expected_fields2 = self.expected_object_fields
        else:
            expected_fields1 = self.first_instance_fields
            expected_fields2 = self.second_instance_fields

        test_case = self.context.test_case
        test_case.assertEqual(2, self.context.model_class.objects.count())
        
        obj1, obj2 = self.context.model_class.objects.all()
        
        test_case.assertEqual(expected_fields1, self.context.serializer_class(instance=obj1).data)
        test_case.assertEqual(expected_fields2, self.context.serializer_class(instance=obj2).data)


class NoObjectsBeforeAndAfterRequest(BaseTestTemplate, AssertNoObjectsMixin):
    pass


class OneObjectExistsBeforeAndAfterRequest(BaseTestTemplate,
                                           CreateSingleObjectMixin,
                                           AssertOneObjectExistsWithFieldsMixin):
    pass


class TwoObjectsExistBeforeAndAfterRequest(BaseTestTemplate,
                                           CreateTwoObjectsMixin,
                                           AssertTwoObjectsExistWithCorrectFieldsMixin):
    pass


class TwoObjectsBeforeRequestAndOneObjectAfterRequest(BaseTestTemplate,
                                                      CreateTwoObjectsMixin,
                                                      AssertOneObjectExistsWithFieldsMixin):
    pass


class OneObjectCreatedAfterHttpRequest(BaseTestTemplate,
                                       AssertOneObjectExistsWithFieldsMixin):
    pass


class OneObjectBeforeRequestNoObjectAfterRequest(BaseTestTemplate,
                                                 CreateSingleObjectMixin,
                                                 AssertNoObjectsMixin):
    pass
