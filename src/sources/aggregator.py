"""多源搜索聚合"""

import time

from src.config import RSS_FEEDS, RSS_KEYWORDS_AI, RSS_KEYWORDS_WEB3
from src.filters.dedup import dedup_articles
from src.models import Article
from src.sources import google_news, newsapi, rss_feeds
from src.sources.stats import SearchStats
from src.sources.google_news import LOCALES

DIRECTION_CONFIG = {
    "ai_agent": {
        "rss_keywords": RSS_KEYWORDS_AI,
        "label": "AI Agent Payment",
    },
    "web3_card": {
        "rss_keywords": RSS_KEYWORDS_WEB3,
        "label": "Web3 卡/U 卡",
    },
}


def search_direction(
    queries: list[str],
    direction: str,
    days_back: int,
) -> tuple[list[Article], SearchStats]:
    """对某一方向执行多源搜索，返回文章列表与统计"""
    cfg = DIRECTION_CONFIG[direction]
    stats = SearchStats(direction=cfg["label"])
    all_articles: list[Article] = []
    rss_keywords = cfg["rss_keywords"]

    print(f"\n  关键词数: {len(queries)}, 搜索窗口: {days_back} 天")

    for i, query in enumerate(queries, 1):
        for locale in LOCALES:
            batch = google_news.search_locale(query, locale, days_back)
            if locale["lang"] == "zh":
                stats.google_news_zh += len(batch)
            else:
                stats.google_news_en += len(batch)
            all_articles.extend(batch)
        time.sleep(0.2)

        for lang in ("zh", "en"):
            batch = newsapi.search_lang(query, lang, days_back)
            if lang == "zh":
                stats.newsapi_zh += len(batch)
            else:
                stats.newsapi_en += len(batch)
            all_articles.extend(batch)
        time.sleep(0.2)

        if i % 4 == 0:
            print(f"    进度: {i}/{len(queries)} 关键词完成, 累计 {len(all_articles)} 条")

    for feed_cfg in RSS_FEEDS:
        batch = rss_feeds.search_feed(feed_cfg, rss_keywords, days_back)
        stats.rss_by_feed[feed_cfg["name"]] = len(batch)
        all_articles.extend(batch)

    stats.raw_total = len(all_articles)
    deduped = dedup_articles(all_articles)
    stats.after_dedup = len(deduped)
    return deduped, stats
