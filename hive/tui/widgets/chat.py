from textual.strip import Strip
from textual.widgets import RichLog
from rich.markdown import Markdown
from rich.text import Text

class ChatWidget(RichLog):
    def __init__(self) -> None:
        super().__init__(id="chat-log", highlight=True, markup=True, wrap=True, min_width=40)
        self._stream_buffer = ""
        self._stream_role = ""

    def add_message(self, role: str, content: str) -> None:
        if role == "user":
            header = Text("\n  👤  You\n", style="bold #f59e0b")
        elif role == "assistant":
            header = Text("\n  🤖  Assistant\n", style="bold #22c55e")
        elif role == "system":
            header = Text("\n  ⚙  System\n", style="bold #64748b")
        else:
            header = Text(f"\n  ⚡  {role.capitalize()}\n", style="bold #94a3b8")
            
        body = Markdown(content) if content else Text("")
        sep = Text("\n  " + "─" * 20, style="#2a2d42")
        
        self.write(header)
        self.write(body)
        self.write(sep)
        self._scroll_to_end()

    def start_stream(self, role: str) -> None:
        self._stream_role = role
        self._stream_buffer = ""
        if role == "user":
            header = Text("\n  👤  You\n", style="bold #f59e0b")
        elif role == "assistant":
            header = Text("\n  🤖  Assistant\n", style="bold #22c55e")
        elif role == "system":
            header = Text("\n  ⚙  System\n", style="bold #64748b")
        else:
            header = Text(f"\n  ⚡  {role.capitalize()}\n", style="bold #94a3b8")
            
        self.write(header)
        self.write(Text("  ● ● ●\n", style="#64748b"))

    def append_token(self, token: str) -> None:
        self._stream_buffer += token
        self.write(Text(token, no_wrap=True))
        self._scroll_to_end()

    def end_stream(self) -> None:
        self._stream_role = ""
        self._stream_buffer = ""
        self.write(Text("\n  " + "─" * 20, style="#2a2d42"))

    def _scroll_to_end(self) -> None:
        self.scroll_end(animate=False)
