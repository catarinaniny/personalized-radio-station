from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from personalized_radio_station.config import load_config
from personalized_radio_station.tts import synthesize_episode


class TtsTests(unittest.TestCase):
    def test_mock_tts_writes_segment_audio_and_episode_wav(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = root / "config.yaml"
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
            episode_dir = root / "episode"
            episode_dir.mkdir()
            episode = {
                "title": "Test",
                "segments": [
                    {"type": "intro", "voice": "host", "text": "Hello there."},
                    {"type": "news", "voice": "anchor", "text": "A story happened."},
                ],
            }

            result = synthesize_episode(episode, config, episode_dir)

            self.assertEqual(len(result.segment_files), 2)
            self.assertTrue((episode_dir / "episode.wav").exists())
            self.assertEqual(episode["segments"][0]["audio_file"], "audio/00-intro.wav")


if __name__ == "__main__":
    unittest.main()
