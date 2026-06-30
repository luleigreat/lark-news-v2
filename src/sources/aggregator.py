"""多源搜索聚合"""

import time

from src.config import RSS_KEYWORDS_AI, RSS_KEYWORDS_WEB3
from src.filters.dedup import dedup_articles
from src.models import Article
from src.sources import google_news, newsapi, rss_feeds

DIRECTION_CONFIG = {
    "ai_agent": {
        "rss_keywords": RSS_KEYWORDS_AI,
    },
    "web3_card": {
        "rss_keywords": RSS_KEYWORDS_WEB3,
    },
}


def search_direction(queries: list[str], direction: str, days_back: int) -> list[Article]:
    """对某一方向执行多源搜索并去重"""
    all_articles: list[Article] = []
    rss_keywords = DIRECTION_CONFIG[direction]["rss_keywords"]

    for query in queries:
        all_articles.extend(google_news.search(query, days_back))
        time.sleep(0.2)
        all_articles.extend(newsapi.search(query, days_back))
        time.sleep(0.2)

    all_articles.extend(rss_feeds.search(rss_keywords, days_back))

    return dedup_articles(all_articles)
