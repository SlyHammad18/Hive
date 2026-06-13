import asyncio

from hive.core.config import load_config
from hive.core.graph.state import HiveState
from hive.core.llm import complete
from hive.core.tools.citations import CitationTracker

_RESEARCHER_SYSTEM_PROMPT = (
    "You are a research analyst. Given the following source materials, "
    "extract key facts, quotes, and data points. "
    "Cite each claim with the source's bracketed number like [1], [2], etc. "
    "Format your response as well-structured Markdown notes."
)


def _build_source_blocks(state: HiveState) -> tuple[CitationTracker, str]:
    tracker = CitationTracker()
    blocks: list[str] = []
    for br in state.get("browser_results", []):
        idx = tracker.add(url=br.url, title=br.title, snippet=br.snippet[:200], agent="Researcher")
        text = (br.text or "")[:2000]
        blocks.append(
            f"[Source {idx}] {br.title}\n"
            f"URL: {br.url}\n"
            f"Content:\n{text}"
        )
    return tracker, "\n\n---\n\n".join(blocks)


def _fallback_notes(state: HiveState) -> str:
    lines: list[str] = []
    for br in state.get("browser_results", []):
        text = (br.text or "")[:500]
        lines.append(f"## {br.title}\n\n{text}")
    return "\n\n".join(lines) if lines else "No source materials provided."


def researcher_node(state: HiveState) -> dict:
    browser_results = state.get("browser_results", [])
    if not browser_results:
        return {"research_notes": "No source materials provided.", "citations": []}

    tracker, source_text = _build_source_blocks(state)
    cfg = load_config()
    model = cfg.get("defaults", {}).get("model", "")

    if model:
        messages = [
            {"role": "system", "content": _RESEARCHER_SYSTEM_PROMPT},
            {"role": "user", "content": f"Analyze the following source materials and extract key findings:\n\n{source_text}"},
        ]
        try:
            content, _ = asyncio.run(complete(messages, model, temperature=0.3))
        except Exception:
            content = _fallback_notes(state)
    else:
        content = _fallback_notes(state)

    return {"research_notes": content, "citations": tracker.get_all()}
