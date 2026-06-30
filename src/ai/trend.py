"""AI 周报趋势总结"""

from typing import Optional

from openai import OpenAI

from src.ai.client import chat_complete
from src.config import OPENAI_API_KEY
from src.ai.filter import DIRECTION_LABELS


def summarize_trend(
    items: list[dict],
    direction: str,
    client: Optional[OpenAI] = None,
) -> str:
    direction_cn = DIRECTION_LABELS.get(direction, direction)

    if not items or not OPENAI_API_KEY or client is None:
        return f"上周{direction_cn}领域共收录 {len(items)} 条相关资讯。"

    titles = "\n".join(f"- {item.get('title', '')}" for item in items[:20])

    prompt = f"""根据以下上周 {direction_cn} 领域新闻标题，用 1-2 句话总结上周关键趋势：

{titles}

直接输出总结，不要前缀。"""

    try:
        resp = chat_complete(
            client,
            messages=[{"role": "user", "content": prompt}],
            limit=1000,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        print(f"[AI] 趋势总结异常: {e}")
        return f"上周{direction_cn}领域共收录 {len(items)} 条相关资讯。"
