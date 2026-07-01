"""搜索统计收集与日志输出"""

from dataclasses import dataclass, field

from src.models import Article

ZH_FEED_NAMES = {
    "PANews", "BlockBeats", "Odaily", "ChainCatcher", "36氪", "机器之心", "钛媒体",
}


@dataclass
class DateFilterStats:
    kept: int = 0
    dropped_no_date: int = 0
    dropped_wrong_date: int = 0
    kept_zh: int = 0
    kept_en: int = 0
    kept_other: int = 0


@dataclass
class SearchStats:
    direction: str = ""
    google_news_zh: int = 0
    google_news_en: int = 0
    newsapi_zh: int = 0
    newsapi_en: int = 0
    rss_by_feed: dict[str, int] = field(default_factory=dict)
    raw_total: int = 0
    after_dedup: int = 0
    date_filter: DateFilterStats = field(default_factory=DateFilterStats)

    @property
    def google_news_total(self) -> int:
        return self.google_news_zh + self.google_news_en

    @property
    def newsapi_total(self) -> int:
        return self.newsapi_zh + self.newsapi_en

    @property
    def rss_total(self) -> int:
        return sum(self.rss_by_feed.values())

    @property
    def raw_zh(self) -> int:
        return self.google_news_zh + self.newsapi_zh + sum(
            n for name, n in self.rss_by_feed.items() if name in ZH_FEED_NAMES
        )

    @property
    def raw_en(self) -> int:
        return self.google_news_en + self.newsapi_en + sum(
            n for name, n in self.rss_by_feed.items() if name not in ZH_FEED_NAMES
        )


def count_by_lang(articles: list[Article]) -> dict[str, int]:
    counts = {"zh": 0, "en": 0, "other": 0}
    for a in articles:
        lang = (a.language or "other").lower()
        if lang == "zh":
            counts["zh"] += 1
        elif lang == "en":
            counts["en"] += 1
        else:
            counts["other"] += 1
    return counts


def log_search_stats(stats: SearchStats, label: str = "搜索统计"):
    df = stats.date_filter
    print(f"\n{'─' * 50}")
    print(f"📊 {label} [{stats.direction}]")
    print(f"{'─' * 50}")
    print("  各渠道抓取（去重前）：")
    print(f"    Google News  中文 {stats.google_news_zh:>4}  |  英文 {stats.google_news_en:>4}  |  小计 {stats.google_news_total:>4}")
    print(f"    NewsAPI      中文 {stats.newsapi_zh:>4}  |  英文 {stats.newsapi_en:>4}  |  小计 {stats.newsapi_total:>4}")
    print(f"    RSS 垂直源   合计 {stats.rss_total:>4}")
    for name, count in sorted(stats.rss_by_feed.items(), key=lambda x: -x[1]):
        if count > 0:
            print(f"      - {name}: {count}")
    print(f"  原始合计: {stats.raw_total}  (国内≈{stats.raw_zh} / 国际≈{stats.raw_en})")
    print(f"  URL 去重后: {stats.after_dedup}")
    print("  日期过滤后:")
    print(f"    保留: {df.kept}  (国内 {df.kept_zh} / 国际 {df.kept_en} / 其他 {df.kept_other})")
    print(f"    丢弃-无发布日期: {df.dropped_no_date}")
    print(f"    丢弃-日期不符: {df.dropped_wrong_date}")
    if df.dropped_no_date > 0:
        print("  ⚠️  无发布日期被丢弃的条目较多，国内 RSS 源常见此问题")
    print(f"{'─' * 50}")


def log_ai_result(items: list[dict], raw: list[Article], label: str):
    raw_lang = count_by_lang(raw)
    print(f"\n  [AI 筛选] {label}")
    print(f"    输入: {len(raw)} 条 (国内 {raw_lang['zh']} / 国际 {raw_lang['en']})")
    print(f"    输出: {len(items)} 条")
    for i, item in enumerate(items, 1):
        title = item.get("title", "")[:40]
        url = item.get("url", "")
        region = _guess_region(url)
        print(f"      {i}. [{region}] {title}")

    selected_urls = {_normalize_url(item.get("url", "")) for item in items}
    dropped = [a for a in raw if _normalize_url(a.url) not in selected_urls]
    print(f"    被筛掉: {len(dropped)} 条")
    for i, a in enumerate(dropped, 1):
        region = _guess_region(a.url)
        title = (a.title or "")[:50]
        print(f"      ✗ {i}. [{region}] {title}")


def _normalize_url(url: str) -> str:
    url = (url or "").strip().rstrip("/")
    return url.split("?")[0].rstrip("/") if "?" in url else url


def _guess_region(url: str) -> str:
    zh_domains = (
        "panewslab", "theblockbeats", "odaily", "chaincatcher", "36kr",
        "jiqizhixin", "tmtpost", "jinse", "8btc", "foresight", ".cn",
    )
    url_lower = (url or "").lower()
    if any(d in url_lower for d in zh_domains):
        return "国内"
    return "国际"
