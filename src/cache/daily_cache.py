"""每日推送结果本地缓存（供周报合并使用）"""

import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path

from src.config import CST
from src.models import Article

CACHE_DIR = Path(os.getenv("DAILY_CACHE_DIR", ".cache/daily"))


def _cache_path(news_date: date) -> Path:
    return CACHE_DIR / f"{news_date.isoformat()}.json"


def save_daily_cache(news_date: date, ai_items: list[dict], web3_items: list[dict]) -> Path:
    """保存某日推送结果"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "news_date": news_date.isoformat(),
        "saved_at": datetime.now(CST).isoformat(),
        "ai_items": ai_items,
        "web3_items": web3_items,
    }
    path = _cache_path(news_date)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[缓存] 已保存 {news_date} (AI {len(ai_items)} 条 / Web3 {len(web3_items)} 条) → {path}")
    return path


def load_daily_cache(news_date: date) -> dict | None:
    path = _cache_path(news_date)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"[缓存] 读取失败 {path}: {e}")
        return None


def load_week_items(start: date, end: date) -> tuple[list[dict], list[dict]]:
    """加载日期范围内所有每日缓存条目"""
    ai_items: list[dict] = []
    web3_items: list[dict] = []
    days_found = 0

    current = start
    while current <= end:
        data = load_daily_cache(current)
        if data:
            days_found += 1
            ai_items.extend(data.get("ai_items", []))
            web3_items.extend(data.get("web3_items", []))
        current += timedelta(days=1)

    print(
        f"[缓存] 加载 {start} ~ {end}: {days_found} 天有缓存, "
        f"AI {len(ai_items)} 条 / Web3 {len(web3_items)} 条"
    )
    return ai_items, web3_items


def items_to_articles(items: list[dict], news_date: date) -> list[Article]:
    """将每日推送条目转为 Article，参与周报合并"""
    pub = datetime(news_date.year, news_date.month, news_date.day, 12, 0, tzinfo=CST)
    articles = []
    for item in items:
        url = item.get("url", "")
        if not url:
            continue
        articles.append(Article(
            title=item.get("title", ""),
            description=item.get("summary", ""),
            url=url,
            source="每日推送",
            published=pub,
            language="zh",
        ))
    return articles


def load_week_articles(start: date, end: date) -> tuple[list[Article], list[Article]]:
    """加载周报日期范围内的缓存并转为 Article"""
    ai_items, web3_items = load_week_items(start, end)
    ai_articles: list[Article] = []
    web3_articles: list[Article] = []

    current = start
    while current <= end:
        data = load_daily_cache(current)
        if data:
            ai_articles.extend(items_to_articles(data.get("ai_items", []), current))
            web3_articles.extend(items_to_articles(data.get("web3_items", []), current))
        current += timedelta(days=1)

    return ai_articles, web3_articles


def purge_week_cache(start: date, end: date) -> int:
    """删除指定日期范围内的缓存文件"""
    removed = 0
    current = start
    while current <= end:
        path = _cache_path(current)
        if path.exists():
            path.unlink()
            removed += 1
            print(f"[缓存] 已删除 {current}")
        current += timedelta(days=1)
    if removed:
        print(f"[缓存] 共清理 {removed} 天")
    return removed


def list_cached_dates() -> list[date]:
    if not CACHE_DIR.exists():
        return []
    dates = []
    for path in CACHE_DIR.glob("*.json"):
        try:
            dates.append(date.fromisoformat(path.stem))
        except ValueError:
            continue
    return sorted(dates)
