import json

from hive.core.config import load_config
from hive.core.graph.state import HiveState
from hive.core.llm import complete
from hive.core.log import get_logger

_log = get_logger("nodes.planner")


_PLANNER_SYSTEM_PROMPT = (
    "You are a research planning assistant. "
    "Break down the user's query into 2–4 focused sub-queries that can be researched independently. "
    "Return ONLY a JSON array of strings, e.g. [\"sub-query one\", \"sub-query two\"]."
)


def _generate_fallback_plan(query: str) -> list[str]:
    return [
        f"Background and context for: {query}",
        f"Key arguments and evidence for: {query}",
        f"Recent developments and trends in: {query}",
    ]


def _parse_plan(content: str) -> list[str] | None:
    text = content.strip()
    if text.startswith("["):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list) and len(parsed) >= 2:
                return [str(item) for item in parsed if str(item).strip()][:4]
        except json.JSONDecodeError:
            pass
    return None


async def planner_node(state: HiveState) -> dict:
    cfg = load_config()
    defaults = cfg.get("defaults", {})
    model: str = defaults.get("model", "") or ""
    query = state.get("query", "")
    iteration: int = state.get("iteration", 0)

    _log.debug("planner_node: model=%r query=%r iteration=%d", model, query[:50] if query else "", iteration)

    plan: list[str] = []

    if model and query:
        messages = [
            {"role": "system", "content": _PLANNER_SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ]
        try:
            content, _ = await complete(messages, model, temperature=0.7)
            parsed = _parse_plan(content)
            if parsed is not None:
                plan = parsed
                _log.debug("  LLM plan: %s", plan)
            else:
                _log.warning("  LLM response did not parse as valid plan")
        except Exception as e:
            _log.warning("  LLM call failed: %s", e)

    if not plan:
        _log.debug("  using fallback plan")
        plan = _generate_fallback_plan(query)

    return {"plan": plan, "iteration": iteration + 1}
