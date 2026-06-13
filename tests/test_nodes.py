from hive.core.graph.state import BrowserResult, CritiqueResult, HiveState, TokenUsage
from hive.core.nodes.planner import planner_node
from hive.core.nodes.browser import browser_node
from hive.core.nodes.researcher import researcher_node
from hive.core.nodes.synthesizer import synthesizer_node
from hive.core.nodes.critic import critic_node


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


def test_planner_node() -> None:
    state = _make_state()
    result = planner_node(state)
    assert "plan" in result
    assert len(result["plan"]) == 2
    assert result["iteration"] == 0


def test_browser_node() -> None:
    state = _make_state()
    state["sub_query"] = "test sub query"  # type: ignore[typeddict-item]
    result = browser_node(state)
    assert "browser_results" in result
    assert len(result["browser_results"]) == 1
    br = result["browser_results"][0]
    assert isinstance(br, BrowserResult)
    assert br.sub_query == "test sub query"


def test_researcher_node() -> None:
    state = _make_state()
    result = researcher_node(state)
    assert "research_notes" in result
    assert result["research_notes"]


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
