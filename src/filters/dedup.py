"""URL 去重"""

from src.models import Article


def dedup_articles(articles: list[Article]) -> list[Article]:
    seen: set[str] = set()
    result: list[Article] = []

    for article in articles:
        url = _normalize_url(article.url)
        if not url or url in seen:
            continue
        seen.add(url)
        result.append(article)

    return result


def _normalize_url(url: str) -> str:
    url = (url or "").strip().rstrip("/")
    if "?" in url:
        return url.split("?")[0].rstrip("/")
    return url
