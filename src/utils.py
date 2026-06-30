"""通用工具函数"""

import re
from datetime import datetime, timezone
from typing import Any, Optional


def clean_html(text: str, max_len: int = 300) -> str:
    text = re.sub(r"<[^>]+>", "", text or "")
    text = re.sub(r"&[a-z]+;", " ", text)
    return text.strip()[:max_len]


def parse_feed_date(entry: Any) -> Optional[datetime]:
    """从 feedparser entry 解析发布时间，依次尝试 published/updated/created"""
    for attr in ("published_parsed", "updated_parsed", "created_parsed"):
        parsed = getattr(entry, attr, None)
        if parsed:
            return datetime(*parsed[:6], tzinfo=timezone.utc)
    return None
