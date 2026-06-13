import asyncio

from hive.core.graph.state import BrowserResult, HiveState
from hive.core.tools.scraper import fetch_page
from hive.core.tools.search import search


async def _fetch_all(urls: list[str]) -> list[str]:
    tasks = [fetch_page(url) for url in urls]
    pages = await asyncio.gather(*tasks)
    return [page.text if page else "" for page in pages]


def browser_node(state: HiveState) -> dict:
    sub_query = state.get("sub_query", "")

    results = search(sub_query, n=3)
    urls = [r.url for r in results]

    texts: list[str] = []
    if urls:
        try:
            texts = asyncio.run(_fetch_all(urls))
        except Exception:
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
