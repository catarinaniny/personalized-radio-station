from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from personalized_radio_station.config import load_config
from personalized_radio_station.runtime import missing_runtime_requirements


class RuntimeTests(unittest.TestCase):
    def test_detects_missing_litellm_and_tts_keys(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"
            config_path.write_text(
                """
station_name: "Test"
style: "brief"
episode_minutes: 1

news:
  topics:
    - "ai"

weather:
  name: "Lisbon"
  latitude: 38.7
  longitude: -9.1

ai:
  model: "openrouter/meta-llama/llama-3.1-8b-instruct"

tts:
  enabled: true
  provider: "openai"
  api_key_env: "OPENAI_API_KEY"
""".strip()
                + "\n"
            )
            config = load_config(config_path)

        with patch.dict("os.environ", {}, clear=True):
            missing = missing_runtime_requirements(config)

        self.assertIn("OPENROUTER_API_KEY", missing[0])
        self.assertIn("OPENAI_API_KEY", missing[1])

    def test_detects_provider_specific_litellm_keys(self) -> None:
        examples = [
            ("openai/gpt-4.1-mini", "OPENAI_API_KEY"),
            ("anthropic/claude-3-5-haiku-latest", "ANTHROPIC_API_KEY"),
            ("openrouter/meta-llama/llama-3.3-70b-instruct", "OPENROUTER_API_KEY"),
        ]

        for model, expected_env in examples:
            with self.subTest(model=model), TemporaryDirectory() as temp_dir:
                config_path = Path(temp_dir) / "config.yaml"
                config_path.write_text(
                    f"""
station_name: "Test"
style: "brief"
episode_minutes: 1

news:
  topics:
    - "ai"

weather:
  name: "Lisbon"
  latitude: 38.7
  longitude: -9.1

ai:
  model: "{model}"

tts:
  enabled: false
""".strip()
                    + "\n"
                )
                config = load_config(config_path)

                with patch.dict("os.environ", {expected_env: ""}, clear=True):
                    missing = missing_runtime_requirements(config)

            self.assertEqual(missing, [f"{expected_env} for LiteLLM model `{model}`"])

    def test_mock_providers_are_rejected_in_normal_runtime(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"
            config_path.write_text(
                """
station_name: "Test"
style: "brief"
episode_minutes: 1

news:
  topics:
    - "ai"

weather:
  name: "Lisbon"
  latitude: 38.7
  longitude: -9.1

ai:
  model: "mock"

tts:
  enabled: true
  provider: "mock"
""".strip()
                + "\n"
            )
            config = load_config(config_path)

        with patch.dict("os.environ", {}, clear=True):
            missing = missing_runtime_requirements(config)

        self.assertIn("test-only LiteLLM model `mock`", missing[0])
        self.assertIn("test-only TTS provider `mock`", missing[1])

    def test_tests_can_explicitly_allow_mock_providers(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"
            config_path.write_text(
                """
station_name: "Test"
style: "brief"
episode_minutes: 1

news:
  topics:
    - "ai"

weather:
  name: "Lisbon"
  latitude: 38.7
  longitude: -9.1

ai:
  model: "mock"

tts:
  enabled: true
  provider: "mock"
""".strip()
                + "\n"
            )
            config = load_config(config_path)

        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(missing_runtime_requirements(config, allow_mock=True), [])

    def test_ollama_needs_no_api_key(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"
            config_path.write_text(
                """
station_name: "Test"
style: "brief"
episode_minutes: 1

news:
  topics:
    - "ai"

weather:
  name: "Lisbon"
  latitude: 38.7
  longitude: -9.1

ai:
  model: "ollama/llama3.1"

tts:
  enabled: false
""".strip()
                + "\n"
            )
            config = load_config(config_path)

        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(missing_runtime_requirements(config), [])


if __name__ == "__main__":
    unittest.main()
