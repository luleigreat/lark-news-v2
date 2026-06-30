"""主编排流程"""

from datetime import datetime
from typing import Optional

from openai import OpenAI

from src.ai.filter import filter_articles
from src.ai.trend import summarize_trend
from src.config import (
    AI_PAYMENT_QUERIES,
    CST,
    DAILY_SEARCH_DAYS,
    DAILY_TOP_N,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    WEB3_CARD_QUERIES,
    WEEKLY_SEARCH_DAYS,
    WEEKLY_TOP_N,
)
from src.filters.date_filter import filter_last_week, filter_yesterday
from src.lark.cards import build_daily_card, build_weekly_cards, send_multi_to_lark, send_to_lark
from src.sources.aggregator import search_direction


def _get_ai_client() -> Optional[OpenAI]:
    if not OPENAI_API_KEY:
        print("[AI] 未配置 OPENAI_API_KEY，将使用简单排序")
        return None
    return OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)


def _log_header(title: str):
    print(f"{'=' * 50}")
    print(f"{title}: {datetime.now(CST).strftime('%Y-%m-%d %H:%M')} CST")
    print(f"{'=' * 50}")


def run_daily() -> bool:
    _log_header("每日推送开始")
    client = _get_ai_client()

    print("\n[搜索] AI Agent Payment...")
    ai_raw = filter_yesterday(
        search_direction(AI_PAYMENT_QUERIES, "ai_agent", DAILY_SEARCH_DAYS)
    )
    print(f"  昨日结果: {len(ai_raw)} 条")

    print("\n[搜索] Web3 卡/U 卡...")
    web3_raw = filter_yesterday(
        search_direction(WEB3_CARD_QUERIES, "web3_card", DAILY_SEARCH_DAYS)
    )
    print(f"  昨日结果: {len(web3_raw)} 条")

    print(f"\n[筛选] AI Agent Payment top {DAILY_TOP_N}...")
    ai_items = filter_articles(ai_raw, "ai_agent", DAILY_TOP_N, client)
    print(f"  入选: {len(ai_items)} 条")

    print(f"\n[筛选] Web3 卡/U 卡 top {DAILY_TOP_N}...")
    web3_items = filter_articles(web3_raw, "web3_card", DAILY_TOP_N, client)
    print(f"  入选: {len(web3_items)} 条")

    print("\n[发送] 构建 Lark 卡片...")
    card = build_daily_card(ai_items, web3_items)
    success = send_to_lark(card)

    print(f"\n{'=' * 50}")
    print(f"每日推送{'成功' if success else '失败'}")
    return success


def run_weekly() -> bool:
    _log_header("周报推送开始")
    client = _get_ai_client()

    print("\n[搜索] AI Agent Payment...")
    ai_raw = filter_last_week(
        search_direction(AI_PAYMENT_QUERIES, "ai_agent", WEEKLY_SEARCH_DAYS)
    )
    print(f"  上周结果: {len(ai_raw)} 条")

    print("\n[搜索] Web3 卡/U 卡...")
    web3_raw = filter_last_week(
        search_direction(WEB3_CARD_QUERIES, "web3_card", WEEKLY_SEARCH_DAYS)
    )
    print(f"  上周结果: {len(web3_raw)} 条")

    print(f"\n[筛选] AI Agent Payment top {WEEKLY_TOP_N}...")
    ai_items = filter_articles(ai_raw, "ai_agent", WEEKLY_TOP_N, client)
    print(f"  入选: {len(ai_items)} 条")

    print(f"\n[筛选] Web3 卡/U 卡 top {WEEKLY_TOP_N}...")
    web3_items = filter_articles(web3_raw, "web3_card", WEEKLY_TOP_N, client)
    print(f"  入选: {len(web3_items)} 条")

    print("\n[AI] 趋势总结...")
    ai_trend = summarize_trend(ai_items, "ai_agent", client)
    web3_trend = summarize_trend(web3_items, "web3_card", client)

    print("\n[发送] 构建周报卡片...")
    cards = build_weekly_cards(ai_items, web3_items, ai_trend, web3_trend)
    success = send_multi_to_lark(cards)

    print(f"\n{'=' * 50}")
    print(f"周报推送{'成功' if success else '失败'}")
    return success
