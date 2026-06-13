import webbrowser

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Button, Static

from hive.core.tools.citations import Citation


class CitationBadge(Button):
    def __init__(self, citation: Citation) -> None:
        self.citation = citation
        super().__init__(f"[{citation.index}]", id=f"cite-{citation.index}", variant="default")

    def on_click(self) -> None:
        webbrowser.open(self.citation.url)


class CitationsWidget(Horizontal):
    def __init__(self) -> None:
        super().__init__(id="citations-bar")
        self._visible = False

    def set_citations(self, citations: list[Citation]) -> None:
        self.remove_children()
        if citations:
            self._visible = True
            self.mount(*[CitationBadge(c) for c in citations])
            self.mount(Static("", classes="citations-spacer"))
        else:
            self._visible = False

    def clear(self) -> None:
        self.remove_children()
        self._visible = False
