"""日期过滤：昨天 / 上周"""

from datetime import date, datetime, timedelta, timezone

from src.config import CST
from src.models import Article


def get_yesterday(now: datetime | None = None) -> date:
    return (now or datetime.now(CST)).date() - timedelta(days=1)


def get_last_week_range(now: datetime | None = None) -> tuple[date, date]:
    """返回上周一至上周日（北京时间）"""
    today = (now or datetime.now(CST)).date()
    last_sunday = today - timedelta(days=today.weekday() + 1)
    last_monday = last_sunday - timedelta(days=6)
    return last_monday, last_sunday


def filter_yesterday(articles: list[Article], now: datetime | None = None) -> list[Article]:
    target = get_yesterday(now)
    return [a for a in articles if _pub_date(a) == target]


def filter_last_week(articles: list[Article], now: datetime | None = None) -> list[Article]:
    start, end = get_last_week_range(now)
    return [a for a in articles if start <= (_pub_date(a) or date.min) <= end]


def _pub_date(article: Article) -> date | None:
    if not article.published:
        return None
    pub = article.published
    if pub.tzinfo is None:
        pub = pub.replace(tzinfo=timezone.utc)
    return pub.astimezone(CST).date()
