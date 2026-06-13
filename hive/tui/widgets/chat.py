from textual.strip import Strip
from textual.widgets import RichLog
from rich.markdown import Markdown
from rich.text import Text


class ChatWidget(RichLog):
    def __init__(self) -> None:
        super().__init__(highlight=True, markup=True, wrap=True, min_width=40)
        self._stream_buffer = ""
        self._stream_role = ""

    def add_message(self, role: str, content: str) -> None:
        label = {"user": "You", "assistant": "Assistant", "agent": "Agent"}.get(role, role)
        header = Text(f"\n{label}\n", style="bold underline")
        body = Markdown(content) if content else Text("")
        self.write(header)
        self.write(body)
        self._scroll_to_end()

    def start_stream(self, role: str) -> None:
        self._stream_role = role
        self._stream_buffer = ""
        label = {"user": "You", "assistant": "Assistant", "agent": "Agent"}.get(role, role)
        self.write(Text(f"\n{label}\n", style="bold underline"))

    def append_token(self, token: str) -> None:
        self._stream_buffer += token
        self.write(Text(token, no_wrap=True))
        self._scroll_to_end()

    def end_stream(self) -> None:
        self._stream_role = ""
        self._stream_buffer = ""

    def _scroll_to_end(self) -> None:
        self.scroll_end(animate=False)
