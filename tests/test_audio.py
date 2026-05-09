from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import wave

from personalized_radio_station.audio import concatenate_wavs, write_mock_wav


class AudioTests(unittest.TestCase):
    def test_writes_and_concatenates_wavs(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first = root / "first.wav"
            second = root / "second.wav"
            output = root / "episode.wav"

            write_mock_wav(first, duration_seconds=0.2)
            write_mock_wav(second, duration_seconds=0.2, frequency_hz=550)
            concatenate_wavs([first, second], output, silence_ms=100)

            self.assertTrue(output.exists())
            with wave.open(str(output), "rb") as wav:
                self.assertEqual(wav.getnchannels(), 1)
                self.assertEqual(wav.getframerate(), 24_000)
                self.assertGreater(wav.getnframes(), 0)


if __name__ == "__main__":
    unittest.main()
