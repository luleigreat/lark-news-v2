"""同一事件去重（标题/摘要语义相似）"""

import re
from difflib import SequenceMatcher

from src.models import Article

_TITLE_THRESHOLD = 0.42
_SUMMARY_THRESHOLD = 0.38
_COMBINED_THRESHOLD = 0.35

_STOPWORDS = frozenset(
    "的 了 与 和 在 是 为 以 及 等 将 已 被 对 从 到 一 笔 完成 宣布 落地".split()
)


def dedup_similar_articles(articles: list[Article]) -> list[Article]:
    """AI 筛选前：合并明显同一事件的候选报道"""
    kept: list[Article] = []

    for article in articles:
        dup_of = _find_duplicate(article.title, article.description, kept, _article_text)
        if dup_of is not None:
            if len(article.description) > len(dup_of.description):
                kept[kept.index(dup_of)] = article
        else:
            kept.append(article)

    return kept


def dedup_similar_items(items: list[dict]) -> list[dict]:
    """AI 筛选后：兜底合并同一事件"""
    kept: list[dict] = []

    for item in items:
        title = item.get("title", "")
        summary = item.get("summary", "")
        dup_of = _find_duplicate(title, summary, kept, _item_text)
        if dup_of is not None:
            if len(summary) > len(dup_of.get("summary", "")):
                kept[kept.index(dup_of)] = item
        else:
            kept.append(item)

    return kept


def _article_text(a: Article) -> tuple[str, str]:
    return a.title, a.description


def _item_text(d: dict) -> tuple[str, str]:
    return d.get("title", ""), d.get("summary", "")


def _find_duplicate(title: str, summary: str, kept: list, text_fn) -> object | None:
    for existing in kept:
        et, es = text_fn(existing)
        if _is_same_event(title, summary, et, es):
            return existing
    return None


def _is_same_event(t1: str, s1: str, t2: str, s2: str) -> bool:
    if not t1 or not t2:
        return False

    if _ratio(t1, t2) >= _TITLE_THRESHOLD:
        return True

    if s1 and s2 and _ratio(s1, s2) >= _SUMMARY_THRESHOLD:
        return True

    combined1 = f"{t1} {s1}"
    combined2 = f"{t2} {s2}"
    if _ratio(combined1, combined2) >= _COMBINED_THRESHOLD:
        return True

    kw1 = _keywords(combined1)
    kw2 = _keywords(combined2)
    if len(kw1 & kw2) >= 3:
        return True

    return False


def _ratio(a: str, b: str) -> float:
    a, b = a.lower().strip(), b.lower().strip()
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _keywords(text: str) -> set[str]:
    text = text.lower()
    tokens = set(re.findall(r"[\u4e00-\u9fff]{2,}|[a-z]{3,}", text))
    tokens -= _STOPWORDS
    chars = re.findall(r"[\u4e00-\u9fff]", text)
    for i in range(len(chars) - 1):
        tokens.add(chars[i] + chars[i + 1])
    return tokens
