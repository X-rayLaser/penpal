import unittest
from pygentify.tool_calling import find_code_section, parse_code_section, detect_language
from pygentify.completion import finilize_response


class FindCodeSectionTests(unittest.TestCase):
    def test_without_code(self):
        s = "no code"
        res = find_code_section(s)
        self.assertIsNone(res)

        s = "`no code`"
        res = find_code_section(s)
        self.assertIsNone(res)

        s = "`no code```"
        res = find_code_section(s)
        self.assertIsNone(res)
        s = "``````"
        res = find_code_section(s)
        self.assertIsNone(res)
        
        s = "``` ```"
        res = find_code_section(s)
        self.assertIsNone(res)

        s = "```\n \n```"
        res = find_code_section(s)
        self.assertIsNone(res)

    def test_with_incomplete_code_section(self):
        s = "  ``` incomplete code\n"
        prefix, code = find_code_section(s)
        self.assertEqual("  ", prefix)
        self.assertEqual(" incomplete code\n", code)

        s = "prefix``` incomplete code\n"
        prefix, code = find_code_section(s)
        self.assertEqual("prefix", prefix)
        self.assertEqual(" incomplete code\n", code)

    def test_with_complete_section(self):
        s = "prefix\n``` complete code\n```"
        prefix, code = find_code_section(s)
        self.assertEqual("prefix\n", prefix)
        self.assertEqual(" complete code\n", code)

        s = "prefix\n```\npython complete code\n```"
        prefix, code = find_code_section(s)
        self.assertEqual("prefix\n", prefix)
        self.assertEqual("\npython complete code\n", code)

    def test_with_continuation(self):
        s = "prefix\n``` complete code\n```\nContinuation"
        prefix, code = find_code_section(s)
        self.assertEqual("prefix\n", prefix)
        self.assertEqual(" complete code\n", code)

    def test_with_multiple_code_sections(self):
        s = "prefix\n``` complete code\n```\nContinuation``` hello, world```"
        prefix, code = find_code_section(s)
        self.assertEqual("prefix\n", prefix)
        self.assertEqual(" complete code\n", code)


class ParseCodeSectionTests(unittest.TestCase):
    def test_with_language_specified(self):
        s = "python\nprint(23)\n"
        code, language = parse_code_section(s, languages=["python"])
        self.assertEqual("print(23)", code)
        self.assertEqual("python", language)

    def test_with_language_with_preceding_new_lines(self):
        s = "\npython\nprint(23)\n"
        code, language = parse_code_section(s, languages=["python"])
        self.assertEqual("print(23)", code)
        self.assertEqual("python", language)

    def test_with_language_with_multiple_preceding_separators(self):
        s = " \n  \n python\nprint(23)\n"
        code, language = parse_code_section(s, languages=["python"])
        self.assertEqual("print(23)", code)
        self.assertEqual("python", language)

    def test_with_language_followed_by_multiple_separators(self):
        s = "\npython \n \nprint(23)\n"
        code, language = parse_code_section(s, languages=["python"])
        self.assertEqual("print(23)", code)
        self.assertEqual("python", language)

    def test_with_language_followed_by_multiple_newlines(self):
        s = "\npython\n\nprint(23)\n"
        code, language = parse_code_section(s, languages=["python"])
        self.assertEqual("print(23)", code)
        self.assertEqual("python", language)

    def test_with_language_not_followed_by_newline(self):
        s = "\npython print(23)\n"
        code, language = parse_code_section(s, languages=["python"])
        self.assertEqual("print(23)", code)
        self.assertEqual("python", language)

        s = "\npythonprint(23)\n"
        code, language = parse_code_section(s, languages=["python"])
        self.assertEqual("print(23)", code)
        self.assertEqual("python", language)

    def test_with_language_in_random_case(self):
        s = "\nJaVascript\n\nprint(23)\n"
        code, language = parse_code_section(s, languages=["javascript"])
        self.assertEqual("print(23)", code)
        self.assertEqual("javascript", language)

    def test_with_code_preceded_by_spaces(self):
        s = "\npython\n\n  print(23)\n"
        code, language = parse_code_section(s, languages=["python"])
        self.assertEqual("print(23)", code)
        self.assertEqual("python", language)

    def test_with_exotic_language_print(self):
        s = "print\nprint(15)"
        code, language = parse_code_section(s, languages=["print"])
        self.assertEqual("print(15)", code)
        self.assertEqual("print", language)

    def test_without_language(self):
        s = "def foo(): pass"
        code, language = parse_code_section(s, languages=["python"])
        self.assertEqual(s, code)
        self.assertIsNone(language)

    def test_without_language_with_newlines(self):
        s = "print(32)\nprint(15)"
        code, language = parse_code_section(s, languages=["python"])
        self.assertEqual(s, code)
        self.assertIsNone(language)

    def test_with_blank_section(self):
        s = " \n\n  \n  "
        res = parse_code_section(s, languages=["python"])
        self.assertIsNone(res)

    def test_with_empty_code(self):
        s = "python\n\n  \n  "
        res = parse_code_section(s, languages=["python"])
        self.assertIsNone(res)


class DetectLanguageTests(unittest.TestCase):
    def test_with_python_code(self):
        code = "def foo(): pass"
        self.assertEqual("python", detect_language(code))

        code = "for num in range(20): pass"
        self.assertEqual("python", detect_language(code))

        code = "if some_thing < other_thing:\n"
        self.assertEqual("python", detect_language(code))

    def test_with_javascript_code(self):
        code = "const handler = e => console.log(e)"
        self.assertEqual("javascript", detect_language(code))

        code = "import React from 'react'\n"
        self.assertEqual("javascript", detect_language(code))


class ResponseFinializationTests(unittest.TestCase):
    def test(self):
        expected_text = "```some text```"
        text, token = finilize_response("```some text", "```")
        self.assertEqual(expected_text, text)
        self.assertEqual("```", token)

        text, token = finilize_response("```some text`", "``")
        self.assertEqual(expected_text, text)
        self.assertEqual("``", token)

        text, token = finilize_response("```some text``", "`")
        self.assertEqual(expected_text, text)
        self.assertEqual("`", token)

        text, token = finilize_response("```some text```", "```suffix")
        self.assertEqual(expected_text, text)
        self.assertEqual("", token)

        text, token = finilize_response("```some text", "```something else")
        self.assertEqual(expected_text, text)
        self.assertEqual("```", token)

        text, token = finilize_response("```some text`", "```")
        self.assertEqual(expected_text, text)
        self.assertEqual("``", token)
