import unittest
import inspect
import base64
from io import BytesIO
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


class EndPointCreateTests:
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


class EndPointDetailTests:
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


class EndPointListTests:
    def test_no_objects_initially(self):
        expected_response = self.response_with_no_objects()
        test = NoObjectsBeforeAndAfterRequest(self.test_context, expected_response=expected_response)
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
        expected_response = self.response_with_one_object()
        test = TwoObjectsExistBeforeAndAfterRequest(self.test_context,
                                                    object_data=object_data,
                                                    expected_response=expected_response)

        test.get(self.list_url, expected_status=200, credentials=self.credentials)

    def response_with_no_objects(self):
        return []

    def response_with_one_object(self):
        return [dict(id=1, **self.response_data)]


class EndPointPaginatedListTests(EndPointListTests):
    def response_with_no_objects(self):
        return {'count': 0, 'next': None, 'previous': None, 'results': []}

    def response_with_one_object(self):
        fields = super().response_with_one_object()
        return {'count': 1, 'next': None, 'previous': None, 'results': fields}


class EndPointRetrieveTests(EndPointDetailTests, EndPointListTests):
    pass


class EndpointDeleteTests:
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


class EndPointUpdateTests:
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
        if hasattr(self, "tertiary_object_data"):
            data1 = dict(getattr(self, "tertiary_object_data"))
        else:
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


class EndPointPutTests(EndPointUpdateTests):
    http_method = "put"


class EndPointPatchTests(EndPointUpdateTests):
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
        self.object_data = default_preset_data()
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
        self.object_data = default_system_msg_data()

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

        self.request_data = dict(self.object_data)
        self.request_data.update({
            'system_message': system_msg.id,
            'preset': preset.id,
        })

        changes = {
            "name": "other conf",
            "model_repo": "other repo"
        }
        self.alt_data = dict(self.request_data)
        self.alt_data.update(changes)

        self.alt_object_data = dict(self.object_data)
        self.alt_object_data.update(changes)
        

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


class BaseChatTestCase(AbstractViewSetTestCase):
    maxDiff=None
    list_url = "/chats/chats/"
    obj_url = "/chats/chats/{}/"
    model_class = models.Chat
    serializer_class = serializers.ChatSerializer

    def setUp(self) -> None:
        self.credentials = dict(username="user", password="password")
        self.user = User.objects.create_user(**self.credentials)

        self.stranger_credentials = dict(username="stranger", password="stranger")
        self.stranger = User.objects.create_user(**self.stranger_credentials)

        configuration_data = default_configuration_data(self.user)
        configuration = models.Configuration.objects.create(**configuration_data)
        self.configuration = configuration

        self.object_data = {
            'configuration': configuration,
        }

        self.request_data = {
            'configuration': configuration.id,
        }

        changes = {
            'system_message': 'New system message'
        }
        self.alt_data = dict(self.request_data)
        self.alt_data.update(changes)

        self.alt_object_data = dict(self.object_data)
        self.alt_object_data.update(changes)

        self.tertiary_object_data = dict(self.object_data)
        self.tertiary_object_data["system_message"] = "Even newer system message"

    @property
    def response_data(self):
        sys_msg = dict(id=1, user=self.user.username, **default_system_msg_data())
        preset = dict(id=1, user=self.user.username, **default_preset_data())
        conf_ro = dict(id=1,
                       name='myconf',
                       model_repo='myrepo',
                       file_name='myfile',
                       launch_params={'p1': 10, 'p2': 20},
                       tools=[],
                       user=self.user.username,
                       system_message=1,
                       system_message_ro=sys_msg,
                       preset=1,
                       preset_ro=preset,
                       template_spec=None,
                       voice_id=None)

        return {
            'user': self.user.username,
            'configuration': self.configuration.id,
            'configuration_ro': conf_ro,
            'system_message': None,
            'prompt_text': "**No data yet**"
        }

    @property
    def alt_response_data(self):
        data = dict(self.response_data)
        data['system_message'] = 'New system message'
        return data


class ChatCreateRetrieveDeleteTestCase(BaseChatTestCase,
                                       EndPointCreateTests,
                                       EndPointPaginatedListTests,
                                       EndPointDetailTests,
                                       EndpointDeleteTests):
    exclude_fields = ["date_time"]


class ChatPatchTestCase(BaseChatTestCase, EndPointPatchTests):
    exclude_fields = ["date_time", "prompt_text"]


class MessageCreateTestCase(AbstractViewSetTestCase, EndPointCreateTests):
    maxDiff=None
    list_url = "/chats/messages/"
    model_class = models.Message
    serializer_class = serializers.MessageSerializer
    exclude_fields = ["date_time"]

    def setUp(self) -> None:
        self.credentials = dict(username="user", password="password")
        self.user = User.objects.create_user(**self.credentials)

        self.stranger_credentials = dict(username="stranger", password="stranger")
        self.stranger = User.objects.create_user(**self.stranger_credentials)

        chat = models.Chat.objects.create(user=self.user)
        self.chat = chat

        self.object_data = {
            'chat': chat,
            'text':  "Hello, world"
        }

        self.request_data = dict(self.object_data)
        self.request_data.update({
            'chat': chat.id
        })

        self.alt_data = dict(self.request_data)

        self.sample_img = (b"GIF89a\x01\x00\x01\x00\x00\x00\x00!\xf9\x04\x01\x00\x00\x00"
                           b"\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x01\x00\x00")

    @property
    def response_data(self):
        return dict(
                    text="Hello, world",
                    clean_text="Hello, world",
                    html="<p>Hello, world</p>",
                    generation_details=None,
                    parent=None,
                    replies=[],
                    chat=self.chat.id,
                    audio=None,
                    image=None,
                    image_b64=None,
                    attached_files=[])

    def test_image_upload(self):
        self.client.login(**self.credentials)
        data = dict(self.request_data)

        img = BytesIO(self.sample_img)
        img.name = "image.gif"

        data.update(image=img)
        resp = self.client.post(self.list_url, data=data)

        self.assertEqual(201, resp.status_code, resp.json())
        self.assertIsNotNone(resp.json()["image"], resp.json())
        self.assertIsNotNone(resp.json()["image_b64"])

    def test_image_b64_upload(self):
        b64 = base64.b64encode(self.sample_img)
        image_data_uri = f"data:image/gif;base64,{b64.decode('ascii')}"

        self.client.login(**self.credentials)
        data = dict(self.request_data)
        data.update(image_data_uri=image_data_uri)
        resp = self.client.post(self.list_url, data=data)

        self.assertEqual(201, resp.status_code, resp.json())
        self.assertIsNotNone(resp.json()["image"], resp.json())
        self.assertIsNotNone(resp.json()["image_b64"])

    def test_audio_upload(self):
        audio_file = open("test_data/sample.wav", "rb")

        data = dict(self.request_data)
        data.update(audio=audio_file)

        self.client.login(**self.credentials)
        resp = self.client.post(self.list_url, data=data)

        self.assertEqual(201, resp.status_code)
        self.assertIsNotNone(models.Message.objects.first().audio)
        self.assertIsNone(resp.json()["audio"], resp.json())
        audio_file.close()


class VoiceListTests(TestCase):
    # todo: more tests for edge cases (network errors, etc.)
    def test_list_voices(self):
        resp = self.client.get('/chats/list-voices/')
        self.assertEqual(200, resp.status_code)
        expected = [{"voice_id": "Voice 1", "url": ""},
                    {"voice_id": "Voice 2", "url": ""},
                    {"voice_id": "Voice 3", "url": ""}]
        self.assertEqual(expected, resp.json())


class TranscribeSpeechTests(TestCase):
    # todo: more tests for edge cases (network errors, etc.)
    def test_transcribe(self):
        resp = self.client.post('/chats/transcribe_speech/')
        expected = dict(text="This is a speech transcribed by DummySpeechToTextBackend backend")
        self.assertEqual(200, resp.status_code)
        self.assertEqual(expected, resp.json())


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


def default_configuration_data(user):
    preset = models.Preset.objects.create(user=user, **default_preset_data())
    system_msg = models.SystemMessage.objects.create(user=user, **default_system_msg_data())

    return {
        'user': user,
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

        exclude = getattr(test_case, "exclude_fields", [])
        if resp.status_code in [200, 201]:
            actual = exclude_fields(resp.json(), exclude)
            expected_response = exclude_fields(expected_response, exclude)
            test_case.assertEqual(expected_response, actual)

        self.make_assertions()

    def get_expected_response(self):
        if self.expected_response is None:
            return self.expected_object_fields
        return self.expected_response


def exclude_fields(obj, exclude_list):
    if isinstance(obj, list):
        return [exclude_fields(item, exclude_list) for item in obj]
        
    if not isinstance(obj, dict):
        return obj

    return {k: exclude_fields(v, exclude_list)
            for k, v in obj.items() if k not in exclude_list}


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
        exclude_list = getattr(self.context.test_case, "exclude_fields", [])

        expected_fields = self.expected_object_fields or self.first_instance_fields
        expected_fields = exclude_fields(expected_fields, exclude_list)
        self.context.test_case.assertEqual(1, model_class.objects.count())
        
        obj = model_class.objects.first()
        ser = serializer_class(instance=obj)
        actual = exclude_fields(ser.data, exclude_list)

        self.context.test_case.assertEqual(expected_fields, actual)


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

        exclude_list = getattr(self.context.test_case, "exclude_fields", [])

        expected_fields1 = exclude_fields(expected_fields1, exclude_list)
        expected_fields2 = exclude_fields(expected_fields2, exclude_list)
        
        actual_fields1 = self.context.serializer_class(instance=obj1).data
        actual_fields1 = exclude_fields(actual_fields1, exclude_list)

        actual_fields2 = self.context.serializer_class(instance=obj2).data
        actual_fields2 = exclude_fields(actual_fields2, exclude_list)

        test_case.assertEqual(expected_fields1, actual_fields1)
        test_case.assertEqual(expected_fields2, actual_fields2)


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


def collect_crud_suite(BaseTestCaseClass, base_name=''):
    base_name = base_name or BaseTestCaseClass.__name__

    suite = unittest.TestSuite()

    bases = (BaseTestCaseClass, EndPointCreateTests, EndPointRetrieveTests, EndpointDeleteTests)
    crd_case = type(base_name + 'CreateRetrieveDeleteTestCase', bases, {})

    put_case = type(base_name + 'PutTestCase', (BaseTestCaseClass, EndPointPutTests), {})
    patch_case = type(base_name + 'PatchTestCase', (BaseTestCaseClass, EndPointPatchTests), {})

    test_cases = [crd_case, put_case, patch_case]
    for case in test_cases:
        suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(case))

    return suite


def load_tests(loader, standard_tests, pattern):
    """Allows to specify which tests to run manually"""
    suite = unittest.TestSuite()
    base_test_cases = [PresetsTestCase, SystemMessageTestCase, ConfigurationTestCase]
    
    suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(FindApiCallTests))

    suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(ChatCreateRetrieveDeleteTestCase))
    suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(ChatPatchTestCase))
    suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(MessageCreateTestCase))
    suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(VoiceListTests))

    for test_case in base_test_cases:
        suite.addTest(collect_crud_suite(test_case))
    
    return suite
