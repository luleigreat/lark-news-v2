"""日期过滤：昨天 / 上周"""

from datetime import date, datetime, timedelta, timezone

from src.config import CST
from src.models import Article
from src.sources.stats import DateFilterStats


def get_yesterday(now: datetime | None = None) -> date:
    return (now or datetime.now(CST)).date() - timedelta(days=1)


def get_last_week_range(now: datetime | None = None) -> tuple[date, date]:
    """返回昨天往前共 7 天（含昨天）。

    例：周一 6/30 推送 → 6/23（周一）~ 6/29（周日）
    与「昨日资讯」衔接，避免周二以后推送时整周偏移到更早的日历周。
    """
    end = get_yesterday(now)
    start = end - timedelta(days=6)
    return start, end


def filter_yesterday(
    articles: list[Article],
    now: datetime | None = None,
) -> tuple[list[Article], DateFilterStats]:
    target = get_yesterday(now)
    kept: list[Article] = []
    stats = DateFilterStats()

    for a in articles:
        pub = _pub_date(a)
        if pub is None:
            stats.dropped_no_date += 1
            continue
        if pub != target:
            stats.dropped_wrong_date += 1
            continue
        kept.append(a)
        _count_lang(a, stats)

    stats.kept = len(kept)
    return kept, stats


def filter_last_week(
    articles: list[Article],
    now: datetime | None = None,
) -> tuple[list[Article], DateFilterStats]:
    start, end = get_last_week_range(now)
    kept: list[Article] = []
    stats = DateFilterStats()

    for a in articles:
        pub = _pub_date(a)
        if pub is None:
            stats.dropped_no_date += 1
            continue
        if not (start <= pub <= end):
            stats.dropped_wrong_date += 1
            continue
        kept.append(a)
        _count_lang(a, stats)

    stats.kept = len(kept)
    return kept, stats


def _pub_date(article: Article) -> date | None:
    if not article.published:
        return None
    pub = article.published
    if pub.tzinfo is None:
        pub = pub.replace(tzinfo=timezone.utc)
    return pub.astimezone(CST).date()


def _count_lang(article: Article, stats: DateFilterStats):
    lang = (article.language or "").lower()
    if lang == "zh":
        stats.kept_zh += 1
    elif lang == "en":
        stats.kept_en += 1
    else:
        stats.kept_other += 1
