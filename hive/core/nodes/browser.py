import asyncio

from hive.core.graph.state import BrowserResult, HiveState
from hive.core.log import get_logger
from hive.core.tools.scraper import fetch_page
from hive.core.tools.search import search

_log = get_logger("nodes.browser")


async def _fetch_all(urls: list[str]) -> list[str]:
    tasks = [fetch_page(url) for url in urls]
    pages = await asyncio.gather(*tasks)
    return [page.text if page else "" for page in pages]


async def browser_node(state: HiveState) -> dict:
    sub_query = state.get("sub_query", "")
    _log.debug("browser_node: sub_query=%r", sub_query[:60] if sub_query else "")

    results = search(sub_query, n=3)
    urls = [r.url for r in results]
    _log.debug("  search returned %d results", len(results))

    texts: list[str] = []
    if urls:
        try:
            texts = await _fetch_all(urls)
            _log.debug("  fetched %d pages", len([t for t in texts if t]))
        except asyncio.CancelledError:
            raise
        except Exception as e:
            _log.warning("  fetch failed: %s", e)
            texts = [""] * len(urls)

    browser_results: list[BrowserResult] = []
    for r, text in zip(results, texts):
        browser_results.append(
            BrowserResult(
                sub_query=sub_query,
                url=r.url,
                title=r.title,
                snippet=r.snippet,
                text=text,
            )
        )

    return {"browser_results": browser_results}
