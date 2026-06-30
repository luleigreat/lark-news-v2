"""OpenAI 兼容 API 封装（兼容 max_tokens / max_completion_tokens）"""

import os
from typing import Any

from openai import OpenAI

from src.config import OPENAI_BASE_URL, OPENAI_MODEL


def _use_max_completion_tokens() -> bool:
    flag = os.getenv("OPENAI_USE_MAX_COMPLETION_TOKENS", "").lower()
    if flag in ("1", "true", "yes"):
        return True
    if flag in ("0", "false", "no"):
        return False

    model = OPENAI_MODEL.lower()
    base = OPENAI_BASE_URL.lower()
    hints = ("gpt-5", "o1", "o3", "o4", "chatgpt", "azure", "openai.azure.com")
    return any(h in model or h in base for h in hints)


def token_limit_kwargs(limit: int) -> dict[str, int]:
    if _use_max_completion_tokens():
        return {"max_completion_tokens": limit}
    return {"max_tokens": limit}


def chat_complete(client: OpenAI, messages: list[dict[str, str]], limit: int) -> Any:
    """调用 chat completions，自动适配不同平台的 token 参数名"""
    primary = token_limit_kwargs(limit)
    kwargs = {"model": OPENAI_MODEL, "messages": messages, **primary}

    try:
        return client.chat.completions.create(**kwargs)
    except Exception as e:
        err = str(e).lower()
        if "max_tokens" in err and "max_completion_tokens" in err and "max_tokens" in primary:
            fallback = {"max_completion_tokens": limit}
        elif "max_completion_tokens" in err and "max_tokens" in err and "max_completion_tokens" in primary:
            fallback = {"max_tokens": limit}
        else:
            raise

        kwargs = {"model": OPENAI_MODEL, "messages": messages, **fallback}
        return client.chat.completions.create(**kwargs)
