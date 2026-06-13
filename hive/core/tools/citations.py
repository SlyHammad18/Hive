from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Citation:
    index: int
    url: str
    title: str
    snippet: str
    agent: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class CitationTracker:
    def __init__(self) -> None:
        self._citations: list[Citation] = []

    def add(self, url: str, title: str, snippet: str, agent: str = "") -> int:
        index = len(self._citations) + 1
        citation = Citation(
            index=index,
            url=url,
            title=title,
            snippet=snippet[:300],
            agent=agent,
        )
        self._citations.append(citation)
        return index

    def get_all(self) -> list[Citation]:
        return list(self._citations)

    def format_references(self) -> str:
        lines: list[str] = []
        for c in self._citations:
            lines.append(f"[{c.index}] {c.title} — {c.url}")
        return "\n".join(lines)
