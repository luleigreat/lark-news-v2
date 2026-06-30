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
from src.filters.date_filter import filter_last_week, filter_yesterday, get_yesterday
from src.lark.cards import build_daily_card, build_weekly_cards, send_multi_to_lark, send_to_lark
from src.sources.aggregator import search_direction
from src.sources.stats import log_ai_result, log_search_stats


def _get_ai_client() -> Optional[OpenAI]:
    if not OPENAI_API_KEY:
        print("[AI] 未配置 OPENAI_API_KEY，将使用简单排序")
        return None
    return OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)


def _log_header(title: str):
    print(f"{'=' * 50}")
    print(f"{title}: {datetime.now(CST).strftime('%Y-%m-%d %H:%M')} CST")
    print(f"{'=' * 50}")


def _search_and_filter(queries, direction, days_back, date_mode: str):
    """搜索 + 日期过滤，输出详细统计"""
    raw, stats = search_direction(queries, direction, days_back)

    if date_mode == "yesterday":
        filtered, df_stats = filter_yesterday(raw)
        target_label = f"昨日 ({get_yesterday()})"
    else:
        filtered, df_stats = filter_last_week(raw)
        target_label = "上周"

    stats.date_filter = df_stats
    log_search_stats(stats, label=f"{target_label} 搜索统计")
    return filtered, stats


def run_daily() -> bool:
    _log_header("每日推送开始")
    client = _get_ai_client()

    print("\n[1/2] AI Agent Payment")
    ai_raw, _ = _search_and_filter(AI_PAYMENT_QUERIES, "ai_agent", DAILY_SEARCH_DAYS, "yesterday")

    print("\n[2/2] Web3 卡/U 卡")
    web3_raw, _ = _search_and_filter(WEB3_CARD_QUERIES, "web3_card", DAILY_SEARCH_DAYS, "yesterday")

    print(f"\n[筛选] AI Agent Payment top {DAILY_TOP_N}...")
    ai_items = filter_articles(ai_raw, "ai_agent", DAILY_TOP_N, client)
    log_ai_result(ai_items, ai_raw, "AI Agent Payment")

    print(f"\n[筛选] Web3 卡/U 卡 top {DAILY_TOP_N}...")
    web3_items = filter_articles(web3_raw, "web3_card", DAILY_TOP_N, client)
    log_ai_result(web3_items, web3_raw, "Web3 卡/U 卡")

    print("\n[发送] 构建 Lark 卡片...")
    card = build_daily_card(ai_items, web3_items)
    success = send_to_lark(card)

    print(f"\n{'=' * 50}")
    print(f"每日推送{'成功' if success else '失败'}")
    return success


def run_weekly() -> bool:
    _log_header("周报推送开始")
    client = _get_ai_client()

    print("\n[1/2] AI Agent Payment")
    ai_raw, _ = _search_and_filter(AI_PAYMENT_QUERIES, "ai_agent", WEEKLY_SEARCH_DAYS, "last_week")

    print("\n[2/2] Web3 卡/U 卡")
    web3_raw, _ = _search_and_filter(WEB3_CARD_QUERIES, "web3_card", WEEKLY_SEARCH_DAYS, "last_week")

    print(f"\n[筛选] AI Agent Payment top {WEEKLY_TOP_N}...")
    ai_items = filter_articles(ai_raw, "ai_agent", WEEKLY_TOP_N, client)
    log_ai_result(ai_items, ai_raw, "AI Agent Payment")

    print(f"\n[筛选] Web3 卡/U 卡 top {WEEKLY_TOP_N}...")
    web3_items = filter_articles(web3_raw, "web3_card", WEEKLY_TOP_N, client)
    log_ai_result(web3_items, web3_raw, "Web3 卡/U 卡")

    print("\n[AI] 趋势总结...")
    ai_trend = summarize_trend(ai_items, "ai_agent", client)
    web3_trend = summarize_trend(web3_items, "web3_card", client)

    print("\n[发送] 构建周报卡片...")
    cards = build_weekly_cards(ai_items, web3_items, ai_trend, web3_trend)
    success = send_multi_to_lark(cards)

    print(f"\n{'=' * 50}")
    print(f"周报推送{'成功' if success else '失败'}")
    return success
