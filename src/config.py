"""项目配置：关键词、数据源、环境变量"""

import os
from datetime import timedelta, timezone

CST = timezone(timedelta(hours=8))

# ── 搜索关键词 ──────────────────────────────────────────────

FOCUS_COMPANIES = [
    "Rain Card",
    "MoonPay",
    "DogPay",
    "RedotPay",
    "Alchemy Pay",
    "Kast",
    "EtherFi",
    "Bybit Card",
]

AI_PAYMENT_QUERIES = [
    "AI Payment",
    "Agent Payment",
    "AI agent payment protocol",
    "autonomous agent payment",
    "AI智能体支付",
    "AI Agent 支付",
    "智能体支付",
    "支付宝 AI 支付",
    "微信支付 AI",
    "Stripe AI agent",
    "OpenAI payment",
    "Visa AI payment",
]

WEB3_CARD_QUERIES = [
    "Crypto Card",
    "Stablecoin Card",
    "crypto debit card",
    "加密货币卡",
    "稳定币卡",
    "U卡",
    "加密支付卡",
    "稳定币 支付卡",
    "Web3 支付卡",
] + FOCUS_COMPANIES

# ── 垂直 RSS 源 ─────────────────────────────────────────────

RSS_FEEDS = [
    {"name": "CoinDesk", "url": "https://www.coindesk.com/arc/outboundfeeds/rss/", "lang": "en"},
    {"name": "PANews", "url": "https://www.panewslab.com/zh/rss/index.xml", "lang": "zh"},
    {"name": "BlockBeats", "url": "https://api.theblockbeats.news/v2/rss/all", "lang": "zh"},
    {"name": "36氪", "url": "https://36kr.com/feed", "lang": "zh"},
]

# RSS 关键词过滤（标题或摘要命中任一即保留）
RSS_KEYWORDS_AI = [
    "ai payment", "agent payment", "智能体支付", "ai agent", "ai 支付",
    "autonomous payment", "agent pay",
]
RSS_KEYWORDS_WEB3 = [
    "crypto card", "stablecoin card", "u卡", "加密卡", "支付卡",
    "debit card", "rain card", "moonpay", "dogpay", "redotpay",
    "alchemy pay", "kast", "etherfi", "bybit card", "稳定币",
]

# ── 环境变量 ──────────────────────────────────────────────────

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")
LARK_WEBHOOK_URL = os.getenv("LARK_WEBHOOK_URL", "")

# ── 任务参数 ──────────────────────────────────────────────────

DAILY_TOP_N = 5
WEEKLY_TOP_N = 10
DAILY_SEARCH_DAYS = 2
WEEKLY_SEARCH_DAYS = 10
