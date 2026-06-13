from dataclasses import dataclass

import httpx
from lxml.html import fromstring
from readability import Document


@dataclass
class PageContent:
    title: str
    url: str
    text: str
    word_count: int


_TIMEOUT = httpx.Timeout(10.0)
_USER_AGENT = "Mozilla/5.0 (compatible; HiveResearch/1.0)"


async def fetch_page(url: str) -> PageContent | None:
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": _USER_AGENT})
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            if "text/html" not in content_type.lower():
                return None
            doc = Document(resp.text)
            title = doc.title() or ""
            summary_html = doc.summary()
            text = ""
            if summary_html:
                text = fromstring(summary_html).text_content().strip()
            word_count = len(text.split()) if text else 0
            return PageContent(title=title, url=url, text=text, word_count=word_count)
    except httpx.HTTPStatusError:
        return None
    except httpx.TimeoutException:
        return None
    except httpx.RequestError:
        return None
