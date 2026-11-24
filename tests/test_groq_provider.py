"""Groq provider integration tests; no live API key or network required."""
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.llm import provider


class GroqProviderTests(unittest.TestCase):
    def setUp(self):
        self.old_key = os.environ.get("GROQ_API_KEY")
        os.environ["GROQ_API_KEY"] = "test-groq-key"

    def tearDown(self):
        if self.old_key is None:
            os.environ.pop("GROQ_API_KEY", None)
        else:
            os.environ["GROQ_API_KEY"] = self.old_key

    @patch("backend.llm.provider._post_json")
    def test_groq_uses_openai_compatible_endpoint_and_extracts_text(self, post):
        post.return_value = {"choices": [{"message": {"content": '{"answer":"ok"}'}}]}
        result = provider.call_groq("system", "user", "llama-3.3-70b-versatile", 20)
        self.assertEqual(result, '{"answer":"ok"}')
        args, kwargs = post.call_args
        self.assertEqual(args[0], "https://api.groq.com/openai/v1/chat/completions")
        self.assertEqual(args[1]["Authorization"], "Bearer test-groq-key")
        self.assertEqual(args[2]["response_format"], {"type": "json_object"})
        self.assertEqual(args[2]["model"], "llama-3.3-70b-versatile")

    def test_groq_is_registered(self):
        self.assertIn("groq", provider.PROVIDERS)
        self.assertEqual(provider.DEFAULT_MODELS["groq"], "llama-3.3-70b-versatile")

    def test_missing_key_fails_without_network_call(self):
        os.environ.pop("GROQ_API_KEY", None)
        with patch("backend.llm.provider._post_json") as post:
            with self.assertRaises(provider.LLMError):
                provider.call_groq("system", "user", "llama-3.3-70b-versatile", 20)
            post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
