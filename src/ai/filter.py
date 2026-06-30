"""AI 筛选、翻译、摘要"""

import json
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

    candidates = []
    for i, a in enumerate(articles):
        candidates.append(
            f"[{i}] 标题: {a.title}\n"
            f"    来源: {a.source} ({a.language})\n"
            f"    描述: {a.description[:200]}\n"
            f"    链接: {a.url}",
        )

    direction_cn = DIRECTION_LABELS.get(direction, direction)
    focus_companies = "、".join(FOCUS_COMPANIES)
    candidate_text = "\n\n".join(candidates)
    pool_size = len(articles)
    min_return = min(top_n, pool_size)

    if mode == "weekly":
        quantity_rule = f"""【周报数量要求 — 最高优先级】
- 候选池共 {pool_size} 条，目标输出 {top_n} 条。
- 候选 ≥ {top_n} 条时，**必须返回 {top_n} 条**，不得因「宁缺毋滥」只返回 3~5 条。
- 候选 {min_return}~{top_n} 条时，**必须返回全部 {min_return} 条**。
- 强相关优先；不足 {top_n} 条时用中度相关（仍须涉及支付/卡）补足名额。
- 只有候选池本身不足时，才可返回少于 {top_n} 条。"""
    else:
        quantity_rule = f"""【每日数量要求】
- 宁缺毋滥：强相关不足 {top_n} 条就只返回相关的；全不相关返回 []。"""

    prompt = f"""你是一个行业资讯筛选专家。请从以下候选新闻中，选出最多 {top_n} 条与「{direction_cn}」相关的重要新闻。

{quantity_rule}

【相关性要求】
- 主题须与「{direction_cn}」相关，涉及支付/付款/钱包/收单/结算/卡等支付要素。
- 丢弃泛泛的 AI 资讯、模型发布、编程工具、与支付无关的内容。
- 英文标题翻译为中文（25字内），摘要统一中文输出（80字内）。
- 候选中有国内来源（language=zh 或 .cn 域名）且相关时，应适当保留，避免结果全是国际媒体。

【同一事件去重 — 非常重要】
- 多条候选若报道**同一事件**（如同一笔交易落地、同一产品发布、同一政策），**只保留 1 条**。
- 合并时选信息最完整、来源最权威的一条，摘要可综合多条信息。
- **绝不要**在最终结果中出现两条描述同一事件的新闻。

【排序优先级】
1. 头部公司动态（Stripe, OpenAI, Visa, 支付宝, Coinbase 等）
   ★ 重点关注：{focus_companies}
2. 监管合规 > 3. 产品发布 > 4. 融资合作 > 5. 技术突破

输出严格 JSON 数组，不要其他内容：
[
  {{"id": 候选编号, "title": "中文标题", "summary": "中文摘要", "url": "原文链接"}},
  ...
]

候选新闻：
{candidate_text}"""

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
        result = _backfill_items(result, articles, top_n)
        return result[:top_n]
    except Exception as e:
        print(f"[AI] 筛选异常: {e}")
        return _basic_filter(articles, top_n)


def _resolve_ai_items(result: list[dict], articles: list[Article]) -> list[dict]:
    """将 AI 返回的 id 映射回原始 url，丢弃无效条目"""
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
    """AI 返回不足时，从候选池按时间倒序补足"""
    if len(selected) >= top_n:
        return selected

    selected_urls = {_normalize_url(i.get("url", "")) for i in selected}
    remaining = [
        a for a in articles
        if _normalize_url(a.url) not in selected_urls
    ]
    if not remaining:
        return selected

    need = top_n - len(selected)
    extras = _basic_filter(remaining, need)
    if extras and len(selected) < top_n:
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
