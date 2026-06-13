from hive.core.graph.state import CritiqueResult, HiveState


def critic_node(state: HiveState) -> dict:
    return {
        "critique": CritiqueResult(
            issues=[],
            confidence=0.9,
            follow_ups=[],
        ),
    }
