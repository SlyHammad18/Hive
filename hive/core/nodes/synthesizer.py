from hive.core.config import load_config
from hive.core.graph.state import HiveState
from hive.core.llm import complete
from hive.core.log import get_logger

_log = get_logger("nodes.synthesizer")

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


async def synthesizer_node(state: HiveState) -> dict:
    research_notes = state.get("research_notes", "")
    if not research_notes:
        _log.debug("synthesizer_node: no research notes")
        return {"synthesis": "No research notes available to synthesize."}

    query = state.get("query", "")
    cfg = load_config()
    model = cfg.get("defaults", {}).get("model", "")
    _log.debug("synthesizer_node: notes_len=%d model=%r", len(research_notes), model)

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
            content, _ = await complete(messages, model, temperature=0.3)
            _log.debug("  LLM synthesis OK (%d chars)", len(content))
        except Exception as e:
            _log.warning("  LLM call failed: %s, using fallback", e)
            content = _fallback_synthesis(state)
    else:
        _log.debug("  no model configured, using fallback synthesis")
        content = _fallback_synthesis(state)

    return {"synthesis": content}
