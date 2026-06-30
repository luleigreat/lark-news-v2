"""NewsAPI 搜索（中英文）"""

from datetime import datetime, timedelta

import requests

from src.config import NEWSAPI_KEY
from src.models import Article


def search(query: str, days_back: int) -> list[Article]:
    if not NEWSAPI_KEY:
        return []

    from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    to_date = datetime.now().strftime("%Y-%m-%d")
    articles = []

    for lang in ("zh", "en"):
        articles.extend(_search_lang(query, lang, from_date, to_date))

    return articles


def _search_lang(query: str, language: str, from_date: str, to_date: str) -> list[Article]:
    try:
        resp = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": query,
                "from": from_date,
                "to": to_date,
                "language": language,
                "sortBy": "relevancy",
                "pageSize": 15,
                "apiKey": NEWSAPI_KEY,
            },
            timeout=10,
        )
        data = resp.json()
        if data.get("status") != "ok":
            print(f"[NewsAPI/{language}] 错误: {data.get('message', 'unknown')}")
            return []

        articles = []
        for a in data.get("articles", []):
            if not a.get("title") or not a.get("url"):
                continue

            pub_time = None
            if a.get("publishedAt"):
                try:
                    from datetime import timezone
                    pub_time = datetime.fromisoformat(a["publishedAt"].replace("Z", "+00:00"))
                except ValueError:
                    pass

            articles.append(Article(
                title=a.get("title", ""),
                description=a.get("description", "") or "",
                url=a.get("url", ""),
                source=a.get("source", {}).get("name", "NewsAPI"),
                published=pub_time,
                language=language,
            ))

        return articles
    except Exception as e:
        print(f"[NewsAPI/{language}] 请求异常: {e}")
        return []
