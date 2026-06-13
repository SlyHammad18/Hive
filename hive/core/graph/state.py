from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Annotated, TypedDict

from langgraph.graph import add_messages

from hive.core.tools.citations import Citation


@dataclass
class BrowserResult:
    sub_query: str
    url: str
    title: str
    snippet: str
    text: str = ""


@dataclass
class CritiqueResult:
    issues: list[str]
    confidence: float
    follow_ups: list[str]


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


def _reduce_browser_results(
    left: list[BrowserResult] | None, right: list[BrowserResult] | None
) -> list[BrowserResult]:
    if left is None and right is None:
        return []
    if left is None:
        return right or []
    if right is None:
        return left
    return left + right


class HiveState(TypedDict):
    query: str
    plan: list[str]
    browser_results: Annotated[list[BrowserResult], _reduce_browser_results]
    research_notes: str
    synthesis: str
    critique: CritiqueResult
    citations: list[Citation]
    token_usage: TokenUsage
    iteration: int
    messages: Annotated[list, add_messages]
