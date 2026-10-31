import unittest
from unittest.mock import MagicMock, patch

import requests

from core.llm import chat_with_tools, stream_chat


def ollama_reply(*lines):
    response = MagicMock()
    response.iter_lines.return_value = lines
    return response


ERROR_DURING_ANSWER = (b'{"message": {"content": "Hel"}}', b'{"error": "model runner crashed"}')


class OllamaErrorDuringAnswer(unittest.TestCase):
    @patch("core.llm.requests.post", return_value=ollama_reply(*ERROR_DURING_ANSWER))
    def test_terminal_reports_it_without_crashing(self, _post):
        self.assertIsNone(chat_with_tools([], "model", "url"))

    @patch("core.llm.requests.post", return_value=ollama_reply(*ERROR_DURING_ANSWER))
    def test_web_stream_raises_what_it_catches(self, _post):
        with self.assertRaises(requests.exceptions.RequestException):
            list(stream_chat([], "model", "url"))

    @patch("core.llm.requests.post", return_value=ollama_reply(
        b'{"message": {"content": "Hel"}}', b'{"message": {"content": "lo"}}'))
    def test_normal_answer_is_unchanged(self, _post):
        self.assertEqual(chat_with_tools([], "model", "url"), ("Hello", []))


if __name__ == "__main__":
    unittest.main()
