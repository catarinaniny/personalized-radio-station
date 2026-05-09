from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from personalized_radio_station.config import load_config


class ConfigTests(unittest.TestCase):
    def test_example_config_uses_openrouter_by_default(self) -> None:
        config = load_config("config.example.yaml")

        self.assertEqual(config.ai.model, "openrouter/openrouter/auto")
        self.assertEqual(config.ai.api_key_env, "OPENROUTER_API_KEY")
        self.assertEqual(config.tts.provider, "elevenlabs")
        self.assertEqual(config.tts.model, "elevenlabs/eleven_multilingual_v2")
        self.assertEqual(config.tts.api_key_env, "ELEVENLABS_API_KEY")
        self.assertTrue(config.tts.enabled)

    def test_loads_ai_and_tts_config(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"
            config_path.write_text(
                """
station_name: "Test Station"
style: "brief"
episode_minutes: 3

news:
  topics:
    - "ai"

weather:
  name: "Lisbon"
  latitude: 38.7
  longitude: -9.1

ai:
  model: "openrouter/meta-llama/llama-3.1-8b-instruct"
  api_key_env: "OPENROUTER_API_KEY"

tts:
  enabled: true
  provider: "elevenlabs"
  model: "elevenlabs/eleven_multilingual_v2"
  voices:
    host:
      voice: "alloy"
      settings:
        stability: 0.4
        similarity_boost: 0.8
""".strip()
                + "\n"
            )

            config = load_config(config_path)

        self.assertEqual(config.station_name, "Test Station")
        self.assertEqual(config.ai.api_key_env, "OPENROUTER_API_KEY")
        self.assertTrue(config.tts.enabled)
        self.assertEqual(config.tts.provider, "elevenlabs")
        self.assertEqual(config.tts.voices["host"].voice, "alloy")
        self.assertEqual(config.tts.voices["host"].settings["stability"], 0.4)


if __name__ == "__main__":
    unittest.main()
