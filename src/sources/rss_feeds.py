"""垂直 RSS 源搜索（关键词过滤）"""

from datetime import datetime, timedelta, timezone

import feedparser

from src.config import RSS_FEEDS
from src.models import Article
from src.utils import clean_html, parse_feed_date


def search_feed(feed_cfg: dict, keywords: list[str], days_back: int) -> list[Article]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    return _fetch_feed(feed_cfg, keywords, cutoff)


def search(keywords: list[str], days_back: int) -> list[Article]:
    articles = []
    for feed_cfg in RSS_FEEDS:
        articles.extend(search_feed(feed_cfg, keywords, days_back))
    return articles


def _fetch_feed(feed_cfg: dict, keywords: list[str], cutoff: datetime) -> list[Article]:
    try:
        feed = feedparser.parse(feed_cfg["url"])
        articles = []
        kw_lower = [k.lower() for k in keywords]

        for entry in feed.entries:
            title = entry.get("title", "")
            summary = clean_html(entry.get("summary", entry.get("description", "")))
            text = f"{title} {summary}".lower()

            if not any(kw in text for kw in kw_lower):
                continue

            pub_time = parse_feed_date(entry)

            if pub_time and pub_time < cutoff:
                continue

            link = entry.get("link", "")
            if not link or not title:
                continue

            articles.append(Article(
                title=title,
                description=summary,
                url=link,
                source=feed_cfg["name"],
                published=pub_time,
                language=feed_cfg.get("lang", "unknown"),
            ))

        return articles
    except Exception as e:
        print(f"[RSS/{feed_cfg['name']}] 请求异常: {e}")
        return []
