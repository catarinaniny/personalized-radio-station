from unittest.mock import patch
import threading
import time
import unittest

from personalized_radio_station.config import NewsConfig
from personalized_radio_station.news import _parse_feed, fetch_news


class NewsTests(unittest.TestCase):
    def test_fetch_news_fetches_google_and_rss_feeds_in_parallel(self) -> None:
        config = NewsConfig(
            topics=["ai"],
            rss_feeds=[
                "https://example.com/tech.xml",
                "https://example.com/products.xml",
            ],
        )
        active = 0
        max_active = 0
        lock = threading.Lock()

        def fake_fetch(url: str) -> str:
            nonlocal active, max_active
            with lock:
                active += 1
                max_active = max(max_active, active)
            time.sleep(0.03)
            with lock:
                active -= 1
            if "news.google.com" in url:
                return _rss("Google News", "Google story")
            if "tech.xml" in url:
                return _rss("Tech Feed", "Tech story")
            return _rss("Product Feed", "Product story")

        with patch("personalized_radio_station.news._fetch", side_effect=fake_fetch):
            items = fetch_news(config, limit_per_feed=1)

        self.assertGreater(max_active, 1)
        self.assertEqual(
            [item.title for item in items],
            ["Google story", "Tech story", "Product story"],
        )
        self.assertEqual(
            [item.source for item in items],
            ["Google News", "Tech Feed", "Product Feed"],
        )

    def test_parse_atom_feed(self) -> None:
        feed_xml = """
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Atom Source</title>
  <entry>
    <title>Atom story</title>
    <link href="https://example.com/atom-story" />
    <updated>2026-05-09T12:00:00Z</updated>
    <summary>Short atom summary</summary>
  </entry>
</feed>
""".strip()

        items = _parse_feed(feed_xml, "fallback")

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].topic, "fallback")
        self.assertEqual(items[0].link, "https://example.com/atom-story")
        self.assertEqual(items[0].summary, "Short atom summary")


def _rss(channel_title: str, item_title: str) -> str:
    return f"""
<rss version="2.0">
  <channel>
    <title>{channel_title}</title>
    <item>
      <title>{item_title}</title>
      <link>https://example.com/{item_title.replace(" ", "-").lower()}</link>
      <description><![CDATA[<p>Summary for {item_title}</p>]]></description>
    </item>
  </channel>
</rss>
""".strip()


if __name__ == "__main__":
    unittest.main()
