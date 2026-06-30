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

# 用于搜索的企业查询词（消歧义，避免 Kast→康卡斯特/Comcast、Rain→降雨 等误命中）
FOCUS_COMPANY_QUERIES = [
    "Rain Card crypto",
    "MoonPay card",
    "DogPay crypto card",
    "RedotPay",
    "Alchemy Pay",
    "Kast Card stablecoin",
    "EtherFi Cash card",
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
] + FOCUS_COMPANY_QUERIES

# ── 垂直 RSS 源（仅搜索层之一，见下方说明）────────────────────
#
# 完整搜索架构（每个方向均会执行）：
#   1. Google News RSS — 按关键词检索，中英文各一遍（覆盖面最广）
#   2. NewsAPI         — 按关键词检索，中英文各一遍（需 API Key）
#   3. RSS_FEEDS       — 拉取垂直站点全量 feed，再用关键词本地过滤
#
# 因此 RSS_FEEDS 不是全部源，而是对 Google News 的补充，专攻行业垂直媒体。

RSS_FEEDS = [
    # 国际 Web3 / 加密
    {"name": "CoinDesk", "url": "https://www.coindesk.com/arc/outboundfeeds/rss/", "lang": "en"},
    {"name": "Cointelegraph", "url": "https://cointelegraph.com/rss", "lang": "en"},
    {"name": "Decrypt", "url": "https://decrypt.co/feed", "lang": "en"},
    {"name": "The Block", "url": "https://www.theblock.co/rss.xml", "lang": "en"},
    # 国际支付 / Fintech
    {"name": "PYMNTS", "url": "https://www.pymnts.com/feed/", "lang": "en"},
    {"name": "TechCrunch Fintech", "url": "https://techcrunch.com/category/fintech/feed/", "lang": "en"},
    # 国内 Web3
    {"name": "PANews", "url": "https://www.panewslab.com/zh/rss/index.xml", "lang": "zh"},
    {"name": "BlockBeats", "url": "https://api.theblockbeats.news/v2/rss/all", "lang": "zh"},
    {"name": "Odaily", "url": "https://www.odaily.news/rss", "lang": "zh"},
    {"name": "ChainCatcher", "url": "https://www.chaincatcher.com/rss/clist", "lang": "zh"},
    # 国内科技 / AI
    {"name": "36氪", "url": "https://36kr.com/feed", "lang": "zh"},
    {"name": "机器之心", "url": "https://www.jiqizhixin.com/rss", "lang": "zh"},
    {"name": "钛媒体", "url": "https://www.tmtpost.com/rss.xml", "lang": "zh"},
]

# RSS 关键词过滤（标题或摘要命中任一即保留）
RSS_KEYWORDS_AI = [
    "ai payment", "agent payment", "智能体支付", "ai agent", "ai 支付",
    "autonomous payment", "agent pay",
]
RSS_KEYWORDS_WEB3 = [
    "crypto card", "stablecoin card", "u卡", "加密卡", "支付卡",
    "debit card", "prepaid card", "rain card", "moonpay", "dogpay",
    "redotpay", "alchemy pay", "kast card", "etherfi", "bybit card",
    "wasabi card", "发卡",
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
