"""Lark 交互式卡片构建与发送"""

import time

import requests

from src.config import CST, LARK_WEBHOOK_URL
from src.filters.date_filter import get_last_week_range, get_yesterday


def build_daily_card(ai_items: list[dict], web3_items: list[dict]) -> dict:
    news_date = get_yesterday().strftime("%Y-%m-%d")
    ai_content = _format_items_md("🤖 AI Agent Payment", ai_items)
    web3_content = _format_items_md("💳 Web3 卡 / U 卡", web3_items)

    return {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": f"AI & Web3 昨日资讯 | {news_date}"},
                "template": "blue",
            },
            "elements": [
                {"tag": "div", "text": {"tag": "lark_md", "content": ai_content}},
                {"tag": "hr"},
                {"tag": "div", "text": {"tag": "lark_md", "content": web3_content}},
                {
                    "tag": "note",
                    "elements": [{"tag": "plain_text", "content": "GoZo1.ai · 每日自动推送"}],
                },
            ],
        },
    }


def build_weekly_cards(
    ai_items: list[dict],
    web3_items: list[dict],
    ai_trend: str,
    web3_trend: str,
) -> list[dict]:
    start, end = get_last_week_range()
    date_range = f"{start.strftime('%m.%d')}-{end.strftime('%m.%d')}"
    empty_text = "📭 上周概况：未发现该方向的相关新闻"

    ai_content = _format_items_md("🤖 AI Agent Payment", ai_items, empty_text)
    ai_content += f"\n**📊 上周趋势**\n{ai_trend}"

    web3_content = _format_items_md("💳 Web3 卡 / U 卡", web3_items, empty_text)
    web3_content += f"\n**📊 上周趋势**\n{web3_trend}"

    return [
        {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": f"AI Agent Payment 周报 | {date_range}"},
                    "template": "turquoise",
                },
                "elements": [
                    {"tag": "div", "text": {"tag": "lark_md", "content": ai_content}},
                    {"tag": "note", "elements": [{"tag": "plain_text", "content": "GoZo1.ai · 每周简报"}]},
                ],
            },
        },
        {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": f"Web3 卡/U 卡 周报 | {date_range}"},
                    "template": "wathet",
                },
                "elements": [
                    {"tag": "div", "text": {"tag": "lark_md", "content": web3_content}},
                    {"tag": "note", "elements": [{"tag": "plain_text", "content": "GoZo1.ai · 每周简报"}]},
                ],
            },
        },
    ]


def _format_items_md(
    section_title: str,
    items: list[dict],
    empty_text: str = "📭 昨日概况：未发现该方向的相关新闻",
) -> str:
    lines = [f"**{section_title}**\n"]
    if not items:
        lines.append(empty_text)
    else:
        for i, item in enumerate(items, 1):
            title = item.get("title", "无标题")
            summary = item.get("summary", "")
            url = item.get("url", "")
            lines.append(f"{i}. **{title}**")
            tail = summary
            if url:
                tail = (f"{tail} " if tail else "") + f"[→原文]({url})"
            if tail:
                lines.append(tail)
            lines.append("")
    return "\n".join(lines)


def send_to_lark(card: dict) -> bool:
    if not LARK_WEBHOOK_URL:
        print("[Lark] 未配置 LARK_WEBHOOK_URL")
        return False

    try:
        resp = requests.post(
            LARK_WEBHOOK_URL,
            json=card,
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        data = resp.json()
        success = data.get("StatusCode") == 0 or data.get("code") == 0
        if success:
            print("[Lark] ✅ 发送成功")
        else:
            print(f"[Lark] ❌ 发送失败: {data}")
        return success
    except Exception as e:
        print(f"[Lark] ❌ 发送异常: {e}")
        return False


def send_multi_to_lark(cards: list[dict]) -> bool:
    all_ok = True
    for i, card in enumerate(cards, 1):
        if not send_to_lark(card):
            all_ok = False
        if i < len(cards):
            time.sleep(1.5)
    return all_ok
