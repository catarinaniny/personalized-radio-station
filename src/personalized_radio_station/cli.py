from __future__ import annotations

from argparse import ArgumentParser, Namespace
from datetime import datetime
from pathlib import Path
from typing import Any
import json
import os
import subprocess
import sys

from .config import load_config
from .env import load_env_file
from .pipeline import generate_episode
from .runtime import missing_runtime_requirements
from .sources import fetch_sources


DEFAULT_CONFIG = Path("config.yaml")
DEFAULT_ENV = Path(".env")
DEFAULT_OUTPUT_DIR = Path("episodes")
DEFAULT_RUNS_DIR = Path("runs")


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "handler"):
        parser.print_help()
        raise SystemExit(2)

    args.handler(args)


def _build_parser() -> ArgumentParser:
    parser = ArgumentParser(prog="radio", description="Personalized radio backend CLI.")
    subparsers = parser.add_subparsers(dest="command")

    check = subparsers.add_parser("check", help="Validate runtime config and credentials.")
    _add_common_options(check)
    check.add_argument("--skip-tts", action="store_true", help="Do not validate TTS credentials.")
    check.set_defaults(handler=_handle_check)

    sources = subparsers.add_parser("sources", help="Fetch Google News RSS and weather only.")
    sources.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Path to config YAML.")
    sources.add_argument(
        "--limit-per-topic",
        type=int,
        default=3,
        help="Maximum Google News RSS items to keep for each topic.",
    )
    sources.set_defaults(handler=_handle_sources)

    generate = subparsers.add_parser("generate", help="Generate an episode in the foreground.")
    _add_common_options(generate)
    generate.add_argument("--skip-tts", action="store_true", help="Generate script only.")
    generate.set_defaults(handler=_handle_generate)

    start = subparsers.add_parser("start", help="Generate an episode in a detached process.")
    _add_common_options(start)
    start.add_argument("--skip-tts", action="store_true", help="Generate script only.")
    start.add_argument(
        "--runs-dir",
        type=Path,
        default=DEFAULT_RUNS_DIR,
        help="Directory for detached logs and PID state.",
    )
    start.set_defaults(handler=_handle_start)

    status = subparsers.add_parser("status", help="Show detached process status.")
    status.add_argument(
        "--runs-dir",
        type=Path,
        default=DEFAULT_RUNS_DIR,
        help="Directory containing detached PID state.",
    )
    status.set_defaults(handler=_handle_status)

    return parser


def _add_common_options(parser: ArgumentParser) -> None:
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Path to config YAML.")
    parser.add_argument("--env", type=Path, default=DEFAULT_ENV, help="Path to .env file.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where episode artifacts are saved.",
    )


def _handle_check(args: Namespace) -> None:
    load_env_file(args.env)
    config_path = _resolve_config_path(args.config)
    missing = _missing_requirements(config_path, include_tts=not args.skip_tts)
    if missing:
        _print_missing(missing)
        raise SystemExit(1)

    print("Runtime requirements look OK.")


def _handle_sources(args: Namespace) -> None:
    config_path = _resolve_config_path(args.config)
    print(json.dumps(fetch_sources(config_path, args.limit_per_topic), indent=2))


def _handle_generate(args: Namespace) -> None:
    load_env_file(args.env)
    config_path = _resolve_config_path(args.config)
    episode_dir = generate_episode(
        config_path,
        args.output_dir,
        skip_tts=args.skip_tts,
    )
    print(f"Generated episode: {episode_dir}")


def _handle_start(args: Namespace) -> None:
    load_env_file(args.env)
    config_path = _resolve_config_path(args.config)
    missing = _missing_requirements(config_path, include_tts=not args.skip_tts)
    if missing:
        _print_missing(missing)
        raise SystemExit(1)

    args.runs_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    log_path = args.runs_dir / f"{timestamp}.log"
    state_path = _state_path(args.runs_dir)

    command = [
        sys.executable,
        "-m",
        "personalized_radio_station.cli",
        "generate",
        "--config",
        str(config_path),
        "--env",
        str(args.env),
        "--output-dir",
        str(args.output_dir),
    ]
    if args.skip_tts:
        command.append("--skip-tts")

    log_file = log_path.open("ab")
    process = subprocess.Popen(
        command,
        cwd=Path.cwd(),
        stdout=log_file,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    log_file.close()

    state = {
        "pid": process.pid,
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "log_file": str(log_path),
        "command": command,
    }
    state_path.write_text(json.dumps(state, indent=2) + "\n")

    print(f"Started detached episode generation with PID {process.pid}.")
    print(f"Log: {log_path}")
    print(f"State: {state_path}")


def _handle_status(args: Namespace) -> None:
    state_path = _state_path(args.runs_dir)
    if not state_path.exists():
        print("No detached run state found.")
        raise SystemExit(1)

    state = json.loads(state_path.read_text())
    pid = int(state["pid"])
    status = "running" if _pid_is_running(pid) else "not running"
    print(f"PID {pid}: {status}")
    print(f"Started: {state.get('started_at')}")
    print(f"Log: {state.get('log_file')}")


def _missing_requirements(config_path: Path, include_tts: bool) -> list[str]:
    config = load_config(config_path)
    return missing_runtime_requirements(config, include_tts=include_tts)


def _print_missing(missing: list[str]) -> None:
    print("Missing runtime requirements:")
    for item in missing:
        print(f"- {item}")


def _resolve_config_path(path: Path) -> Path:
    if not path.exists() and path == DEFAULT_CONFIG:
        return Path("config.example.yaml")
    return path


def _state_path(runs_dir: Path) -> Path:
    return runs_dir / "radio.pid.json"


def _pid_is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


if __name__ == "__main__":
    main()
