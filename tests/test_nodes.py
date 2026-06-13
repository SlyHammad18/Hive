from hive.core.graph.state import BrowserResult, CritiqueResult, HiveState, TokenUsage
from hive.core.nodes.browser import browser_node
from hive.core.nodes.critic import critic_node
from hive.core.nodes.planner import planner_node, _generate_fallback_plan, _parse_plan
from hive.core.nodes.researcher import researcher_node
from hive.core.nodes.synthesizer import synthesizer_node


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
