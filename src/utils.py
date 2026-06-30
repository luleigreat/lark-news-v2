"""通用工具函数"""

import re


def clean_html(text: str, max_len: int = 300) -> str:
    text = re.sub(r"<[^>]+>", "", text or "")
    text = re.sub(r"&[a-z]+;", " ", text)
    return text.strip()[:max_len]
