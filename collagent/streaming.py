"""
CollAgent - Streaming Console and Output Handling

Copyright (C) 2026 Tuomo Sainio
Licensed under AGPL-3.0
"""

import io
import threading
from queue import Queue

from rich.console import Console


# Global console for CLI output
console = Console(width=100, record=True)

# Storage for web search results (thread-safe)
search_results = {}
search_results_lock = threading.Lock()


class StreamingConsole:
    """A console that captures output and sends it to a queue for SSE streaming."""

    def __init__(self, output_queue: Queue):
        self.queue = output_queue
        self._console = Console(width=80, record=True, force_terminal=True)
        self._thread_local = threading.local()  # Thread-local storage for section

    def set_section(self, section: str = None):
        """Set the current section for message grouping (thread-local)."""
        self._thread_local.section = section

    def _get_section(self):
        """Get the current section for this thread."""
        return getattr(self._thread_local, 'section', None)

    def fatal_error(self, message: str, error_code: str = None, help_url: str = None):
        """Send a fatal error that should be shown as a modal to the user.

        Use this for catastrophic errors that are user-fixable (billing, auth, etc.)
        rather than transient errors that might resolve on retry.

        Args:
            message: The error message to display
            error_code: Optional error code (e.g., 'insufficient_quota', 'invalid_api_key')
            help_url: Optional URL for more information
        """
        msg = {
            "type": "fatal_error",
            "text": message,
        }
        if error_code:
            msg["code"] = error_code
        if help_url:
            msg["help_url"] = help_url
        self.queue.put(msg)

    def print(self, *args, section: str = None, **kwargs):
        """Capture print output and send to queue.

        Args:
            section: Optional section identifier for grouping messages.
                     If not provided, uses the current section set via set_section().
        """
        # Create a string buffer to capture the output
        buffer = io.StringIO()
        temp_console = Console(file=buffer, width=80, force_terminal=False, no_color=True)
        temp_console.print(*args, **kwargs)
        text = buffer.getvalue().strip()

        if text:
            # Determine log level based on rich markup
            level = "info"
            text_str = str(args[0]) if args else ""
            if "[red]" in text_str or "[bold red]" in text_str:
                level = "error"
            elif "[yellow]" in text_str:
                level = "warning"
            elif "[green]" in text_str or "[bold green]" in text_str:
                level = "success"
            elif "[dim]" in text_str:
                level = "dim"
            elif "[cyan]" in text_str or "[bold cyan]" in text_str:
                level = "info"

            # Use provided section or fall back to thread-local section
            msg_section = section if section is not None else self._get_section()

            msg = {"type": "log", "text": text, "level": level}
            if msg_section:
                msg["section"] = msg_section
            self.queue.put(msg)

        # Also record to the internal console for HTML export
        self._console.print(*args, **kwargs)

    def save_html(self, path: str, clear: bool = False):
        """Save console output as HTML."""
        self._console.save_html(path, clear=clear)

    def export_html(self) -> str:
        """Export console output as HTML string."""
        return self._console.export_html()
