from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import unittest

from personalized_radio_station.cli import main


class CliTests(unittest.TestCase):
    def test_check_reports_missing_openrouter_key(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = _write_openrouter_config(Path(temp_dir))

            with patch.dict("os.environ", {}, clear=True), patch("builtins.print") as print_mock:
                with self.assertRaises(SystemExit) as raised:
                    main(["check", "--config", str(config_path)])

        self.assertEqual(raised.exception.code, 1)
        printed = "\n".join(call.args[0] for call in print_mock.call_args_list)
        self.assertIn("OPENROUTER_API_KEY", printed)

    def test_start_writes_detached_state(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = _write_openrouter_config(root)
            env_path = root / ".env"
            env_path.write_text("OPENROUTER_API_KEY=test-key\n")
            runs_dir = root / "runs"
            output_dir = root / "episodes"

            class FakeProcess:
                pid = 12345

            with patch("subprocess.Popen", return_value=FakeProcess()) as popen_mock, patch(
                "builtins.print"
            ):
                main(
                    [
                        "start",
                        "--config",
                        str(config_path),
                        "--env",
                        str(env_path),
                        "--output-dir",
                        str(output_dir),
                        "--runs-dir",
                        str(runs_dir),
                    ]
                )

            state_path = runs_dir / "radio.pid.json"
            state = json.loads(state_path.read_text())

        self.assertEqual(state["pid"], 12345)
        self.assertIn("personalized_radio_station.cli", state["command"])
        self.assertIn("generate", state["command"])
        self.assertTrue(state["log_file"].endswith(".log"))
        self.assertEqual(popen_mock.call_args.kwargs["start_new_session"], True)

    def test_status_reads_detached_state(self) -> None:
        with TemporaryDirectory() as temp_dir:
            runs_dir = Path(temp_dir) / "runs"
            runs_dir.mkdir()
            (runs_dir / "radio.pid.json").write_text(
                json.dumps(
                    {
                        "pid": 12345,
                        "started_at": "2026-05-09T12:00:00",
                        "log_file": str(runs_dir / "run.log"),
                    }
                )
            )

            with patch("os.kill"), patch("builtins.print") as print_mock:
                main(["status", "--runs-dir", str(runs_dir)])

        printed = "\n".join(call.args[0] for call in print_mock.call_args_list)
        self.assertIn("PID 12345: running", printed)


def _write_openrouter_config(root: Path) -> Path:
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
  model: "openrouter/openrouter/auto"
  api_key_env: "OPENROUTER_API_KEY"

tts:
  enabled: false
""".strip()
        + "\n"
    )
    return config_path


if __name__ == "__main__":
    unittest.main()
