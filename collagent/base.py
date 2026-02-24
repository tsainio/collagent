"""
CollAgent - Abstract Base Class for Agents

Copyright (C) 2026 Tuomo Sainio
Licensed under AGPL-3.0
"""

import json
import re
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

        # Processing model (optional separate model for extraction)
        self.processing_client = None      # OpenAI or genai client
        self.processing_model_name = None  # Model name string
        self.processing_provider = None    # "google", "openai", or "openai_compatible"

        # Search tool (optional external search instead of built-in grounding)
        self.search_tool = None            # SearchTool instance
        self.search_client = None          # OpenAI client for search LLM
        self.search_model_name = None      # Model name for search LLM

        # Use provided console or import global console lazily
        if output_console is not None:
            self.console = output_console
        else:
            from .streaming import console
            self.console = console

    def set_processing_model(self, provider: str, model_name: str, client=None):
        """
        Configure a separate model for extraction/processing.

        Args:
            provider: "google", "openai", or "openai_compatible"
            model_name: Model name string
            client: Pre-configured client (OpenAI or genai.Client)
        """
        self.processing_provider = provider
        self.processing_model_name = model_name
        self.processing_client = client

    def set_search_tool(self, search_tool, client=None, model_name=None):
        """
        Configure an external search tool and optional separate search LLM.

        Args:
            search_tool: SearchTool instance
            client: OpenAI client for search LLM (uses main client if None)
            model_name: Model name for search LLM (uses main model if None)
        """
        self.search_tool = search_tool
        self.search_client = client
        self.search_model_name = model_name

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

    # ── Shared search/extraction methods for external tools ──────────────

    @staticmethod
    def _strip_thinking_tokens(text: str) -> str:
        """Strip <think>...</think> blocks from model output (e.g. qwen3)."""
        return re.sub(r'<think>.*?</think>\s*', '', text, flags=re.DOTALL)

    def _get_search_llm_client(self):
        """Get the OpenAI-compatible client to use for search LLM calls."""
        if self.search_client is not None:
            return self.search_client
        # Fall back to the agent's own client if it's an OpenAI client
        if hasattr(self, 'client'):
            return self.client
        return None

    def _get_search_llm_model(self):
        """Get the model name to use for search LLM calls."""
        if self.search_model_name is not None:
            return self.search_model_name
        return self.model_name

    def _run_tool_based_search(self, system_instruction: str, user_message: str,
                                continue_message: str, max_turns: int,
                                phase_name: str, error_context: str) -> str:
        """
        Multi-turn search using external search tool + any LLM via Chat Completions.

        Unlike built-in web search where each API call both searches and produces
        text, tool-based search separates these: the LLM requests searches via
        function calls, we execute them and feed results back, then the LLM
        synthesizes. A single "logical turn" may require multiple API round-trips
        (search calls + synthesis), so we track text turns and API calls separately.

        Returns accumulated research text.
        """
        client = self._get_search_llm_client()
        model = self._get_search_llm_model()

        if client is None:
            self.console.print("[red]No client available for tool-based search[/red]")
            return ""

        # Define the web_search function tool for Chat Completions
        tools = [{
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search the web for information. Returns a list of results with titles, URLs, and content snippets.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query"
                        }
                    },
                    "required": ["query"]
                }
            }
        }]

        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_message},
        ]

        accumulated_text = []
        last_response_length = 0

        text_turns = 0          # Turns where the LLM produced text (what max_turns limits)
        search_rounds = 0       # Function-call round-trips (search + feed results)
        max_search_rounds = max_turns * 3  # Generous ceiling to prevent runaway loops
        did_search = False      # Whether any searches were performed

        while text_turns < max_turns and search_rounds < max_search_rounds:
            self.console.print(f"[dim]{phase_name} round {search_rounds + text_turns + 1}...[/dim]")

            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=tools,
                    temperature=0.7,
                )
            except Exception as e:
                if self._handle_api_error(e, error_context):
                    return ""
                break

            choice = response.choices[0]
            message = choice.message

            # Append assistant message to history
            messages.append(message)

            # Capture any text the LLM produced alongside tool calls
            if message.content:
                clean_content = self._strip_thinking_tokens(message.content)
                if clean_content.strip():
                    accumulated_text.append(clean_content)
                    if len(clean_content) > 400 and hasattr(self.console, 'record'):
                        # Truncated for live view, full in log
                        self.console.print(f"[dim]{clean_content[:400]}...[/dim]", _record=False)
                        self.console.record(f"[dim]{clean_content}[/dim]")
                    else:
                        self.console.print(f"[dim]{clean_content}[/dim]")

            # Handle tool calls
            if message.tool_calls:
                did_search = True
                search_rounds += 1

                for tc in message.tool_calls:
                    if tc.function.name == "web_search":
                        try:
                            args = json.loads(tc.function.arguments)
                            query = args.get("query", "")
                            self.console.print(f"[dim]  Searching: {query}[/dim]")
                            results = self.search_tool.search(query)
                            result_text = json.dumps(results, ensure_ascii=False)
                        except Exception as e:
                            result_text = json.dumps({"error": str(e)})

                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": result_text,
                        })
                    else:
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": json.dumps({"error": f"Unknown function: {tc.function.name}"}),
                        })
                # Let the LLM process the search results
                continue

            # No tool calls — this is a pure text response (a "text turn")
            response_text = self._strip_thinking_tokens(message.content or "")
            if response_text:
                # Text was already captured above, just check stop conditions
                text_turns += 1

                if "SEARCH COMPLETE" in response_text.upper():
                    self.console.print("[dim]Search complete signal received.[/dim]")
                    break

                if last_response_length > 0 and len(response_text) < last_response_length * 0.3:
                    self.console.print("[dim]Diminishing returns detected, stopping.[/dim]")
                    break

                last_response_length = len(response_text)

                # Ask model to continue
                messages.append({"role": "user", "content": continue_message})
            else:
                if accumulated_text:
                    break

            if choice.finish_reason == "stop" and not message.tool_calls:
                # Model decided to stop naturally
                if accumulated_text:
                    break

        # If searches were performed but no text synthesis was produced,
        # make a final call without tools to force the LLM to summarize
        if not accumulated_text and did_search:
            self.console.print(f"[dim]Synthesizing search results...[/dim]")
            messages.append({
                "role": "user",
                "content": (
                    "Based on all the search results you have gathered, provide a "
                    "comprehensive summary of your findings. SEARCH COMPLETE"
                ),
            })
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.7,
                )
                response_text = self._strip_thinking_tokens(response.choices[0].message.content or "")
                if response_text.strip():
                    accumulated_text.append(response_text)
            except Exception:
                pass

        return "\n\n".join(accumulated_text)

    def _run_chat_completions_extraction(self, system_instruction: str, user_message: str,
                                          save_func_schema: dict, save_func_name: str,
                                          on_save: callable, progress_message: str,
                                          error_context: str, max_turns: int = 5) -> list:
        """
        Generic extraction using OpenAI Chat Completions API.

        Multi-turn function calling loop with save + finish tools.
        Used for openai_compatible provider and OpenAI models via Chat Completions.

        Args:
            system_instruction: System prompt for extraction
            user_message: User prompt with research text
            save_func_schema: JSON schema dict for save function (Chat Completions format)
            save_func_name: Name of the save function to match
            on_save: Callback(args) -> (display_name, score, result_message)
            progress_message: Message to show during extraction
            error_context: Context for error messages
            max_turns: Maximum extraction turns

        Returns:
            List of extracted items
        """
        client = self.processing_client
        model = self.processing_model_name

        if client is None or model is None:
            self.console.print("[red]No processing client configured for chat completions extraction[/red]")
            return []

        # Build tools list
        finish_tool = {
            "type": "function",
            "function": {
                "name": "finish_extraction",
                "description": "Call this after saving all items.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "summary": {
                            "type": "string",
                            "description": "Brief summary"
                        }
                    },
                    "required": ["summary"]
                }
            }
        }

        # Normalize save_func_schema to Chat Completions tool format
        if "function" in save_func_schema:
            save_tool = {"type": "function", "function": save_func_schema["function"]}
        else:
            save_tool = {"type": "function", "function": save_func_schema}

        tools = [save_tool, finish_tool]

        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_message},
        ]

        items = []

        for turn in range(max_turns):
            self.console.print(f"[dim]{progress_message}[/dim]")

            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=tools,
                    temperature=0.3,
                )
            except Exception as e:
                if self._handle_api_error(e, error_context):
                    return items
                break

            choice = response.choices[0]
            message = choice.message

            messages.append(message)

            if not message.tool_calls:
                break

            finished = False
            for tc in message.tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                except json.JSONDecodeError:
                    args = {}

                if name == save_func_name:
                    display_name, score, result = on_save(args)
                    items.append(args)
                    self.console.print(f"[green]✓ Saved:[/green] {display_name} ({score}/5)")
                elif name == "finish_extraction":
                    finished = True
                    result = "Extraction complete"
                else:
                    result = f"Unknown: {name}"

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps({"result": result}),
                })

            if finished:
                break

        return items

    def _run_genai_extraction(self, system_instruction: str, user_message: str,
                               save_func_schema: dict, save_func_name: str,
                               on_save: callable, progress_message: str,
                               error_context: str, max_turns: int = 5) -> list:
        """
        Extraction using Google genai API.

        Used when processing_provider is "google" but the main agent is not Google.

        Args:
            system_instruction: System prompt for extraction
            user_message: User prompt with research text
            save_func_schema: JSON schema dict for save function
            save_func_name: Name of the save function to match
            on_save: Callback(args) -> (display_name, score, result_message)
            progress_message: Message to show during extraction
            error_context: Context for error messages
            max_turns: Maximum extraction turns

        Returns:
            List of extracted items
        """
        from google import genai
        from google.genai import types

        client = self.processing_client
        model = self.processing_model_name

        if client is None or model is None:
            self.console.print("[red]No processing client configured for genai extraction[/red]")
            return []

        # Convert JSON schema to genai FunctionDeclaration
        func_info = save_func_schema.get("function", save_func_schema)
        properties = {}
        for prop_name, prop_def in func_info.get("parameters", {}).get("properties", {}).items():
            schema_type = prop_def.get("type", "STRING").upper()
            type_map = {
                "STRING": types.Type.STRING,
                "INTEGER": types.Type.INTEGER,
                "NUMBER": types.Type.NUMBER,
                "BOOLEAN": types.Type.BOOLEAN,
            }
            properties[prop_name] = types.Schema(
                type=type_map.get(schema_type, types.Type.STRING),
                description=prop_def.get("description", "")
            )

        save_func_decl = types.FunctionDeclaration(
            name=func_info.get("name", save_func_name),
            description=func_info.get("description", ""),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties=properties,
                required=func_info.get("parameters", {}).get("required", [])
            )
        )

        finish_func = types.FunctionDeclaration(
            name="finish_extraction",
            description="Call this after saving all items.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "summary": types.Schema(type=types.Type.STRING, description="Brief summary"),
                },
                required=["summary"]
            )
        )

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            tools=[types.Tool(function_declarations=[save_func_decl, finish_func])],
            temperature=0.3,
        )

        contents = [types.Content(role="user", parts=[types.Part(text=user_message)])]
        items = []

        for turn in range(max_turns):
            self.console.print(f"[dim]{progress_message}[/dim]")

            try:
                response = client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=config,
                )
            except Exception as e:
                if self._handle_api_error(e, error_context):
                    return items
                break

            # Parse function calls from genai response
            function_calls = []
            try:
                if (response.candidates and
                    response.candidates[0].content and
                    response.candidates[0].content.parts):
                    for part in response.candidates[0].content.parts:
                        if hasattr(part, 'function_call') and part.function_call:
                            function_calls.append(part.function_call)
            except (AttributeError, IndexError):
                pass

            if not function_calls:
                break

            if response.candidates and response.candidates[0].content:
                contents.append(response.candidates[0].content)

            function_responses = []
            finished = False

            for fc in function_calls:
                name = fc.name
                args = dict(fc.args) if fc.args else {}

                if name == save_func_name:
                    display_name, score, result = on_save(args)
                    items.append(args)
                    self.console.print(f"[green]✓ Saved:[/green] {display_name} ({score}/5)")
                elif name == "finish_extraction":
                    finished = True
                    result = "Extraction complete"
                else:
                    result = f"Unknown: {name}"

                function_responses.append(types.Part(
                    function_response=types.FunctionResponse(
                        name=name,
                        response={"result": result}
                    )
                ))

            contents.append(types.Content(role="user", parts=function_responses))

            if finished:
                break

        return items

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
