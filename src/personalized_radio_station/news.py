from __future__ import annotations

from dataclasses import asdict, dataclass
from email.utils import parsedate_to_datetime
from html import unescape
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
import re
import xml.etree.ElementTree as ET

from .config import NewsConfig


@dataclass(frozen=True)
class NewsItem:
    topic: str
    title: str
    link: str
    published_at: str | None
    source: str | None
    summary: str | None

    def to_dict(self) -> dict[str, str | None]:
        return asdict(self)


def fetch_google_news(config: NewsConfig, limit_per_topic: int = 5) -> list[NewsItem]:
    items: list[NewsItem] = []

    for topic in config.topics:
        feed_url = _google_news_url(topic, config)
        feed_xml = _fetch(feed_url)
        items.extend(_parse_feed(feed_xml, topic)[:limit_per_topic])

    return _dedupe_by_title(items)


def _google_news_url(topic: str, config: NewsConfig) -> str:
    country = config.country.upper()
    language = config.language
    return (
        "https://news.google.com/rss/search"
        f"?q={quote_plus(topic)}"
        f"&hl={quote_plus(language)}"
        f"&gl={quote_plus(country)}"
        f"&ceid={quote_plus(country + ':' + language.split('-')[0])}"
    )


def _fetch(url: str) -> str:
    request = Request(url, headers={"User-Agent": "personalized-radio-station/0.1"})
    with urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8", errors="replace")


def _parse_feed(feed_xml: str, topic: str) -> list[NewsItem]:
    root = ET.fromstring(feed_xml)
    parsed_items: list[NewsItem] = []

    for item in root.findall("./channel/item"):
        title = _text(item, "title") or "Untitled"
        parsed_items.append(
            NewsItem(
                topic=topic,
                title=title,
                link=_text(item, "link") or "",
                published_at=_parse_date(_text(item, "pubDate")),
                source=_text(item, "source"),
                summary=_clean_html(_text(item, "description")),
            )
        )

    return parsed_items


def _text(node: ET.Element, child_name: str) -> str | None:
    child = node.find(child_name)
    if child is None or child.text is None:
        return None
    return child.text.strip()


def _parse_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).isoformat()
    except (TypeError, ValueError):
        return value


def _clean_html(value: str | None) -> str | None:
    if not value:
        return None
    text = re.sub(r"<[^>]+>", " ", value)
    text = re.sub(r"\s+", " ", unescape(text))
    return text.strip()


def _dedupe_by_title(items: list[NewsItem]) -> list[NewsItem]:
    seen: set[str] = set()
    deduped: list[NewsItem] = []

    for item in items:
        key = re.sub(r"\W+", "", item.title.lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    return deduped
