import webbrowser
from urllib.parse import urlparse

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Static

from hive.core.tools.citations import Citation


class CitationEntry(Static):
    def __init__(self, citation: Citation) -> None:
        self.citation = citation
        domain = urlparse(citation.url).netloc
        super().__init__(
            f"[bold #f59e0b][{citation.index}][/]  {citation.title}\n    [#64748b]{domain}[/]",
            id=f"cite-{citation.index}",
            classes="citation-entry"
        )

    def on_click(self) -> None:
        webbrowser.open(self.citation.url)


class CitationsWidget(VerticalScroll):
    def __init__(self) -> None:
        super().__init__(id="citations-panel")
        self._visible = False

    def compose(self) -> ComposeResult:
        yield Static("📎 SOURCES", classes="citation-title")

    def set_citations(self, citations: list[Citation]) -> None:
        self.remove_children()
        self.mount(Static("📎 SOURCES", classes="citation-title"))
        if citations:
            self._visible = True
            self.mount(*[CitationEntry(c) for c in citations])
        else:
            self._visible = False

    def clear(self) -> None:
        self.remove_children()
        self.mount(Static("📎 SOURCES", classes="citation-title"))
        self._visible = False
