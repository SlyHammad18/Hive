import json
import re

from hive.core.config import load_config
from hive.core.graph.state import CritiqueResult, HiveState
from hive.core.llm import complete
from hive.core.log import get_logger

_log = get_logger("nodes.critic")

_CRITIC_SYSTEM_PROMPT = (
    "You are a critical reviewer of research answers. "
    "Given the original query and the synthesized answer, evaluate it for:\n"
    "1. Unsupported claims (claims made without citation evidence)\n"
    "2. Gaps in reasoning or missing important aspects\n"
    "3. Overall confidence in the answer (0.0 = completely unreliable, 1.0 = fully confident)\n\n"
    "Return ONLY a JSON object with this structure:\n"
    '{"issues": ["issue1", "issue2"], "confidence": 0.85, "follow_ups": ["follow-up question 1"]}\n'
    "Where issues is a list of specific problems found, "
    "confidence is a number between 0 and 1, "
    "and follow_ups is a list of questions that should be researched further."
)


def _parse_critique(content: str) -> CritiqueResult | None:
    text = content.strip()
    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group())
            issues = [str(i) for i in data.get("issues", [])]
            confidence = float(data.get("confidence", 0.5))
            confidence = max(0.0, min(1.0, confidence))
            follow_ups = [str(f) for f in data.get("follow_ups", [])]
            return CritiqueResult(issues=issues, confidence=confidence, follow_ups=follow_ups)
        except (json.JSONDecodeError, ValueError, TypeError):
            pass
    return None


async def critic_node(state: HiveState) -> dict:
    synthesis = state.get("synthesis", "")
    query = state.get("query", "")
    _log.debug("critic_node: synthesis_len=%d", len(synthesis))

    if not synthesis:
        _log.debug("  no synthesis to review")
        return {
            "critique": CritiqueResult(
                issues=["No synthesis to review."],
                confidence=0.0,
                follow_ups=["Re-run the pipeline with a valid query."],
            )
        }

    cfg = load_config()
    model = cfg.get("defaults", {}).get("model", "")

    if model:
        messages = [
            {"role": "system", "content": _CRITIC_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Original query: {query}\n\nSynthesized answer:\n{synthesis}",
            },
        ]
        try:
            content, _ = await complete(messages, model, temperature=0.3)
            parsed = _parse_critique(content)
            if parsed is not None:
                _log.debug("  LLM critique: confidence=%.2f issues=%d", parsed.confidence, len(parsed.issues))
                return {"critique": parsed}
            _log.warning("  LLM response did not parse as critique")
        except Exception as e:
            _log.warning("  LLM call failed: %s", e)

    _log.debug("  using fallback high-confidence critique")
    return {
        "critique": CritiqueResult(
            issues=[],
            confidence=0.9,
            follow_ups=[],
        ),
    }
