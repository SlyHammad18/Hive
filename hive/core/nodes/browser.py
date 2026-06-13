from hive.core.graph.state import BrowserResult, HiveState


def browser_node(state: HiveState) -> dict:
    sub_query = state.get("sub_query", "")
    return {
        "browser_results": [
            BrowserResult(
                sub_query=sub_query,
                url="https://example.com",
                title="Example",
                snippet="example snippet",
            )
        ],
    }
