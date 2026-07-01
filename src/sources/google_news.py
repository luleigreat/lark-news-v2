"""Google News RSS 搜索（按查询语种分流 + 噪音过滤）"""

from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import feedparser

from src.config import SPAM_SOURCES, SPAM_TITLE_PATTERNS, SPAM_URL_PATTERNS
from src.models import Article
from src.utils import clean_html, has_cjk, parse_feed_date

LOCALES = [
    {"hl": "zh-CN", "gl": "CN", "ceid": "CN:zh-Hans", "lang": "zh"},
    {"hl": "en-US", "gl": "US", "ceid": "US:en", "lang": "en"},
]
_LOCALE_BY_LANG = {loc["lang"]: loc for loc in LOCALES}


def locales_for_query(query: str) -> list[dict]:
    """按查询语种选择检索区域：含中文→中文区；纯英文→英文区。

    避免英文词（如 Crypto Card）在中文区召回大量交易所币价页，
    也避免中文泛词在英文区产生噪音。
    """
    lang = "zh" if has_cjk(query) else "en"
    return [_LOCALE_BY_LANG[lang]]


def is_spam(url: str, title: str, source: str = "") -> bool:
    u = (url or "").lower()
    t = (title or "").lower()
    s = (source or "").lower()
    if any(p in u for p in SPAM_URL_PATTERNS):
        return True
    if any(p in t for p in SPAM_TITLE_PATTERNS):
        return True
    if s and any(p == s or p in s for p in SPAM_SOURCES):
        return True
    return False


def search_locale(query: str, locale: dict, days_back: int) -> list[Article]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    return _search_locale(query, locale, cutoff, days_back)


def search(query: str, days_back: int) -> list[Article]:
    articles = []
    for locale in locales_for_query(query):
        articles.extend(search_locale(query, locale, days_back))
    return articles


def _search_locale(query: str, locale: dict, cutoff: datetime, days_back: int) -> list[Article]:
    try:
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
            title = entry.get("title", "")
            if not link or not title:
                continue

            source = entry.get("source", {}).get("title", f"Google News ({locale['lang']})")
            if is_spam(link, title, source):
                continue

            articles.append(Article(
                title=title,
                description=clean_html(entry.get("summary", entry.get("description", ""))),
                url=link,
                source=source,
                published=pub_time,
                language=locale["lang"],
            ))

        return articles
    except Exception as e:
        print(f"[Google News/{locale['lang']}] 请求异常: {e}")
        return []
