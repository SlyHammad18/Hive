import pytest

from hive.core.tools.scraper import fetch_page


@pytest.mark.asyncio
async def test_fetch_known_page() -> None:
    result = await fetch_page("https://example.com")
    assert result is not None
    assert result.title == "Example Domain"
    assert "example" in result.text.lower()
    assert result.word_count > 0
    assert result.url == "https://example.com"


@pytest.mark.asyncio
async def test_fetch_nonexistent_page() -> None:
    result = await fetch_page("https://example.invalid/nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_fetch_non_html_url() -> None:
    result = await fetch_page("https://raw.githubusercontent.com/opencode-ai/opencode/refs/heads/main/LICENSE")
    assert result is None
