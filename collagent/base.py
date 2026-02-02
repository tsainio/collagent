"""
CollAgent - Abstract Base Class for Agents

Copyright (C) 2026 Tuomo Sainio
Licensed under AGPL-3.0
"""

import threading
from abc import ABC, abstractmethod
from typing import Optional

from rich.table import Table


class CollAgentBase(ABC):
    """Abstract base class for CollAgent implementations."""

    def __init__(self, api_key: str, model: str, output_console=None):
        """
        Initialize the base agent.

        Args:
            api_key: API key for the provider
            model: Model identifier to use
            output_console: Console for output (uses global console if not provided)
        """
        self.api_key = api_key
        self.model_name = model
        self.collaborators = []
        self.searched_institutions = []
        self._collaborators_lock = threading.Lock()

        # Use provided console or import global console lazily
        if output_console is not None:
            self.console = output_console
        else:
            from .streaming import console
            self.console = console

    @abstractmethod
    def search(self, profile: str, institution: Optional[str] = None,
               focus_areas: Optional[list] = None, max_turns: int = 10) -> list:
        """
        Search for collaborators at a specific institution.

        Args:
            profile: User's research profile/description
            institution: Target institution to search
            focus_areas: Optional list of focus areas
            max_turns: Maximum agent turns

        Returns:
            List of collaborator dictionaries
        """
        pass

    @abstractmethod
    def search_broad(self, profile: str, focus_areas: Optional[list] = None,
                     region: Optional[str] = None, max_institutions: int = 5,
                     max_turns: int = 10) -> list:
        """
        Broad search: discover institutions first, then search each.

        Args:
            profile: User's research profile/description
            focus_areas: Optional list of focus areas
            region: Geographic region filter
            max_institutions: Maximum institutions to search
            max_turns: Maximum agent turns

        Returns:
            List of collaborator dictionaries
        """
        pass

    @abstractmethod
    def generate_report(self, output_file: Optional[str] = None) -> str:
        """
        Generate a markdown report of findings.

        Args:
            output_file: Optional path to save the report

        Returns:
            Markdown report string
        """
        pass

    # Fatal error codes that should trigger a modal (user-fixable issues)
    FATAL_ERROR_PATTERNS = {
        # OpenAI errors
        "insufficient_quota": ("API quota exceeded", "https://platform.openai.com/account/billing"),
        "invalid_api_key": ("Invalid API key", "https://platform.openai.com/api-keys"),
        "rate_limit_exceeded": ("Rate limit exceeded", None),
        # Google/Gemini errors
        "RESOURCE_EXHAUSTED": ("API quota exhausted", "https://console.cloud.google.com/billing"),
        "INVALID_ARGUMENT": ("Invalid API configuration", None),
        "PERMISSION_DENIED": ("API permission denied", None),
        "UNAUTHENTICATED": ("Invalid API key", "https://aistudio.google.com/apikey"),
        # HTTP status codes
        "401": ("Authentication failed - check your API key", None),
        "403": ("Access forbidden - check API permissions", None),
        "429": ("Too many requests - quota or rate limit exceeded", None),
    }

    def _handle_api_error(self, exception: Exception, context: str) -> bool:
        """
        Handle an API error, checking if it's a fatal (user-fixable) error.

        Args:
            exception: The exception that was raised
            context: Context string for error messages (e.g., "Phase 1")

        Returns:
            True if it was a fatal error (modal shown), False otherwise
        """
        error_str = str(exception)

        # Check for fatal error patterns
        for pattern, (message, help_url) in self.FATAL_ERROR_PATTERNS.items():
            if pattern.lower() in error_str.lower():
                # It's a fatal error - show modal if console supports it
                if hasattr(self.console, 'fatal_error'):
                    self.console.fatal_error(
                        f"{message}\n\n{error_str}",
                        error_code=pattern,
                        help_url=help_url
                    )
                else:
                    # Fall back to regular print for CLI
                    self.console.print(f"[bold red]{message}[/bold red]")
                    self.console.print(f"[red]{error_str}[/red]")
                    if help_url:
                        self.console.print(f"[dim]More info: {help_url}[/dim]")
                return True

        # Not a fatal error - just print it normally
        self.console.print(f"[red]API Error in {context}: {exception}[/red]")
        return False

    def print_shortlist(self, top_n: int = 5):
        """Print a shortlist table of top candidates to console."""
        if not self.collaborators:
            self.console.print("[yellow]No collaborators to display.[/yellow]")
            return

        sorted_collabs = sorted(
            self.collaborators,
            key=lambda x: x.get("alignment_score", 0),
            reverse=True
        )[:top_n]

        table = Table(
            title=f"Top {len(sorted_collabs)} Candidates",
            show_header=True,
            header_style="bold cyan",
            border_style="blue"
        )

        table.add_column("#", style="dim", width=3)
        table.add_column("Name", style="bold", min_width=20)
        table.add_column("Institution", min_width=15)
        table.add_column("Position", min_width=12)
        table.add_column("Score", justify="center", width=7)
        table.add_column("Research Focus", max_width=35)

        for i, c in enumerate(sorted_collabs, 1):
            score = c.get("alignment_score", 0)
            stars = "★" * score + "☆" * (5 - score)

            table.add_row(
                str(i),
                c.get("name", "Unknown"),
                c.get("institution", "N/A"),
                c.get("position", "N/A")[:20] if c.get("position") else "N/A",
                stars,
                (c.get("research_focus", "N/A")[:50] + "...")
                if c.get("research_focus") and len(c.get("research_focus", "")) > 50
                else c.get("research_focus", "N/A")
            )

        self.console.print()
        self.console.print(table)
        self.console.print()
