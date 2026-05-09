from types import SimpleNamespace
from unittest.mock import patch
import unittest

from personalized_radio_station.ai import generate_text
from personalized_radio_station.config import AiConfig


class AiTests(unittest.TestCase):
    def test_openrouter_reasoning_is_sent_in_extra_body(self) -> None:
        captured = {}

        def fake_completion(**kwargs):
            captured.update(kwargs)
            return _response("ok")

        fake_litellm = SimpleNamespace(completion=fake_completion)
        config = AiConfig(
            model="openrouter/openai/gpt-oss-20b:nitro",
            api_key_env="OPENROUTER_API_KEY",
            max_tokens=4000,
            reasoning={"effort": "low", "exclude": True},
        )

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}), patch.dict(
            "sys.modules", {"litellm": fake_litellm}
        ):
            content = generate_text([{"role": "user", "content": "hello"}], config)

        self.assertEqual(content, "ok")
        self.assertEqual(captured["max_tokens"], 4000)
        self.assertEqual(
            captured["extra_body"],
            {"reasoning": {"effort": "low", "exclude": True}},
        )
        self.assertNotIn("reasoning_effort", captured)

    def test_non_openrouter_reasoning_uses_reasoning_effort(self) -> None:
        captured = {}

        def fake_completion(**kwargs):
            captured.update(kwargs)
            return _response("ok")

        fake_litellm = SimpleNamespace(completion=fake_completion)
        config = AiConfig(
            model="openai/gpt-5.4-mini",
            api_key_env="OPENAI_API_KEY",
            reasoning={"effort": "low", "exclude": True},
        )

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}), patch.dict(
            "sys.modules", {"litellm": fake_litellm}
        ):
            generate_text([{"role": "user", "content": "hello"}], config)

        self.assertEqual(captured["reasoning_effort"], "low")
        self.assertNotIn("extra_body", captured)

    def test_empty_response_error_includes_debug_details(self) -> None:
        def fake_completion(**kwargs):
            return _response(
                "",
                finish_reason="length",
                usage={"prompt_tokens": 100, "completion_tokens": 4000, "total_tokens": 4100},
                reasoning="internal trace present",
            )

        fake_litellm = SimpleNamespace(completion=fake_completion)
        config = AiConfig(model="openrouter/openai/gpt-oss-20b:nitro")

        with patch.dict("sys.modules", {"litellm": fake_litellm}):
            with self.assertRaisesRegex(RuntimeError, "finish_reason=length") as raised:
                generate_text([{"role": "user", "content": "hello"}], config)

        message = str(raised.exception)
        self.assertIn("completion_tokens=4000", message)
        self.assertIn("reasoning_present=True", message)
        self.assertIn("lowering ai.reasoning.effort", message)


def _response(
    content: str,
    finish_reason: str = "stop",
    usage: dict | None = None,
    reasoning: str | None = None,
):
    message = SimpleNamespace(content=content)
    if reasoning is not None:
        message.reasoning = reasoning
    choice = SimpleNamespace(message=message, finish_reason=finish_reason)
    return SimpleNamespace(choices=[choice], usage=usage or {})


if __name__ == "__main__":
    unittest.main()
