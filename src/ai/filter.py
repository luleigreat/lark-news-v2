"""AI 筛选、翻译、摘要"""

import json
import re
from typing import Optional

from openai import OpenAI

from src.ai.client import chat_complete
from src.config import FOCUS_COMPANIES, OPENAI_API_KEY
from src.filters.event_dedup import dedup_similar_items
from src.models import Article

DIRECTION_LABELS = {
    "ai_agent": "AI Agent 支付",
    "web3_card": "Web3 卡 / U 卡",
}

DAILY_CACHE_SOURCE = "每日推送"


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
            result = _backfill_items(result, articles, top_n)
        result = _ensure_chinese(result, client)
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
    if direction == "ai_agent":
        return f"""【AI Agent 支付 — 强相关定义】
✅ 保留：AI Agent / 智能体 + 支付/付款/结算/钱包/收单/Agentic Payment/自主支付
✅ 保留：Stripe、Visa、万事达、支付宝、微信支付、OpenAI 等推出的 Agent 支付能力
❌ 丢弃：AI 炒股/交易活动/交易平台促销（无支付要素）
❌ 丢弃：AI 助手安全测试、黑客攻击、模型发布、编程工具
❌ 丢弃：仅提 AI Agent 但无支付/钱包/结算场景"""

    return f"""【Web3 卡/U 卡 — 强相关定义】
✅ 保留：Crypto Card / 加密卡 / 借记卡 / 预付卡 / U卡 / 稳定币支付卡 / 发卡
✅ 保留：{focus} 及同类发卡/支付卡企业的产品、牌照、合作
✅ 保留：WasabiCard、Bybit Card 等明确发卡主体的新闻
❌ 丢弃：单纯稳定币发行、托管、储备、链上统计（如 TRON 账户数、USDT 溢价）
❌ 丢弃：稳定币诉讼、交易所股权、证券入股、投资平台接入（如 Aladdin）
❌ 丢弃：稳定币宏观政策/央行计划，除非明确涉及支付卡产品
❌ 丢弃：稳定币交易/杠杆/做市平台，与发卡无关"""


def _build_prompt(direction: str, top_n: int, candidate_text: str, mode: str, pool_size: int) -> str:
    direction_cn = DIRECTION_LABELS.get(direction, direction)
    direction_rules = _direction_rules(direction)

    if mode == "weekly":
        quantity_rule = f"""【周报数量要求】
- 候选池共约 {pool_size} 条，目标最多 {top_n} 条。
- **优先从「★每日已推送」条目选取**（这些是每日已初审的优质内容），再视需要从「搜索补充」选取。
- **严格遵守下方强相关定义**，宁可不足 {top_n} 条，也绝不填入不相关新闻凑数。
- 禁止用「稳定币行业宏观/链上数据/交易所动态」冒充 Web3 卡新闻。"""
    else:
        quantity_rule = f"""【每日数量要求】
- 宁缺毋滥：强相关不足 {top_n} 条就只返回相关的；全不相关返回 []。"""

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
