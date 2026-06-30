"""AI 筛选、翻译、摘要"""

import json
from typing import Optional

from openai import OpenAI

from src.ai.client import chat_complete
from src.config import FOCUS_COMPANIES, OPENAI_API_KEY
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
            f"    来源: {a.source}\n"
            f"    描述: {a.description[:200]}\n"
            f"    链接: {a.url}",
        )

    direction_cn = DIRECTION_LABELS.get(direction, direction)
    focus_companies = "、".join(FOCUS_COMPANIES)
    candidate_text = "\n\n".join(candidates)

    prompt = f"""你是一个行业资讯筛选专家。请从以下候选新闻中，选出最多 {top_n} 条与「{direction_cn}」**强相关**的重要新闻。

【硬性要求】
- 只保留主题紧扣「{direction_cn}」的新闻，必须涉及支付/付款/钱包/收单/结算/卡等支付要素。
- 丢弃泛泛的 AI 资讯、模型发布、编程工具、与支付无关的内容。
- 英文标题翻译为中文（25字内），摘要统一中文输出（80字内）。
- 宁缺毋滥：强相关不足 {top_n} 条就只返回相关的；全不相关返回 []。

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
        return result[:top_n]
    except Exception as e:
        print(f"[AI] 筛选异常: {e}")
        return _basic_filter(articles, top_n)


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
