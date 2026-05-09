from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import unittest

from personalized_radio_station.news import NewsItem
from personalized_radio_station.pipeline import generate_episode
from personalized_radio_station.weather import WeatherReport


class PipelineTests(unittest.TestCase):
    def test_rejects_mock_ai_and_tts_without_test_opt_in(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = root / "config.yaml"
            config_path.write_text(
                """
station_name: "Test Station"
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

            with self.assertRaisesRegex(RuntimeError, "test-only LiteLLM model"):
                generate_episode(config_path, root / "episodes")

    def test_generates_episode_artifacts_with_mock_ai_and_tts(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = root / "config.yaml"
            output_dir = root / "episodes"
            config_path.write_text(
                """
station_name: "Test Station"
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
            news = [
                NewsItem(
                    topic="ai",
                    title="A useful AI story",
                    link="https://example.com/story",
                    published_at=None,
                    source="Example News",
                    summary="Summary",
                )
            ]
            weather = WeatherReport(
                location="Lisbon",
                temperature_c=21.0,
                apparent_temperature_c=21.0,
                precipitation_mm=0.0,
                wind_speed_kmh=8.0,
                weather_code=1,
            )

            with patch(
                "personalized_radio_station.pipeline.fetch_google_news",
                return_value=news,
            ), patch(
                "personalized_radio_station.pipeline.fetch_weather",
                return_value=weather,
            ):
                logs: list[str] = []
                episode_dir = generate_episode(
                    config_path,
                    output_dir,
                    allow_mock=True,
                    duration="unlimited",
                    log=logs.append,
                )

            self.assertTrue((episode_dir / "sources.json").exists())
            self.assertTrue((episode_dir / "script.md").exists())
            self.assertTrue((episode_dir / "episode.wav").exists())
            episode = json.loads((episode_dir / "episode.json").read_text())
            self.assertEqual(episode["audio_file"], "episode.wav")
            self.assertEqual(episode["timing"]["target_duration"], "unlimited")
            self.assertGreater(episode["timing"]["script_words"], 0)
            self.assertIn("audio_duration_seconds", episode["timing"])
            self.assertIn("measured_words_per_minute", episode["timing"])
            self.assertTrue((output_dir / "latest").is_symlink())
            self.assertTrue(any("Fetching Google News RSS" in log for log in logs))
            self.assertTrue(any("targeting unlimited" in log for log in logs))
            self.assertTrue(any("Rendering TTS" in log for log in logs))


if __name__ == "__main__":
    unittest.main()
