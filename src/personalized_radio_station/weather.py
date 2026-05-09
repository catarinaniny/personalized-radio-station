from __future__ import annotations

from dataclasses import asdict, dataclass
from urllib.parse import urlencode
from urllib.request import urlopen
import json

from .config import WeatherConfig


@dataclass(frozen=True)
class WeatherReport:
    location: str
    temperature_c: float | None
    apparent_temperature_c: float | None
    precipitation_mm: float | None
    wind_speed_kmh: float | None
    weather_code: int | None

    def to_dict(self) -> dict[str, float | int | str | None]:
        return asdict(self)


def fetch_weather(config: WeatherConfig) -> WeatherReport:
    params = urlencode(
        {
            "latitude": config.latitude,
            "longitude": config.longitude,
            "current": ",".join(
                [
                    "temperature_2m",
                    "apparent_temperature",
                    "precipitation",
                    "wind_speed_10m",
                    "weather_code",
                ]
            ),
            "timezone": "auto",
        }
    )
    url = f"https://api.open-meteo.com/v1/forecast?{params}"

    with urlopen(url, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))

    current = payload.get("current", {})
    return WeatherReport(
        location=config.name,
        temperature_c=current.get("temperature_2m"),
        apparent_temperature_c=current.get("apparent_temperature"),
        precipitation_mm=current.get("precipitation"),
        wind_speed_kmh=current.get("wind_speed_10m"),
        weather_code=current.get("weather_code"),
    )
