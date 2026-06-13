import os
from dataclasses import dataclass

from ddgs import DDGS
from tavily import TavilyClient


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str


def search(query: str, n: int = 8, config: dict | None = None) -> list[SearchResult]:
    tavily_key = _get_tavily_key(config)
    if tavily_key:
        return _search_tavily(query, n, tavily_key)
    return _search_ddg(query, n)


def _get_tavily_key(config: dict | None) -> str | None:
    if config:
        key = config.get("search", {}).get("tavily_api_key", "")
        if key:
            return key
    return os.environ.get("TAVILY_API_KEY") or None


def _search_tavily(query: str, n: int, api_key: str) -> list[SearchResult]:
    client = TavilyClient(api_key=api_key)
    response = client.search(query=query, max_results=n)
    results: list[SearchResult] = []
    for r in response.get("results", []):
        results.append(
            SearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                snippet=r.get("content", ""),
            )
        )
    return results


def _search_ddg(query: str, n: int) -> list[SearchResult]:
    with DDGS() as ddgs:
        raw = list(ddgs.text(query, max_results=n))
    results: list[SearchResult] = []
    for r in raw:
        results.append(
            SearchResult(
                title=r.get("title", ""),
                url=r.get("href", ""),
                snippet=r.get("body", ""),
            )
        )
    return results
