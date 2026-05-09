from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from personalized_radio_station.news import NewsItem
from personalized_radio_station.sources import fetch_sources, main
from personalized_radio_station.weather import WeatherReport


class SourcesTests(unittest.TestCase):
    def test_fetch_sources_returns_weather_and_news(self) -> None:
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
  model: "openrouter/openrouter/auto"
""".strip()
                + "\n"
            )

            with patch(
                "personalized_radio_station.sources.fetch_google_news",
                return_value=[
                    NewsItem(
                        topic="ai",
                        title="A source story",
                        link="https://example.com",
                        published_at=None,
                        source="Example",
                        summary=None,
                    )
                ],
            ), patch(
                "personalized_radio_station.sources.fetch_weather",
                return_value=WeatherReport(
                    location="Lisbon",
                    temperature_c=20,
                    apparent_temperature_c=20,
                    precipitation_mm=0,
                    wind_speed_kmh=5,
                    weather_code=1,
                ),
            ):
                result = fetch_sources(config_path, limit_per_topic=1)

        self.assertEqual(result["weather"]["location"], "Lisbon")
        self.assertEqual(result["news"][0]["title"], "A source story")

    def test_sources_cli_prints_json(self) -> None:
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
  model: "openrouter/openrouter/auto"
""".strip()
                + "\n"
            )

            with patch(
                "sys.argv",
                [
                    "sources",
                    "--config",
                    str(config_path),
                    "--limit-per-topic",
                    "1",
                ],
            ), patch(
                "personalized_radio_station.sources.fetch_sources",
                return_value={"weather": {"location": "Lisbon"}, "news": []},
            ), patch("builtins.print") as print_mock:
                main()

        printed = print_mock.call_args.args[0]
        self.assertIn('"weather"', printed)
        self.assertIn('"Lisbon"', printed)


if __name__ == "__main__":
    unittest.main()
