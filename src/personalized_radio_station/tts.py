from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import json
import os
import re
import subprocess

from .audio import concatenate_wavs, write_mock_wav
from .config import AppConfig, TtsVoiceConfig


@dataclass(frozen=True)
class TtsResult:
    segment_files: list[Path]
    episode_file: Path | None


def synthesize_episode(episode: dict[str, Any], config: AppConfig, episode_dir: Path) -> TtsResult:
    if not config.tts.enabled:
        return TtsResult(segment_files=[], episode_file=None)

    provider = config.tts.provider.lower()
    audio_dir = episode_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    segment_files: list[Path] = []
    for index, segment in enumerate(episode.get("segments", [])):
        text = str(segment.get("text", "")).strip()
        if not text:
            continue

        voice_name = _voice_name_for_segment(segment, config)
        voice = config.tts.voices.get(voice_name) or next(iter(config.tts.voices.values()))
        extension = "wav" if provider in {"mock", "piper"} else config.tts.response_format
        segment_path = audio_dir / f"{index:02d}-{_slug(segment.get('type', 'segment'))}.{extension}"

        if provider == "mock":
            _synthesize_mock(text, voice_name, segment_path)
        elif provider == "openai":
            _synthesize_openai(text, voice, config, segment_path)
        elif provider == "piper":
            _synthesize_piper(text, voice, config, segment_path)
        else:
            raise ValueError(f"Unsupported TTS provider: {config.tts.provider}")

        segment["audio_file"] = str(segment_path.relative_to(episode_dir))
        segment_files.append(segment_path)

    episode_file = None
    if segment_files and all(path.suffix == ".wav" for path in segment_files):
        episode_file = concatenate_wavs(segment_files, episode_dir / "episode.wav")

    return TtsResult(segment_files=segment_files, episode_file=episode_file)


def _voice_name_for_segment(segment: dict[str, Any], config: AppConfig) -> str:
    explicit_voice = segment.get("voice")
    if explicit_voice:
        return str(explicit_voice)

    segment_type = str(segment.get("type", "news"))
    return config.voices.get(segment_type, "host")


def _synthesize_mock(text: str, voice_name: str, output_path: Path) -> None:
    duration = min(8.0, max(0.7, len(text) / 55))
    frequency = 360 + (sum(ord(char) for char in voice_name) % 260)
    write_mock_wav(output_path, duration_seconds=duration, frequency_hz=frequency)


def _synthesize_openai(
    text: str, voice: TtsVoiceConfig, config: AppConfig, output_path: Path
) -> None:
    api_key = os.environ.get(config.tts.api_key_env)
    if not api_key:
        raise RuntimeError(f"Missing {config.tts.api_key_env} for OpenAI TTS.")

    body: dict[str, Any] = {
        "model": config.tts.model,
        "voice": voice.voice,
        "input": text,
        "response_format": config.tts.response_format,
        "speed": voice.speed,
    }
    if voice.instructions:
        body["instructions"] = voice.instructions

    request = Request(
        f"{config.tts.api_base.rstrip('/')}/audio/speech",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=60) as response:
            output_path.write_bytes(response.read())
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI TTS failed: {exc.code} {details}") from exc


def _synthesize_piper(
    text: str, voice: TtsVoiceConfig, config: AppConfig, output_path: Path
) -> None:
    if not config.tts.piper_model_path:
        raise RuntimeError("Missing `tts.piper_model_path` for Piper TTS.")

    command = [
        config.tts.piper_path,
        "--model",
        config.tts.piper_model_path,
        "--output_file",
        str(output_path),
    ]
    if voice.speaker:
        command.extend(["--speaker", voice.speaker])

    try:
        subprocess.run(
            command,
            input=text,
            text=True,
            capture_output=True,
            check=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(f"Piper executable not found: {config.tts.piper_path}") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"Piper TTS failed: {exc.stderr}") from exc


def _slug(value: Any) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-")
    return slug or "segment"
