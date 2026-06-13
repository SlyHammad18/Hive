from unittest.mock import AsyncMock, patch

from hive.core.graph.state import BrowserResult, CritiqueResult, HiveState, TokenUsage
from hive.core.nodes.browser import browser_node
from hive.core.nodes.critic import critic_node
from hive.core.nodes.planner import planner_node, _generate_fallback_plan, _parse_plan
from hive.core.nodes.researcher import researcher_node
from hive.core.nodes.synthesizer import synthesizer_node
from hive.core.tools.scraper import PageContent


def _make_state(**overrides: object) -> HiveState:
    base: HiveState = {
        "query": "test query",
        "plan": [],
        "browser_results": [],
        "research_notes": "",
        "synthesis": "",
        "critique": CritiqueResult(issues=[], confidence=0.0, follow_ups=[]),
        "citations": [],
        "token_usage": TokenUsage(),
        "iteration": 0,
        "messages": [],
    }
    base.update(overrides)  # type: ignore[typeddict-unknown-key]
    return base


def test_planner_node_fallback_when_no_model() -> None:
    state = _make_state(query="test query")
    result = planner_node(state)
    assert "plan" in result
    assert len(result["plan"]) >= 2
    assert result["plan"][0].startswith("Background")
    assert result["iteration"] == 1


def test_planner_node_increments_iteration() -> None:
    state = _make_state(query="test query", iteration=0)
    result = planner_node(state)
    assert result["iteration"] == 1


def test_generate_fallback_plan() -> None:
    plan = _generate_fallback_plan("AI safety")
    assert len(plan) == 3
    assert all("AI safety" in q for q in plan)


def test_parse_plan_valid_json() -> None:
    result = _parse_plan('["sub one", "sub two", "sub three"]')
    assert result == ["sub one", "sub two", "sub three"]


def test_parse_plan_too_few_items() -> None:
    result = _parse_plan('["only one"]')
    assert result is None


def test_parse_plan_invalid() -> None:
    assert _parse_plan("not json") is None
    assert _parse_plan("") is None


def test_browser_node_with_mocked_search() -> None:
    fake_results = [
        type("FakeResult", (), {"title": "Page A", "url": "https://a.com", "snippet": "snippet A"})(),
        type("FakeResult", (), {"title": "Page B", "url": "https://b.com", "snippet": "snippet B"})(),
    ]
    mock_fetch = AsyncMock(side_effect=[
        PageContent(title="Page A", url="https://a.com", text="text from A", word_count=3),
        PageContent(title="Page B", url="https://b.com", text="text from B", word_count=3),
    ])
    with patch("hive.core.nodes.browser.search", return_value=fake_results):
        with patch("hive.core.nodes.browser.fetch_page", mock_fetch):
            state: HiveState = _make_state()
            state["sub_query"] = "test sub query"  # type: ignore[typeddict-item]
            result = browser_node(state)
    assert "browser_results" in result
    assert len(result["browser_results"]) == 2
    br0 = result["browser_results"][0]
    assert br0.sub_query == "test sub query"
    assert br0.url == "https://a.com"
    assert br0.text == "text from A"
    br1 = result["browser_results"][1]
    assert br1.url == "https://b.com"
    assert br1.text == "text from B"


def test_browser_node_empty_search() -> None:
    with patch("hive.core.nodes.browser.search", return_value=[]):
        state: HiveState = _make_state()
        state["sub_query"] = "empty"  # type: ignore[typeddict-item]
        result = browser_node(state)
    assert len(result["browser_results"]) == 0


def test_browser_node_partial_fetch_failure() -> None:
    fake_results = [
        type("FakeResult", (), {"title": "Page A", "url": "https://a.com", "snippet": "snippet A"})(),
        type("FakeResult", (), {"title": "Page B", "url": "https://b.com", "snippet": "snippet B"})(),
    ]
    mock_fetch = AsyncMock(side_effect=[
        PageContent(title="Page A", url="https://a.com", text="text from A", word_count=3),
        None,
    ])
    with patch("hive.core.nodes.browser.search", return_value=fake_results):
        with patch("hive.core.nodes.browser.fetch_page", mock_fetch):
            state: HiveState = _make_state()
            state["sub_query"] = "test"  # type: ignore[typeddict-item]
            result = browser_node(state)
    assert result["browser_results"][0].text == "text from A"
    assert result["browser_results"][1].text == ""


def test_researcher_node_no_sources() -> None:
    state = _make_state()
    result = researcher_node(state)
    assert result["research_notes"] == "No source materials provided."
    assert result["citations"] == []


def test_researcher_node_with_sources() -> None:
    br = BrowserResult(sub_query="q", url="https://a.com", title="Page A", snippet="snippet A", text="Some interesting facts about AI.")
    state = _make_state(browser_results=[br])
    result = researcher_node(state)
    assert "research_notes" in result
    assert len(result["research_notes"]) > 0
    assert "citations" in result
    assert len(result["citations"]) == 1
    assert result["citations"][0].url == "https://a.com"
    assert result["citations"][0].agent == "Researcher"


def test_researcher_node_citations_are_indexed() -> None:
    brs = [
        BrowserResult(sub_query="q1", url="https://a.com", title="Page A", snippet="snippet A", text="Content A."),
        BrowserResult(sub_query="q2", url="https://b.com", title="Page B", snippet="snippet B", text="Content B."),
    ]
    state = _make_state(browser_results=brs)
    result = researcher_node(state)
    assert len(result["citations"]) == 2
    assert result["citations"][0].index == 1
    assert result["citations"][1].index == 2


def test_synthesizer_node() -> None:
    state = _make_state()
    result = synthesizer_node(state)
    assert "synthesis" in result
    assert result["synthesis"]


def test_critic_node() -> None:
    state = _make_state()
    result = critic_node(state)
    assert "critique" in result
    assert result["critique"].confidence == 0.9
