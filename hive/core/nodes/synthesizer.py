import asyncio

from hive.core.config import load_config
from hive.core.graph.state import HiveState
from hive.core.llm import complete

_SYNTHESIZER_SYSTEM_PROMPT = (
    "You are a research synthesis writer. Given the following research notes "
    "with inline citations like [1], [2], etc., write a coherent, well-structured "
    "final answer that directly addresses the original query. "
    "Preserve all citation markers exactly as they appear. "
    "Organize the answer with clear sections and a summary."
)


def _fallback_synthesis(state: HiveState) -> str:
    notes = state.get("research_notes", "")
    if not notes:
        return "No research notes available to synthesize."
    return notes


def synthesizer_node(state: HiveState) -> dict:
    research_notes = state.get("research_notes", "")
    if not research_notes:
        return {"synthesis": "No research notes available to synthesize."}

    query = state.get("query", "")
    cfg = load_config()
    model = cfg.get("defaults", {}).get("model", "")

    if model:
        messages = [
            {"role": "system", "content": _SYNTHESIZER_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Original query: {query}\n\n"
                    f"Research notes:\n{research_notes}\n\n"
                    "Write a comprehensive, well-structured answer based on the above."
                ),
            },
        ]
        try:
            content, _ = asyncio.run(complete(messages, model, temperature=0.3))
        except Exception:
            content = _fallback_synthesis(state)
    else:
        content = _fallback_synthesis(state)

    return {"synthesis": content}
