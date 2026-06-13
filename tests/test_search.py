import os

import pytest

from hive.core.tools.search import search, SearchResult, _search_ddg


@pytest.fixture(autouse=True)
def clear_tavily_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)


def test_search_result_dataclass() -> None:
    r = SearchResult(title="t", url="u", snippet="s")
    assert r.title == "t"
    assert r.url == "u"
    assert r.snippet == "s"


def test_search_falls_back_to_ddg_when_no_key() -> None:
    results = search("test query", n=3)
    assert len(results) > 0
    assert all(isinstance(r, SearchResult) for r in results)
    assert all(r.title for r in results)
    assert all(r.url for r in results)


def test_search_ddg_directly() -> None:
    results = _search_ddg("python programming", n=3)
    assert len(results) > 0
    assert "python" in results[0].title.lower() or "python" in results[0].snippet.lower()


def test_search_returns_results_with_urls() -> None:
    results = search("example query", n=5)
    assert len(results) > 0
    assert all(r.url.startswith("http") for r in results if r.url)


@pytest.mark.skipif(not os.environ.get("TAVILY_API_KEY"), reason="TAVILY_API_KEY not set")
def test_search_uses_tavily_when_key_in_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", os.environ["TAVILY_API_KEY"])
    results = search("test", n=3)
    assert len(results) > 0


def test_search_uses_tavily_when_key_in_config() -> None:
    config = {"search": {"tavily_api_key": "test-key"}}
    from hive.core.tools import search as search_module

    original = search_module._search_tavily
    called = False

    def fake_tavily(query: str, n: int, api_key: str) -> list[SearchResult]:
        nonlocal called
        called = True
        assert api_key == "test-key"
        return [SearchResult(title="x", url="http://x.com", snippet="x")]

    search_module._search_tavily = fake_tavily
    try:
        results = search("test", config=config)
        assert called
        assert len(results) == 1
    finally:
        search_module._search_tavily = original
