"""NewsAPI 搜索（中英文）"""

from datetime import datetime, timedelta

import requests

from src.config import NEWSAPI_KEY
from src.models import Article

_rate_limited = False
_rate_limit_logged = False


def is_rate_limited() -> bool:
    return _rate_limited


def search_lang(query: str, language: str, days_back: int) -> list[Article]:
    if not NEWSAPI_KEY or _rate_limited:
        return []

    from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    to_date = datetime.now().strftime("%Y-%m-%d")
    return _search_lang(query, language, from_date, to_date)


def search(query: str, days_back: int) -> list[Article]:
    if not NEWSAPI_KEY or _rate_limited:
        return []

    articles = []
    for lang in ("zh", "en"):
        if _rate_limited:
            break
        articles.extend(search_lang(query, lang, days_back))
    return articles


def _mark_rate_limited(message: str):
    global _rate_limited, _rate_limit_logged
    _rate_limited = True
    if not _rate_limit_logged:
        print(f"[NewsAPI] 已达请求限额，后续跳过: {message}")
        _rate_limit_logged = True


def _is_rate_limit_error(message: str, status_code: int) -> bool:
    msg = (message or "").lower()
    if status_code == 429:
        return True
    return any(k in msg for k in ("too many requests", "rate limit", "limited to", "quota"))


def _search_lang(query: str, language: str, from_date: str, to_date: str) -> list[Article]:
    global _rate_limited

    if _rate_limited:
        return []

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
            message = data.get("message", "unknown")
            if _is_rate_limit_error(message, resp.status_code):
                _mark_rate_limited(message)
            else:
                print(f"[NewsAPI/{language}] 错误: {message}")
            return []

        articles = []
        for a in data.get("articles", []):
            if not a.get("title") or not a.get("url"):
                continue

            pub_time = None
            if a.get("publishedAt"):
                try:
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
        if _is_rate_limit_error(str(e), 0):
            _mark_rate_limited(str(e))
        else:
            print(f"[NewsAPI/{language}] 请求异常: {e}")
        return []
