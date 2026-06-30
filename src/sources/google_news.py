"""Google News RSS 搜索（中英文双语言）"""

from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import feedparser

from src.models import Article
from src.utils import clean_html

LOCALES = [
    {"hl": "zh-CN", "gl": "CN", "ceid": "CN:zh-Hans", "lang": "zh"},
    {"hl": "en-US", "gl": "US", "ceid": "US:en", "lang": "en"},
]


def search(query: str, days_back: int) -> list[Article]:
    articles = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

    for locale in LOCALES:
        articles.extend(_search_locale(query, locale, cutoff))

    return articles


def _search_locale(query: str, locale: dict, cutoff: datetime) -> list[Article]:
    try:
        url = (
            f"https://news.google.com/rss/search"
            f"?q={quote(query)}&hl={locale['hl']}&gl={locale['gl']}&ceid={locale['ceid']}"
        )
        feed = feedparser.parse(url)
        articles = []

        for entry in feed.entries:
            pub_time = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                pub_time = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)

            if pub_time and pub_time < cutoff:
                continue

            link = entry.get("link", "")
            if not link or not entry.get("title"):
                continue

            articles.append(Article(
                title=entry.get("title", ""),
                description=clean_html(entry.get("summary", entry.get("description", ""))),
                url=link,
                source=entry.get("source", {}).get("title", f"Google News ({locale['lang']})"),
                published=pub_time,
                language=locale["lang"],
            ))

        return articles
    except Exception as e:
        print(f"[Google News/{locale['lang']}] 请求异常: {e}")
        return []
