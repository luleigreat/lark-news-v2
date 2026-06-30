"""数据模型"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Article:
    title: str
    url: str
    description: str = ""
    source: str = ""
    published: Optional[datetime] = None
    language: str = "unknown"

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "description": self.description,
            "url": self.url,
            "source": self.source,
            "published": self.published.isoformat() if self.published else "",
            "language": self.language,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Article":
        pub = data.get("published", "")
        published = None
        if pub:
            try:
                from datetime import timezone
                published = datetime.fromisoformat(str(pub).replace("Z", "+00:00"))
                if published.tzinfo is None:
                    published = published.replace(tzinfo=timezone.utc)
            except ValueError:
                pass
        return cls(
            title=data.get("title", ""),
            url=data.get("url", ""),
            description=data.get("description", ""),
            source=data.get("source", ""),
            published=published,
            language=data.get("language", "unknown"),
        )


@dataclass
class NewsItem:
    """AI 筛选后的输出条目"""
    title: str
    summary: str
    url: str
    id: int = 0

    def to_dict(self) -> dict:
        return {"id": self.id, "title": self.title, "summary": self.summary, "url": self.url}
