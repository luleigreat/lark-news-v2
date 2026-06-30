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

    prompt = f"""根据以下上周 {direction_cn} 领域新闻标题，总结上周关键趋势。

输出格式要求（严格遵守，简洁易读）：
- 第一行：一句话核心趋势概述（30字以内），不要"上周""本周"前缀。
- 之后：2-3 条要点，每条以「1. 」「2. 」编号开头，单条不超过 40 字，提炼具体动向与代表案例。
- 不要输出多余说明、不要使用分号堆叠成长句。

标题列表：
{titles}"""

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
