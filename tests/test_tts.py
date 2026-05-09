from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
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
            self.assertEqual(episode["segments"][0]["voice"], "host")
            self.assertEqual(episode["segments"][1]["voice"], "host")

    def test_elevenlabs_tts_uses_litellm_speech(self) -> None:
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
  provider: "elevenlabs"
  model: "elevenlabs/eleven_multilingual_v2"
  response_format: "mp3"
  api_key_env: "ELEVENLABS_API_KEY"
  voices:
    host:
      voice: "alloy"
      settings:
        stability: 0.5
        similarity_boost: 0.8
""".strip()
                + "\n"
            )
            config = load_config(config_path)
            episode_dir = root / "episode"
            episode_dir.mkdir()
            episode = {
                "title": "Test",
                "segments": [{"type": "intro", "voice": "host", "text": "Hello."}],
            }

            captured = {}

            class FakeSpeechResponse:
                def read(self):
                    return b"mp3-bytes"

            def fake_speech(**kwargs):
                captured.update(kwargs)
                return FakeSpeechResponse()

            fake_litellm = SimpleNamespace(speech=fake_speech)
            with patch.dict("os.environ", {"ELEVENLABS_API_KEY": "test-key"}), patch.dict(
                "sys.modules", {"litellm": fake_litellm}
            ), patch(
                "personalized_radio_station.tts.concatenate_audio_files",
                return_value=episode_dir / "episode.mp3",
            ):
                result = synthesize_episode(episode, config, episode_dir)

            self.assertEqual(result.segment_files[0].read_bytes(), b"mp3-bytes")
            self.assertEqual(captured["model"], "elevenlabs/eleven_multilingual_v2")
            self.assertEqual(captured["voice"], "alloy")
            self.assertEqual(captured["response_format"], "mp3")
            self.assertEqual(captured["api_key"], "test-key")
            self.assertEqual(captured["voice_settings"]["stability"], 0.5)

    def test_single_voice_forces_same_voice_for_all_mp3_segments(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = root / "config.yaml"
            config_path.write_text(
                """
station_name: "Test"
style: "brief"
duration: "1 minute"

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
  provider: "elevenlabs"
  model: "elevenlabs/eleven_multilingual_v2"
  response_format: "mp3"
  api_key_env: "ELEVENLABS_API_KEY"
  single_voice: true
  primary_voice: "host"
  voices:
    host:
      voice: "alloy"
    anchor:
      voice: "onyx"
""".strip()
                + "\n"
            )
            config = load_config(config_path)
            episode_dir = root / "episode"
            episode_dir.mkdir()
            episode = {
                "title": "Test",
                "segments": [
                    {"type": "intro", "voice": "host", "text": "Intro."},
                    {"type": "news", "voice": "anchor", "text": "News."},
                ],
            }

            voices_used = []

            class FakeSpeechResponse:
                def read(self):
                    return b"mp3-bytes"

            def fake_speech(**kwargs):
                voices_used.append(kwargs["voice"])
                return FakeSpeechResponse()

            fake_litellm = SimpleNamespace(speech=fake_speech)
            with patch.dict("os.environ", {"ELEVENLABS_API_KEY": "test-key"}), patch.dict(
                "sys.modules", {"litellm": fake_litellm}
            ), patch(
                "personalized_radio_station.tts.concatenate_audio_files",
                return_value=episode_dir / "episode.mp3",
            ):
                synthesize_episode(episode, config, episode_dir)

            self.assertEqual(voices_used, ["alloy", "alloy"])
            self.assertEqual([segment["voice"] for segment in episode["segments"]], ["host", "host"])

    def test_litellm_tts_provider_streams_to_file(self) -> None:
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
  provider: "litellm"
  model: "openai/gpt-4o-mini-tts"
  response_format: "wav"
  api_key_env: "OPENAI_API_KEY"
  voices:
    host:
      voice: "alloy"
      instructions: "Warm."
""".strip()
                + "\n"
            )
            config = load_config(config_path)
            episode_dir = root / "episode"
            episode_dir.mkdir()
            episode = {
                "title": "Test",
                "segments": [{"type": "intro", "voice": "host", "text": "Hello."}],
            }

            captured = {}

            class FakeSpeechResponse:
                def stream_to_file(self, path):
                    Path(path).write_bytes(b"wav-bytes")

            def fake_speech(**kwargs):
                captured.update(kwargs)
                return FakeSpeechResponse()

            fake_litellm = SimpleNamespace(speech=fake_speech)
            with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}), patch.dict(
                "sys.modules", {"litellm": fake_litellm}
            ), patch(
                "personalized_radio_station.tts.concatenate_wavs",
                return_value=episode_dir / "episode.wav",
            ):
                result = synthesize_episode(episode, config, episode_dir)

            self.assertEqual(result.segment_files[0].read_bytes(), b"wav-bytes")
            self.assertEqual(captured["model"], "openai/gpt-4o-mini-tts")
            self.assertEqual(captured["voice"], "alloy")
            self.assertEqual(captured["api_key"], "test-key")


if __name__ == "__main__":
    unittest.main()
