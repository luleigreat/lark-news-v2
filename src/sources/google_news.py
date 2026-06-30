"""Google News RSS 搜索（中英文双语言）"""

from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import feedparser

from src.models import Article
from src.utils import clean_html, parse_feed_date

LOCALES = [
    {"hl": "zh-CN", "gl": "CN", "ceid": "CN:zh-Hans", "lang": "zh"},
    {"hl": "en-US", "gl": "US", "ceid": "US:en", "lang": "en"},
]


def search_locale(query: str, locale: dict, days_back: int) -> list[Article]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    return _search_locale(query, locale, cutoff, days_back)


def search(query: str, days_back: int) -> list[Article]:
    articles = []
    for locale in LOCALES:
        articles.extend(search_locale(query, locale, days_back))
    return articles


def _search_locale(query: str, locale: dict, cutoff: datetime, days_back: int) -> list[Article]:
    try:
        # when 限定时间范围，提升近期新闻召回
        when = f"when:{days_back}d" if days_back <= 7 else ""
        q = f"{query} {when}".strip()
        url = (
            f"https://news.google.com/rss/search"
            f"?q={quote(q)}&hl={locale['hl']}&gl={locale['gl']}&ceid={locale['ceid']}"
        )
        feed = feedparser.parse(url)
        articles = []

        for entry in feed.entries:
            pub_time = parse_feed_date(entry)

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
