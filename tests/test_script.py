from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from personalized_radio_station.config import load_config
from personalized_radio_station.news import NewsItem
from personalized_radio_station.script import _build_prompt
from personalized_radio_station.weather import WeatherReport


class ScriptTests(unittest.TestCase):
    def test_prompt_requests_tuned_in_opening_and_single_voice(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"
            config_path.write_text(
                """
station_name: "Test Station"
style: "brief"
duration: "18 minutes"

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
  single_voice: true
  primary_voice: "host"
""".strip()
                + "\n"
            )
            config = load_config(config_path)

        prompt = _build_prompt(
            [
                NewsItem(
                    topic="ai",
                    title="A story",
                    link="https://example.com",
                    published_at=None,
                    source="Example",
                    summary=None,
                )
            ],
            WeatherReport(
                location="Lisbon",
                temperature_c=20,
                apparent_temperature_c=20,
                precipitation_mm=0,
                wind_speed_kmh=5,
                weather_code=1,
            ),
            config,
        )

        self.assertIn("already_on_air_listener_just_tuned_in", prompt)
        self.assertIn("station was already playing", prompt)
        self.assertIn('Use the voice label \\"host\\" for every segment.', prompt)
        self.assertIn('"target_duration": "18 minutes"', prompt)


if __name__ == "__main__":
    unittest.main()
