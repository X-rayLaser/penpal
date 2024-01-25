from unittest import TestCase
from tools.api_calls import TaggedApiCallBackend, ApiFunctionCall, ApiCallNotFoundError


class FindApiCallTests(TestCase):
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
