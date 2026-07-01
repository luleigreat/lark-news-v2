"""AI 筛选、翻译、摘要"""

import json
import re
from typing import Optional

from openai import OpenAI

from src.ai.client import chat_complete
from src.config import CST, FOCUS_COMPANIES, OPENAI_API_KEY
from src.filters.event_dedup import dedup_similar_items
from src.models import Article

DIRECTION_LABELS = {
    "ai_agent": "AI Agent 支付",
    "web3_card": "Web3 卡 / U 卡",
}

DAILY_CACHE_SOURCE = "每日推送"

_RELEVANCE_KEYWORDS = {
    "ai_agent": [
        "ai payment", "agent payment", "智能体支付", "agentic wallet", "agentic payment",
        "智能体钱包", "支付轨道", "扫码", "agent pay", "ai wallet", "ai 支付",
        "okx", "agentic", "stripe", "visa", "万事达", "支付宝", "微信", "tron",
    ],
    "web3_card": [
        "crypto card", "stablecoin card", "加密卡", "支付卡", "u卡", "发卡",
        "debit card", "prepaid card", "bingx card", "bingx", "rain card", "moonpay",
        "redotpay", "openpayd", "bybit card", "数字资产支付", "预付卡", "gtc", "gtech",
    ],
}


def filter_articles(
    articles: list[Article],
    direction: str,
    top_n: int,
    client: Optional[OpenAI] = None,
    mode: str = "daily",
) -> list[dict]:
    if not articles:
        return []

    if not OPENAI_API_KEY or client is None:
        print("[AI] 未配置 API Key，使用简单排序降级")
        return _basic_filter(articles, top_n)

    candidates = _build_candidates(articles)
    prompt = _build_prompt(direction, top_n, candidates, mode, len(articles))

    try:
        resp = chat_complete(
            client,
            messages=[{"role": "user", "content": prompt}],
            limit=8000,
        )
        content = (resp.choices[0].message.content or "").strip()
        result = _extract_json_array(content)
        if result is None:
            print("[AI] JSON 解析失败，降级使用简单排序")
            return _basic_filter(articles, top_n)

        result = _resolve_ai_items(result, articles)
        result = dedup_similar_items(result)
        if mode == "weekly":
            result = _backfill_from_cache(result, articles, top_n)
        else:
            result = _backfill_by_relevance(result, articles, direction, top_n)
        result = _ensure_chinese(result, client)
        result = _attach_dates(result, articles)
        return result[:top_n]
    except Exception as e:
        print(f"[AI] 筛选异常: {e}")
        return _basic_filter(articles, top_n)


def _build_candidates(articles: list[Article]) -> str:
    lines = []
    for i, a in enumerate(articles):
        tag = "★每日已推送" if a.source == DAILY_CACHE_SOURCE else "搜索补充"
        lines.append(
            f"[{i}] ({tag}) 标题: {a.title}\n"
            f"    来源: {a.source} ({a.language})\n"
            f"    描述: {a.description[:200]}\n"
            f"    链接: {a.url}",
        )
    return "\n\n".join(lines)


def _direction_rules(direction: str) -> str:
    focus = "、".join(FOCUS_COMPANIES)
    common_warn = """
【字符串误命中 — 必须剔除】
- 公司/关键词仅字符串巧合命中但实际无关的，一律丢弃。例如：
  Kast ≠ 康卡斯特/卡斯特/Comcast；Rain ≠ 普通降雨；Token ≠ 词元工厂/算力；
  "支付" 出现在租金缴费、水电缴费等与本方向无关的民生新闻里也要丢弃。"""

    if direction == "ai_agent":
        return f"""【AI Agent 支付 — 相关定义】
✅ 强相关：AI Agent / 智能体 + 支付/付款/结算/收单/Agentic Payment
✅ 强相关：Agentic Wallet / 智能体钱包（如 OKX Agentic Wallet、NeoSoul 接入智能体钱包）
✅ 强相关：Stripe、Visa、万事达、支付宝、微信、OpenAI 等推出的 Agent 支付或 AI 钱包能力
✅ 强相关：公链/平台推出的 AI 支付轨道、AI 支付基建（如 TRON 推动 AI 支付轨道）
✅ 中度相关（应纳入）：大厂 AI + 钱包/支付布局（腾讯/谷歌发 AI 邮箱钱包、支付宝/微信的 AI 扫码支付时刻）
❌ 丢弃：AI 炒股/交易活动/交易平台促销（无支付要素）
❌ 丢弃：AI 助手安全测试、黑客攻击、纯模型发布、编程工具、算力/Token 产量
❌ 丢弃：普通民生缴费（租金、水电）与 AI Agent 无关
❌ 丢弃：仅提 AI Agent 但完全无支付/钱包/结算场景{common_warn}"""

    return f"""【Web3 卡/U 卡 — 相关定义】
✅ 强相关：Crypto Card / 加密卡 / 借记卡 / 预付卡 / U卡 / 稳定币支付卡 / 发卡
✅ 强相关：{focus}、BingX Card 及同类发卡/支付卡企业的产品、牌照、合作
✅ 强相关：WasabiCard、Bybit Card、RedotPay+OpenPayd 等明确发卡/支付卡主体
✅ 中度相关（应纳入）：交易所/平台新推出 Crypto Card（如 BingX Card 全球数字资产支付）
✅ 中度相关（应纳入）：企业联合发行稳定币用于跨境支付/发卡基础设施（明确服务支付场景时）
❌ 丢弃：单纯稳定币发行、托管、储备、链上统计（如 TRON 账户数、USDT 溢价），且无卡/支付场景
❌ 丢弃：稳定币诉讼、交易所股权、证券入股、投资平台接入（如 Aladdin）
❌ 丢弃：稳定币宏观政策/央行计划，除非明确涉及支付卡产品
❌ 丢弃：稳定币交易/杠杆/做市平台，与发卡无关
❌ 丢弃：美股/存储股/财报等传统金融新闻（如康卡斯特 Comcast）{common_warn}"""


def _build_prompt(direction: str, top_n: int, candidate_text: str, mode: str, pool_size: int) -> str:
    direction_cn = DIRECTION_LABELS.get(direction, direction)
    direction_rules = _direction_rules(direction)

    if mode == "weekly":
        quantity_rule = f"""【周报数量要求】
- 候选池共约 {pool_size} 条，目标尽量凑满 {top_n} 条。
- 选取顺序：① 先选「★每日已推送」中符合强相关定义的；② 再从「搜索补充」中选强相关的；
  ③ 若仍不足 {top_n} 条，可纳入"中度相关"（主题确属本方向、但非头部事件）补足。
- 红线：无论如何都**不得纳入下方 ❌ 清单中的不相关内容**。宁可少于 {top_n} 条，也不要塞 ❌ 类内容。
- 禁止用「稳定币行业宏观/链上数据/交易所动态」冒充 Web3 卡新闻。"""
    else:
        quantity_rule = f"""【每日数量要求】
- 候选池共约 {pool_size} 条，目标尽量凑满 {top_n} 条。
- 选取顺序：① 强相关优先；② 强相关不足时纳入「中度相关」（主题明确属于本方向，如大厂 AI 钱包、AI 扫码支付、新发卡、支付基建）。
- 仅当候选池确实零相关时返回 []；不要因为过于保守而遗漏中度相关条目。
- 红线：仍须剔除下方 ❌ 清单中的不相关内容。"""

    return f"""你是一个行业资讯筛选专家。从候选中选出最多 {top_n} 条「{direction_cn}」新闻。

{quantity_rule}

{direction_rules}

【输出要求】
- 所有 title、summary **必须中文**；英文原标题须翻译（title 25字内，summary 80字内）。
- 同一事件只保留 1 条。

【排序优先级】
1. ★每日已推送 且强相关 > 2. 搜索补充且强相关
2. 头部企业 > 监管合规 > 产品发布 > 融资合作

输出严格 JSON 数组：
[
  {{"id": 候选编号, "title": "中文标题", "summary": "中文摘要", "url": "原文链接"}},
  ...
]

候选新闻：
{candidate_text}"""


def _relevance_score(article: Article, direction: str) -> float:
    text = f"{article.title} {article.description}".lower()
    return sum(1 for kw in _RELEVANCE_KEYWORDS.get(direction, []) if kw.lower() in text)


def _backfill_by_relevance(
    selected: list[dict],
    articles: list[Article],
    direction: str,
    top_n: int,
) -> list[dict]:
    """每日回填：从候选池中按主题关键词补足，避免盲目按时间排序"""
    if len(selected) >= top_n:
        return selected

    selected_urls = {_normalize_url(i.get("url", "")) for i in selected}
    remaining = [a for a in articles if _normalize_url(a.url) not in selected_urls]
    if not remaining:
        return selected

    scored = [(a, _relevance_score(a, direction)) for a in remaining]
    scored = [(a, s) for a, s in scored if s >= 1]
    scored.sort(
        key=lambda x: (
            x[1],
            x[0].published.timestamp() if x[0].published else 0,
        ),
        reverse=True,
    )

    need = top_n - len(selected)
    extras = [
        {
            "title": a.title[:50],
            "summary": (a.description or "")[:120],
            "url": a.url,
        }
        for a, _ in scored[:need]
    ]
    if extras:
        print(f"  [相关回填] AI 返回 {len(selected)} 条，按关键词补 {len(extras)} 条")
    return selected + extras


def _backfill_from_cache(selected: list[dict], articles: list[Article], top_n: int) -> list[dict]:
    """周报回填：仅从每日缓存（已中文化）补足，不用搜索原文"""
    if len(selected) >= top_n:
        return selected

    selected_urls = {_normalize_url(i.get("url", "")) for i in selected}
    cache_articles = [
        a for a in articles
        if a.source == DAILY_CACHE_SOURCE and _normalize_url(a.url) not in selected_urls
    ]
    if not cache_articles:
        return selected

    need = top_n - len(selected)
    extras = [
        {"title": a.title, "summary": a.description, "url": a.url}
        for a in cache_articles[:need]
    ]
    if extras:
        print(f"  [缓存回填] AI 返回 {len(selected)} 条，从每日缓存补 {len(extras)} 条")
    return selected + extras


def _ensure_chinese(items: list[dict], client: OpenAI) -> list[dict]:
    """检测未翻译条目，调用 AI 补译"""
    needs_translate = [i for i in items if _is_mostly_english(i.get("title", ""))]
    if not needs_translate:
        return items

    print(f"  [翻译] {len(needs_translate)} 条标题未中文化，正在补译...")
    for item in needs_translate:
        try:
            resp = chat_complete(
                client,
                messages=[{"role": "user", "content": (
                    f"将以下新闻标题和摘要翻译为中文（title 25字内，summary 80字内），"
                    f"输出 JSON：{{\"title\":\"\",\"summary\":\"\"}}\n"
                    f"title: {item.get('title', '')}\n"
                    f"summary: {item.get('summary', '')}"
                )}],
                limit=500,
            )
            content = (resp.choices[0].message.content or "").strip()
            parsed = json.loads(content[content.find("{"):content.rfind("}") + 1])
            item["title"] = parsed.get("title", item["title"])
            item["summary"] = parsed.get("summary", item.get("summary", ""))
        except Exception:
            pass
    return items


def _is_mostly_english(text: str) -> bool:
    if not text:
        return False
    ascii_chars = sum(1 for c in text if c.isascii() and c.isalpha())
    cjk_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    return ascii_chars > cjk_chars


def _resolve_ai_items(result: list[dict], articles: list[Article]) -> list[dict]:
    resolved = []
    for item in result:
        url = item.get("url", "")
        idx = item.get("id")
        if not url and idx is not None and 0 <= idx < len(articles):
            url = articles[idx].url
        if not url:
            continue
        resolved.append({
            "id": item.get("id", 0),
            "title": item.get("title", ""),
            "summary": item.get("summary", ""),
            "url": url,
        })
    return resolved


def _backfill_items(selected: list[dict], articles: list[Article], top_n: int) -> list[dict]:
    if len(selected) >= top_n:
        return selected

    selected_urls = {_normalize_url(i.get("url", "")) for i in selected}
    remaining = [a for a in articles if _normalize_url(a.url) not in selected_urls]
    if not remaining:
        return selected

    need = top_n - len(selected)
    extras = _basic_filter(remaining, need)
    if extras:
        print(f"  [AI 回填] AI 返回 {len(selected)} 条，从候选池补 {len(extras)} 条")
    return selected + extras


def _normalize_url(url: str) -> str:
    url = (url or "").strip().rstrip("/")
    return url.split("?")[0].rstrip("/") if "?" in url else url


def _attach_dates(items: list[dict], articles: list[Article]) -> list[dict]:
    """为每条结果附上发布日期（取自对应 Article）"""
    url_map = {_normalize_url(a.url): a for a in articles}
    for item in items:
        art = url_map.get(_normalize_url(item.get("url", "")))
        if art and art.published:
            item["date"] = art.published.astimezone(CST).date().isoformat()
    return items


def _basic_filter(articles: list[Article], top_n: int) -> list[dict]:
    def _pub_ts(a: Article) -> float:
        return a.published.timestamp() if a.published else 0

    sorted_articles = sorted(articles, key=_pub_ts, reverse=True)
    return [
        {
            "id": i,
            "title": a.title[:50],
            "summary": (a.description or "")[:120],
            "url": a.url,
        }
        for i, a in enumerate(sorted_articles[:top_n])
    ]


def _extract_json_array(content: str) -> Optional[list]:
    if not content:
        return None

    if "```" in content:
        for part in content.split("```"):
            p = part.lstrip()
            if p.startswith("json"):
                p = p[4:]
            if "[" in p and "]" in p:
                content = p
                break

    start = content.find("[")
    if start == -1:
        return None

    end = content.rfind("]")
    if end > start:
        try:
            return json.loads(content[start:end + 1])
        except json.JSONDecodeError:
            pass

    depth = 0
    in_str = False
    esc = False
    last_obj_end = -1
    for i in range(start, len(content)):
        c = content[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                last_obj_end = i

    if last_obj_end > start:
        try:
            return json.loads(content[start:last_obj_end + 1] + "]")
        except json.JSONDecodeError:
            return None
    return None
