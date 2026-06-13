from hive.core.tools.citations import Citation, CitationTracker


def test_add_returns_incremental_index() -> None:
    tracker = CitationTracker()
    assert tracker.add("http://a.com", "A", "snippet a") == 1
    assert tracker.add("http://b.com", "B", "snippet b") == 2
    assert tracker.add("http://c.com", "C", "snippet c") == 3


def test_get_all_returns_all_citations() -> None:
    tracker = CitationTracker()
    tracker.add("http://a.com", "A", "snippet a")
    tracker.add("http://b.com", "B", "snippet b")
    all_c = tracker.get_all()
    assert len(all_c) == 2
    assert all_c[0].index == 1
    assert all_c[1].index == 2


def test_get_all_returns_copy() -> None:
    tracker = CitationTracker()
    tracker.add("http://a.com", "A", "snippet a")
    tracker.get_all().append(Citation(index=999, url="", title="", snippet=""))
    assert len(tracker.get_all()) == 1


def test_format_references() -> None:
    tracker = CitationTracker()
    tracker.add("http://a.com", "Title A", "snippet")
    tracker.add("http://b.org", "Title B", "snippet")
    expected = "[1] Title A — http://a.com\n[2] Title B — http://b.org"
    assert tracker.format_references() == expected


def test_snippet_truncated_to_300_chars() -> None:
    tracker = CitationTracker()
    long_snippet = "x" * 500
    tracker.add("http://a.com", "A", long_snippet)
    assert len(tracker.get_all()[0].snippet) == 300


def test_citation_dataclass_defaults() -> None:
    from datetime import datetime
    c = Citation(index=1, url="http://a.com", title="T", snippet="S")
    assert c.agent == ""
    assert isinstance(c.timestamp, datetime)


def test_add_with_agent() -> None:
    tracker = CitationTracker()
    tracker.add("http://a.com", "A", "snippet", agent="Researcher")
    assert tracker.get_all()[0].agent == "Researcher"
