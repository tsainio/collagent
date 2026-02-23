"""
CollAgent - Core Agent Class (Google Implementation)

Copyright (C) 2026 Tuomo Sainio
Licensed under AGPL-3.0
"""

import concurrent.futures
from datetime import datetime
from typing import Optional

from google import genai
from google.genai import types
from rich.panel import Panel

from .base import CollAgentBase


class CollAgentGoogle(CollAgentBase):
    """Research Collaborator Search Agent using Google GenAI SDK (Two-Phase)"""

    def __init__(self, api_key: str, model: str = "gemini-3-flash-preview", output_console=None):
        super().__init__(api_key, model, output_console)
        self.client = genai.Client(api_key=api_key)

    def get_response_text(self, response) -> str:
        """Extract text from response"""
        try:
            if (response.candidates and
                response.candidates[0].content and
                response.candidates[0].content.parts):
                texts = []
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'text') and part.text:
                        texts.append(part.text)
                return "\n".join(texts)
        except (AttributeError, IndexError):
            pass
        return ""

    def parse_function_calls(self, response) -> list:
        """Extract function calls from response"""
        calls = []
        try:
            if (response.candidates and
                response.candidates[0].content and
                response.candidates[0].content.parts):
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        calls.append(part.function_call)
        except (AttributeError, IndexError):
            pass
        return calls

    def _run_tool_based_search(self, system_instruction: str, user_message: str,
                                continue_message: str, max_turns: int,
                                phase_name: str, error_context: str) -> str:
        """
        Override base method: if we have an OpenAI search client, use it.
        Otherwise, use the genai client with function calling for the search LLM.
        """
        if self._get_search_llm_client() is not None and self.search_client is not None:
            # We have an explicit OpenAI search client — use the base Chat Completions method
            return super()._run_tool_based_search(
                system_instruction, user_message, continue_message,
                max_turns, phase_name, error_context
            )

        # Use genai function calling with the external search tool
        return self._run_tool_based_search_genai(
            system_instruction, user_message, continue_message,
            max_turns, phase_name, error_context
        )

    def _run_tool_based_search_genai(self, system_instruction: str, user_message: str,
                                      continue_message: str, max_turns: int,
                                      phase_name: str, error_context: str) -> str:
        """
        Multi-turn search using external search tool + Google genai function calling.
        Used when the Google agent has a search_tool but no OpenAI search client.

        Unlike grounded search where each API call both searches and produces text,
        tool-based search separates these: the LLM requests searches via function
        calls, we execute them and feed results back, then the LLM synthesizes.
        A single "logical turn" may require multiple API round-trips (search calls
        + synthesis), so we track text turns and API calls separately.
        """
        import json

        web_search_func = types.FunctionDeclaration(
            name="web_search",
            description="Search the web for information. Returns a list of results with titles, URLs, and content snippets.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "query": types.Schema(type=types.Type.STRING, description="The search query"),
                },
                required=["query"]
            )
        )

        search_config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            tools=[types.Tool(function_declarations=[web_search_func])],
            temperature=0.7,
        )

        contents = [types.Content(role="user", parts=[types.Part(text=user_message)])]
        accumulated_text = []
        last_response_length = 0

        text_turns = 0          # Turns where the LLM produced text (what max_turns limits)
        search_rounds = 0       # Function-call round-trips (search + feed results)
        max_search_rounds = max_turns * 3  # Generous ceiling to prevent runaway loops
        did_search = False      # Whether any searches were performed

        while text_turns < max_turns and search_rounds < max_search_rounds:
            self.console.print(f"[dim]{phase_name} turn {text_turns + 1}/{max_turns}...[/dim]")

            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=search_config,
                )
            except Exception as e:
                if self._handle_api_error(e, error_context):
                    return ""
                break

            # Check for function calls and text — a response can contain both
            func_calls = self.parse_function_calls(response)
            response_text = self.get_response_text(response)

            # Capture any text the LLM produced alongside function calls
            if response_text:
                accumulated_text.append(response_text)
                preview = response_text[:400] + "..." if len(response_text) > 400 else response_text
                self.console.print(f"[dim]{preview}[/dim]")

            if func_calls:
                did_search = True
                search_rounds += 1

                # Append assistant response to conversation
                if response.candidates and response.candidates[0].content:
                    contents.append(response.candidates[0].content)

                # Execute each search and collect results
                function_responses = []
                for fc in func_calls:
                    if fc.name == "web_search":
                        args = dict(fc.args) if fc.args else {}
                        query = args.get("query", "")
                        self.console.print(f"[dim]  Searching: {query}[/dim]")
                        try:
                            results = self.search_tool.search(query)
                            result_text = json.dumps(results, ensure_ascii=False)
                        except Exception as e:
                            result_text = json.dumps({"error": str(e)})
                    else:
                        result_text = json.dumps({"error": f"Unknown function: {fc.name}"})

                    function_responses.append(types.Part(
                        function_response=types.FunctionResponse(
                            name=fc.name,
                            response={"result": result_text}
                        )
                    ))

                contents.append(types.Content(role="user", parts=function_responses))
                continue  # Let the LLM process the results

            # No function calls — this is a pure text response (a "text turn")
            if response_text:
                text_turns += 1

                if "SEARCH COMPLETE" in response_text.upper():
                    self.console.print("[dim]Search complete signal received.[/dim]")
                    break

                if last_response_length > 0 and len(response_text) < last_response_length * 0.3:
                    self.console.print("[dim]Diminishing returns detected, stopping.[/dim]")
                    break

                last_response_length = len(response_text)

                # Continue conversation
                if response.candidates and response.candidates[0].content:
                    contents.append(response.candidates[0].content)
                    contents.append(types.Content(
                        role="user",
                        parts=[types.Part(text=continue_message)]
                    ))
            else:
                if accumulated_text:
                    break

        # If searches were performed but no text synthesis was produced,
        # make a final call without tools to force the LLM to summarize
        if not accumulated_text and did_search:
            self.console.print(f"[dim]Synthesizing search results...[/dim]")
            synthesis_config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7,
            )
            contents.append(types.Content(
                role="user",
                parts=[types.Part(text=(
                    "Based on all the search results you have gathered, provide a "
                    "comprehensive summary of your findings. SEARCH COMPLETE"
                ))]
            ))
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=synthesis_config,
                )
                response_text = self.get_response_text(response)
                if response_text:
                    accumulated_text.append(response_text)
            except Exception:
                pass

        return "\n\n".join(accumulated_text)

    def _run_grounded_search(self, system_instruction: str, user_message: str,
                              continue_message: str, max_turns: int,
                              phase_name: str, error_context: str) -> str:
        """
        Run a multi-turn Google Search grounded conversation.
        Returns accumulated research text.
        """
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.7,
        )

        contents = [types.Content(role="user", parts=[types.Part(text=user_message)])]
        accumulated_text = []
        last_response_length = 0

        turn = 0
        while turn < max_turns:
            turn += 1

            self.console.print(f"[dim]{phase_name} turn {turn}/{max_turns}...[/dim]")

            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=config,
                )
            except Exception as e:
                if self._handle_api_error(e, error_context):
                    return ""  # Fatal error - abort completely
                break

            response_text = self.get_response_text(response)
            if response_text:
                accumulated_text.append(response_text)
                preview = response_text[:400] + "..." if len(response_text) > 400 else response_text
                self.console.print(f"[dim]{preview}[/dim]")

                # Check for stop phrase
                if "SEARCH COMPLETE" in response_text.upper():
                    self.console.print("[dim]Search complete signal received.[/dim]")
                    break

                # Check for diminishing returns
                if last_response_length > 0 and len(response_text) < last_response_length * 0.3:
                    self.console.print("[dim]Diminishing returns detected, stopping.[/dim]")
                    break

                last_response_length = len(response_text)

            # Continue conversation for multi-turn search
            try:
                if response.candidates and response.candidates[0].content:
                    contents.append(response.candidates[0].content)
                    contents.append(types.Content(
                        role="user",
                        parts=[types.Part(text=continue_message)]
                    ))
                else:
                    self.console.print("[dim]No more results.[/dim]")
                    break
            except (AttributeError, IndexError) as e:
                self.console.print(f"[yellow]Response parsing issue: {e}[/yellow]")
                break

        return "\n\n".join(accumulated_text)

    def _run_extraction_loop(self, system_instruction: str, user_message: str,
                              save_func: types.FunctionDeclaration,
                              save_func_name: str, on_save: callable,
                              progress_message: str, error_context: str,
                              max_turns: int = 5) -> list:
        """
        Run a function-calling extraction loop.

        Args:
            system_instruction: System prompt for extraction
            user_message: User prompt with research text
            save_func: FunctionDeclaration for the save function
            save_func_name: Name of the save function to match
            on_save: Callback(args) -> (display_name, score, result_message)
            progress_message: Message to show during extraction
            error_context: Context for error messages
            max_turns: Maximum extraction turns

        Returns:
            List of extracted items
        """
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
            tools=[types.Tool(function_declarations=[save_func, finish_func])],
            temperature=0.3,
        )

        contents = [types.Content(role="user", parts=[types.Part(text=user_message)])]
        items = []

        for turn in range(max_turns):
            self.console.print(f"[dim]{progress_message}[/dim]")

            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=config,
                )
            except Exception as e:
                if self._handle_api_error(e, error_context):
                    return items  # Fatal error - abort completely
                break

            function_calls = self.parse_function_calls(response)

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

    def phase1_research(self, profile: str, institution: Optional[str] = None,
                        focus_areas: Optional[list] = None, max_turns: int = 10) -> str:
        """
        Phase 1: Use Google Search grounding to research potential collaborators.
        Returns accumulated research text.
        """
        search_method = "external search tool" if self.search_tool else "Google Search"
        self.console.print(f"[cyan]Phase 1: Researching with {search_method}...[/cyan]")

        system_instruction = """You are a research assistant finding potential collaborators.

Your task: Search for researchers at the target institution and gather detailed information about them.

For each promising researcher, collect:
- Full name and current position
- Research focus and lab/group
- Recent publications or projects
- Contact information if available
- Website/profile URL

Search thoroughly using multiple queries. Focus on finding 3-5 researchers whose work aligns well with the user's profile.

IMPORTANT: When you have gathered sufficient information about 3-5 good candidates and have no more useful searches to perform, end your response with the exact phrase "SEARCH COMPLETE" on its own line."""

        user_message = f"""Find potential research collaborators for me.

## My Research Profile
{profile}

## Search Parameters
- Target Institution: {institution or "Any relevant institution"}
- Focus Areas: {", ".join(focus_areas) if focus_areas else "Based on my profile"}

Search for researchers and gather detailed information about promising matches. When done, say "SEARCH COMPLETE"."""

        if self.search_tool:
            return self._run_tool_based_search(
                system_instruction=system_instruction,
                user_message=user_message,
                continue_message="Continue searching. If you have found enough candidates (3-5), provide a summary and say 'SEARCH COMPLETE'.",
                max_turns=max_turns,
                phase_name="Research",
                error_context="Phase 1"
            )

        return self._run_grounded_search(
            system_instruction=system_instruction,
            user_message=user_message,
            continue_message="Continue searching. If you have found enough candidates (3-5), provide a summary and say 'SEARCH COMPLETE'.",
            max_turns=max_turns,
            phase_name="Research",
            error_context="Phase 1"
        )

    def phase2_extract(self, research_text: str, profile: str) -> list:
        """
        Phase 2: Use function calling to extract structured collaborator data.
        """
        self.console.print("\n[cyan]Phase 2: Extracting structured data...[/cyan]")

        system_instruction = """Extract collaborator information from the research text and save each one using save_collaborator.

For each researcher mentioned:
1. Call save_collaborator with all available information
2. Assign an alignment_score (1-5) based on fit with the user's profile. BE CRITICAL AND CONSERVATIVE:
   - 5: Exceptional - direct research overlap, same methods/techniques, obvious synergy
   - 4: Strong - significant overlap in research area, complementary expertise
   - 3: Moderate - some shared interests but different focus or methods
   - 2: Weak - tangential connection, would require significant stretch to collaborate
   - 1: Minimal - only broadly related field, no clear collaboration angle
   Most candidates should score 2-3. Reserve 4-5 for truly excellent matches.
3. Explain WHY they're a good match in alignment_reasons

After saving all collaborators, call finish_extraction."""

        user_message = f"""Based on the following research, extract and save each potential collaborator.

## User's Research Profile (for scoring alignment)
{profile}

## Research Findings
{research_text}

Call save_collaborator for each researcher, then finish_extraction when done."""

        def on_save_collaborator(args):
            with self._collaborators_lock:
                self.collaborators.append(args)
            name = args.get("name", "Unknown")
            score = args.get("alignment_score", "?")
            return (name, f"alignment: {score}", f"Saved: {name}")

        # Route to appropriate extraction method based on processing provider
        if self.processing_provider in ("openai_compatible", "openai"):
            save_collaborator_schema = {
                "name": "save_collaborator",
                "description": "Save a potential collaborator. Call this for each researcher found.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Researcher's full name"},
                        "position": {"type": "string", "description": "Current position/title"},
                        "institution": {"type": "string", "description": "Institution name"},
                        "email": {"type": "string", "description": "Contact email if found"},
                        "research_focus": {"type": "string", "description": "Their main research areas"},
                        "alignment_score": {"type": "integer", "description": "Alignment with user's research (1-5). Be critical: 5=exceptional direct overlap, 4=strong overlap, 3=moderate relevance, 2=weak connection, 1=minimal relevance"},
                        "alignment_reasons": {"type": "string", "description": "Why this person is a good match"},
                        "key_publications": {"type": "string", "description": "Relevant recent publications"},
                        "collaboration_angle": {"type": "string", "description": "Suggested collaboration approach"},
                    },
                    "required": ["name", "institution", "research_focus", "alignment_score", "alignment_reasons"]
                }
            }

            self._run_chat_completions_extraction(
                system_instruction=system_instruction,
                user_message=user_message,
                save_func_schema=save_collaborator_schema,
                save_func_name="save_collaborator",
                on_save=on_save_collaborator,
                progress_message="Extracting data...",
                error_context="Phase 2"
            )
        elif self.processing_provider == "google":
            # Use genai extraction with the processing model
            save_collaborator_schema = {
                "name": "save_collaborator",
                "description": "Save a potential collaborator. Call this for each researcher found.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Researcher's full name"},
                        "position": {"type": "string", "description": "Current position/title"},
                        "institution": {"type": "string", "description": "Institution name"},
                        "email": {"type": "string", "description": "Contact email if found"},
                        "research_focus": {"type": "string", "description": "Their main research areas"},
                        "alignment_score": {"type": "integer", "description": "Alignment with user's research (1-5). Be critical: 5=exceptional direct overlap, 4=strong overlap, 3=moderate relevance, 2=weak connection, 1=minimal relevance"},
                        "alignment_reasons": {"type": "string", "description": "Why this person is a good match"},
                        "key_publications": {"type": "string", "description": "Relevant recent publications"},
                        "collaboration_angle": {"type": "string", "description": "Suggested collaboration approach"},
                    },
                    "required": ["name", "institution", "research_focus", "alignment_score", "alignment_reasons"]
                }
            }

            # Temporarily swap model name for extraction
            orig_model = self.model_name
            self.model_name = self.processing_model_name
            orig_client = self.client
            self.client = self.processing_client

            save_collaborator_func = types.FunctionDeclaration(
                name="save_collaborator",
                description="Save a potential collaborator. Call this for each researcher found.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "name": types.Schema(type=types.Type.STRING, description="Researcher's full name"),
                        "position": types.Schema(type=types.Type.STRING, description="Current position/title"),
                        "institution": types.Schema(type=types.Type.STRING, description="Institution name"),
                        "email": types.Schema(type=types.Type.STRING, description="Contact email if found"),
                        "research_focus": types.Schema(type=types.Type.STRING, description="Their main research areas"),
                        "alignment_score": types.Schema(type=types.Type.INTEGER, description="Alignment with user's research (1-5). Be critical: 5=exceptional direct overlap, 4=strong overlap, 3=moderate relevance, 2=weak connection, 1=minimal relevance"),
                        "alignment_reasons": types.Schema(type=types.Type.STRING, description="Why this person is a good match"),
                        "key_publications": types.Schema(type=types.Type.STRING, description="Relevant recent publications"),
                        "collaboration_angle": types.Schema(type=types.Type.STRING, description="Suggested collaboration approach"),
                    },
                    required=["name", "institution", "research_focus", "alignment_score", "alignment_reasons"]
                )
            )

            try:
                self._run_extraction_loop(
                    system_instruction=system_instruction,
                    user_message=user_message,
                    save_func=save_collaborator_func,
                    save_func_name="save_collaborator",
                    on_save=on_save_collaborator,
                    progress_message="Extracting data...",
                    error_context="Phase 2"
                )
            finally:
                self.model_name = orig_model
                self.client = orig_client
        else:
            # Default: use native genai extraction with main model
            save_collaborator_func = types.FunctionDeclaration(
                name="save_collaborator",
                description="Save a potential collaborator. Call this for each researcher found.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "name": types.Schema(type=types.Type.STRING, description="Researcher's full name"),
                        "position": types.Schema(type=types.Type.STRING, description="Current position/title"),
                        "institution": types.Schema(type=types.Type.STRING, description="Institution name"),
                        "email": types.Schema(type=types.Type.STRING, description="Contact email if found"),
                        "research_focus": types.Schema(type=types.Type.STRING, description="Their main research areas"),
                        "alignment_score": types.Schema(type=types.Type.INTEGER, description="Alignment with user's research (1-5). Be critical: 5=exceptional direct overlap, 4=strong overlap, 3=moderate relevance, 2=weak connection, 1=minimal relevance"),
                        "alignment_reasons": types.Schema(type=types.Type.STRING, description="Why this person is a good match"),
                        "key_publications": types.Schema(type=types.Type.STRING, description="Relevant recent publications"),
                        "collaboration_angle": types.Schema(type=types.Type.STRING, description="Suggested collaboration approach"),
                    },
                    required=["name", "institution", "research_focus", "alignment_score", "alignment_reasons"]
                )
            )

            self._run_extraction_loop(
                system_instruction=system_instruction,
                user_message=user_message,
                save_func=save_collaborator_func,
                save_func_name="save_collaborator",
                on_save=on_save_collaborator,
                progress_message="Extracting data...",
                error_context="Phase 2"
            )

        return self.collaborators

    def discover_institutions(self, profile: str, focus_areas: Optional[list] = None,
                              region: Optional[str] = None, max_turns: int = 5) -> str:
        """
        Discover suitable institutions/departments based on research profile.
        Uses Google Search grounding to find relevant universities and research groups.
        Returns accumulated research text about institutions.
        """
        self.console.print("[cyan]Phase 0: Discovering institutions...[/cyan]")

        system_instruction = """You are a research assistant helping find suitable institutions for academic collaboration.

Your task: Search for universities, research institutes, and departments that are strong in the user's research area.

For each promising institution, collect:
- Institution name and department/school
- Country and city
- Key research groups or centers relevant to the research area
- Notable faculty or research strengths
- Why it's a good match for collaboration

Search thoroughly using multiple queries. Focus on finding 5-10 institutions that are leaders in the relevant research areas.

IMPORTANT: When you have gathered sufficient information about 5-10 good institutions and have no more useful searches to perform, end your response with the exact phrase "SEARCH COMPLETE" on its own line."""

        region_constraint = f"\n- Region preference: {region}" if region else ""
        focus_str = ", ".join(focus_areas) if focus_areas else "Based on my profile"

        user_message = f"""Find top institutions for potential research collaboration.

## My Research Profile
{profile}

## Search Parameters
- Focus Areas: {focus_str}{region_constraint}

Search for universities and research institutes that are strong in these areas. When done, say "SEARCH COMPLETE"."""

        if self.search_tool:
            return self._run_tool_based_search(
                system_instruction=system_instruction,
                user_message=user_message,
                continue_message="Continue searching. If you have found enough institutions (5-10), provide a summary and say 'SEARCH COMPLETE'.",
                max_turns=max_turns,
                phase_name="Institution discovery",
                error_context="Institution Discovery"
            )

        return self._run_grounded_search(
            system_instruction=system_instruction,
            user_message=user_message,
            continue_message="Continue searching. If you have found enough institutions (5-10), provide a summary and say 'SEARCH COMPLETE'.",
            max_turns=max_turns,
            phase_name="Institution discovery",
            error_context="Institution Discovery"
        )

    def extract_institutions(self, research_text: str, profile: str) -> list:
        """
        Extract structured institution data from research text.
        Uses function calling to save institution information.
        """
        self.console.print("\n[cyan]Extracting institution data...[/cyan]")

        system_instruction = """Extract institution information from the research text and save each one using save_institution.

For each institution mentioned:
1. Call save_institution with all available information
2. Assign a relevance_score (1-5) based on fit with the user's research profile. BE CRITICAL AND CONSERVATIVE:
   - 5: World-leading - top institution specifically in user's exact research area
   - 4: Strong - excellent program with clear relevance to user's research
   - 3: Relevant - good institution but not specialized in user's specific area
   - 2: Tangential - some related work but not a strong fit
   - 1: Weak - only loosely connected to user's research interests
   Most institutions should score 2-3. Reserve 4-5 for truly exceptional fits.
3. Explain WHY it's a good match in the reason field

After saving all institutions, call finish_extraction."""

        user_message = f"""Based on the following research, extract and save each potential institution.

## User's Research Profile (for scoring relevance)
{profile}

## Research Findings
{research_text}

Call save_institution for each institution, then finish_extraction when done."""

        def on_save_institution(args):
            name = args.get("name", "Unknown")
            score = args.get("relevance_score", "?")
            return (name, f"relevance: {score}", f"Saved: {name}")

        save_institution_json_schema = {
            "name": "save_institution",
            "description": "Save a potential institution for collaboration. Call this for each institution found.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Institution name (e.g., 'ETH Zürich', 'LUT University')"},
                    "department": {"type": "string", "description": "Relevant department or school"},
                    "country": {"type": "string", "description": "Country where the institution is located"},
                    "city": {"type": "string", "description": "City where the institution is located"},
                    "relevance_score": {"type": "integer", "description": "Relevance to user's research (1-5). Be critical: 5=world-leading in exact area, 4=strong program, 3=relevant but not specialized, 2=tangential, 1=weak fit"},
                    "reason": {"type": "string", "description": "Why this institution is a good match"},
                    "key_groups": {"type": "string", "description": "Key research groups or centers"},
                },
                "required": ["name", "country", "relevance_score", "reason"]
            }
        }

        if self.processing_provider in ("openai_compatible", "openai"):
            institutions = self._run_chat_completions_extraction(
                system_instruction=system_instruction,
                user_message=user_message,
                save_func_schema=save_institution_json_schema,
                save_func_name="save_institution",
                on_save=on_save_institution,
                progress_message="Extracting institutions...",
                error_context="Institution Extraction"
            )
        elif self.processing_provider == "google":
            # Use genai with the processing model
            save_institution_func = types.FunctionDeclaration(
                name="save_institution",
                description="Save a potential institution for collaboration. Call this for each institution found.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "name": types.Schema(type=types.Type.STRING, description="Institution name (e.g., 'ETH Zürich', 'LUT University')"),
                        "department": types.Schema(type=types.Type.STRING, description="Relevant department or school"),
                        "country": types.Schema(type=types.Type.STRING, description="Country where the institution is located"),
                        "city": types.Schema(type=types.Type.STRING, description="City where the institution is located"),
                        "relevance_score": types.Schema(type=types.Type.INTEGER, description="Relevance to user's research (1-5). Be critical: 5=world-leading in exact area, 4=strong program, 3=relevant but not specialized, 2=tangential, 1=weak fit"),
                        "reason": types.Schema(type=types.Type.STRING, description="Why this institution is a good match"),
                        "key_groups": types.Schema(type=types.Type.STRING, description="Key research groups or centers"),
                    },
                    required=["name", "country", "relevance_score", "reason"]
                )
            )

            orig_model = self.model_name
            orig_client = self.client
            self.model_name = self.processing_model_name
            self.client = self.processing_client

            try:
                institutions = self._run_extraction_loop(
                    system_instruction=system_instruction,
                    user_message=user_message,
                    save_func=save_institution_func,
                    save_func_name="save_institution",
                    on_save=on_save_institution,
                    progress_message="Extracting institutions...",
                    error_context="Institution Extraction"
                )
            finally:
                self.model_name = orig_model
                self.client = orig_client
        else:
            # Default: use native genai extraction with main model
            save_institution_func = types.FunctionDeclaration(
                name="save_institution",
                description="Save a potential institution for collaboration. Call this for each institution found.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "name": types.Schema(type=types.Type.STRING, description="Institution name (e.g., 'ETH Zürich', 'LUT University')"),
                        "department": types.Schema(type=types.Type.STRING, description="Relevant department or school"),
                        "country": types.Schema(type=types.Type.STRING, description="Country where the institution is located"),
                        "city": types.Schema(type=types.Type.STRING, description="City where the institution is located"),
                        "relevance_score": types.Schema(type=types.Type.INTEGER, description="Relevance to user's research (1-5). Be critical: 5=world-leading in exact area, 4=strong program, 3=relevant but not specialized, 2=tangential, 1=weak fit"),
                        "reason": types.Schema(type=types.Type.STRING, description="Why this institution is a good match"),
                        "key_groups": types.Schema(type=types.Type.STRING, description="Key research groups or centers"),
                    },
                    required=["name", "country", "relevance_score", "reason"]
                )
            )

            institutions = self._run_extraction_loop(
                system_instruction=system_instruction,
                user_message=user_message,
                save_func=save_institution_func,
                save_func_name="save_institution",
                on_save=on_save_institution,
                progress_message="Extracting institutions...",
                error_context="Institution Extraction"
            )

        # Sort by relevance score
        institutions.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        return institutions

    def search_broad(self, profile: str, focus_areas: Optional[list] = None,
                     region: Optional[str] = None, max_institutions: int = 5,
                     max_turns: int = 10) -> list:
        """
        Broad search: Discover institutions first, then search each for collaborators.
        """
        model_info = f"Search Model: {self.model_name}\nProcessing Model: {self.processing_model_name}" \
            if self.processing_model_name and self.processing_model_name != self.model_name \
            else f"Model: {self.model_name}"
        self.console.print(Panel(
            f"[bold]Starting broad collaborator search[/bold]\n\n"
            f"Mode: Institution Discovery + Multi-Institution Search\n"
            f"Max Institutions: {max_institutions}\n"
            f"Region: {region or 'Worldwide'}\n"
            f"{model_info}",
            title="CollAgent - Broad Search",
            border_style="blue"
        ))

        # Phase 0: Discover institutions
        inst_text = self.discover_institutions(
            profile=profile,
            focus_areas=focus_areas,
            region=region,
            max_turns=max(3, max_turns // 4)
        )

        if not inst_text:
            self.console.print("[yellow]No institution data gathered.[/yellow]")
            return []

        # Extract institutions
        institutions = self.extract_institutions(inst_text, profile)

        if not institutions:
            self.console.print("[yellow]No institutions extracted.[/yellow]")
            return []

        # Limit institutions
        institutions = institutions[:max_institutions]
        self.searched_institutions = institutions  # Store for report

        self.console.print(f"\n[bold]Will search {len(institutions)} institutions in parallel:[/bold]")
        for inst in institutions:
            self.console.print(f"  • {inst.get('name', 'Unknown')} ({inst.get('country', 'Unknown')})")

        # Search institutions in parallel (limit to 5 concurrent to avoid rate limits)
        turns_per_inst = max(3, max_turns // len(institutions))

        def search_institution(inst_data):
            inst_name = inst_data.get("name", "Unknown Institution")
            # Set section for this thread's messages
            if hasattr(self.console, 'set_section'):
                self.console.set_section(inst_name)
            self.console.print(f"\n[bold blue]━━━ Searching: {inst_name} ━━━[/bold blue]")
            try:
                self.search(
                    profile=profile,
                    institution=inst_name,
                    focus_areas=focus_areas,
                    max_turns=turns_per_inst
                )
            finally:
                # Clear section when done
                if hasattr(self.console, 'set_section'):
                    self.console.set_section(None)
            return inst_name

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(search_institution, inst) for inst in institutions]
            for future in concurrent.futures.as_completed(futures):
                try:
                    inst_name = future.result()
                    self.console.print(f"[dim]Completed: {inst_name}[/dim]")
                except Exception as e:
                    self.console.print(f"[red]Search error: {e}[/red]")

        self.console.print(f"\n[green bold]Broad search complete![/green bold]")
        self.console.print(f"[dim]Searched {len(institutions)} institutions, found {len(self.collaborators)} potential collaborators.[/dim]")

        return self.collaborators

    def search(self, profile: str, institution: Optional[str] = None,
               focus_areas: Optional[list] = None, max_turns: int = 10) -> list:
        """
        Search for collaborators using two-phase approach.
        Phase 1: Google Search grounding for research
        Phase 2: Function calling for structured extraction
        """
        model_info = f"Search Model: {self.model_name}\nProcessing Model: {self.processing_model_name}" \
            if self.processing_model_name and self.processing_model_name != self.model_name \
            else f"Model: {self.model_name}"
        self.console.print(Panel(
            f"[bold]Starting collaborator search[/bold]\n\n"
            f"Target: {institution or 'Open search'}\n"
            f"{model_info}\n"
            f"Method: Two-phase (Search → Extract)",
            title="CollAgent",
            border_style="green"
        ))

        # Phase 1: Research with Google Search
        research_text = self.phase1_research(
            profile=profile,
            institution=institution,
            focus_areas=focus_areas,
            max_turns=max_turns // 2
        )

        if not research_text:
            self.console.print("[yellow]No research data gathered.[/yellow]")
            return []

        # Phase 2: Extract structured data
        collaborators = self.phase2_extract(research_text, profile)

        self.console.print(f"\n[green bold]Search complete![/green bold]")
        self.console.print(f"[dim]Found {len(collaborators)} potential collaborators.[/dim]")

        return collaborators

    def generate_report(self, output_file: Optional[str] = None) -> str:
        """Generate a markdown report of findings"""

        if not self.collaborators:
            return "No collaborators found."

        sorted_collabs = sorted(
            self.collaborators,
            key=lambda x: x.get("alignment_score", 0),
            reverse=True
        )

        report = f"""# Collaborator Search Report

Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}
Model: Google Gemini ({self.model_name})
Search: Google Search (built-in grounding)

## Summary

Found **{len(sorted_collabs)}** potential collaborators"""

        # Add institution summary if broad search was used
        if self.searched_institutions:
            report += f" across **{len(self.searched_institutions)}** institutions"
        report += ".\n\n"

        # Show institutions searched (if broad mode)
        if self.searched_institutions:
            report += "### Institutions Searched\n\n"
            for inst in self.searched_institutions:
                score = inst.get("relevance_score", 0)
                stars = "★" * score + "☆" * (5 - score)
                inst_name = inst.get("name", "Unknown")
                country = inst.get("country", "")
                reason = inst.get("reason", "")
                report += f"- **{inst_name}** ({country}) - Relevance: {stars}\n"
                if reason:
                    report += f"  - {reason}\n"
            report += "\n"

        report += "---\n\n"

        # Group collaborators by institution if broad search was used
        if self.searched_institutions:
            # Create groups by institution
            by_institution = {}
            for c in sorted_collabs:
                inst = c.get("institution", "Unknown")
                if inst not in by_institution:
                    by_institution[inst] = []
                by_institution[inst].append(c)

            report += "## Collaborators by Institution\n\n"

            collab_num = 1
            for inst_name, collabs in by_institution.items():
                # Find institution info
                inst_info = next(
                    (i for i in self.searched_institutions if i.get("name", "") == inst_name),
                    None
                )
                inst_country = inst_info.get("country", "") if inst_info else ""

                report += f"### {inst_name}"
                if inst_country:
                    report += f" ({inst_country})"
                report += f"\n\n*{len(collabs)} collaborator(s) found*\n\n"

                for c in collabs:
                    score = c.get("alignment_score", 0)
                    stars = "★" * score + "☆" * (5 - score)

                    report += f"""#### {collab_num}. {c.get("name", "Unknown")}

**Alignment:** {stars} ({score}/5)

| Field | Details |
|-------|---------|
| Position | {c.get("position", "N/A")} |
| Email | {c.get("email", "N/A")} |

**Research Focus:** {c.get("research_focus", "N/A")}

**Why This Match:** {c.get("alignment_reasons", "N/A")}

**Suggested Collaboration:** {c.get("collaboration_angle", "N/A")}

**Key Publications:** {c.get("key_publications", "N/A")}

---

"""
                    collab_num += 1

        else:
            # Single institution mode - original flat list
            report += "## Top Matches\n\n"

            for i, c in enumerate(sorted_collabs, 1):
                score = c.get("alignment_score", 0)
                stars = "★" * score + "☆" * (5 - score)

                report += f"""### {i}. {c.get("name", "Unknown")}

**Alignment:** {stars} ({score}/5)

| Field | Details |
|-------|---------|
| Position | {c.get("position", "N/A")} |
| Institution | {c.get("institution", "N/A")} |
| Email | {c.get("email", "N/A")} |

**Research Focus:** {c.get("research_focus", "N/A")}

**Why This Match:** {c.get("alignment_reasons", "N/A")}

**Suggested Collaboration:** {c.get("collaboration_angle", "N/A")}

**Key Publications:** {c.get("key_publications", "N/A")}

---

"""

        if output_file:
            with open(output_file, "w") as f:
                f.write(report)
            self.console.print(f"[green]Report saved to {output_file}[/green]")

        return report


# HTML Report Template for web results (double braces to escape for .format())
HTML_REPORT_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CollAgent Search Results</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            color: #e4e4e7;
            min-height: 100vh;
            padding: 2rem;
        }}
        .container {{ max-width: 900px; margin: 0 auto; }}
        h1 {{
            text-align: center;
            font-size: 2rem;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 1.5rem;
        }}
        .summary {{
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 2rem;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        .section-header {{
            font-size: 1.25rem;
            color: #667eea;
            margin: 2rem 0 1rem 0;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid rgba(102, 126, 234, 0.3);
        }}
        .top-badge {{
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 0.25rem 0.75rem;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 600;
            margin-left: 0.5rem;
            vertical-align: middle;
        }}
        .collaborator {{
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        .collaborator.top-candidate {{
            border: 1px solid rgba(102, 126, 234, 0.4);
            background: rgba(102, 126, 234, 0.08);
        }}
        .collaborator h3 {{
            color: #667eea;
            margin-bottom: 0.5rem;
        }}
        .score {{
            color: #fbbf24;
            font-size: 1.1rem;
            margin-bottom: 0.5rem;
        }}
        .field {{ margin-bottom: 0.5rem; }}
        .field-label {{ color: #a1a1aa; font-size: 0.875rem; }}
        .field-value {{ color: #e4e4e7; }}
        table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; }}
        th, td {{ padding: 0.5rem; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.1); }}
        th {{ color: #a1a1aa; }}
        td a {{ color: #818cf8; text-decoration: none; }}
        td a:hover {{ color: #a5b4fc; text-decoration: underline; }}
        .btn-find-page {{
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white !important;
            text-decoration: none;
            border: none;
            padding: 0.4rem 0.8rem;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.8rem;
            font-weight: 500;
            transition: all 0.2s ease;
        }}
        .btn-find-page:hover {{
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
            color: white !important;
            text-decoration: none;
        }}
        .website-cell .found-link {{
            color: #818cf8;
            text-decoration: none;
        }}
        .website-cell .found-link:hover {{
            color: #a5b4fc;
            text-decoration: underline;
        }}
        .website-cell .error {{
            color: #f87171;
            font-size: 0.85rem;
        }}
        hr {{ border: none; border-top: 1px solid rgba(255,255,255,0.1); margin: 1rem 0; }}
        .timestamp {{ color: #71717a; font-size: 0.875rem; text-align: center; margin-top: 2rem; }}

        /* Collapsible styles */
        .collapsible-header {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 1rem 1.5rem;
            margin: 2rem 0 1rem 0;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: all 0.3s ease;
        }}
        .collapsible-header:hover {{
            background: rgba(255, 255, 255, 0.08);
        }}
        .collapsible-header h3 {{
            margin: 0;
            color: #a1a1aa;
            font-size: 1rem;
        }}
        .collapsible-icon {{
            font-size: 1.25rem;
            color: #667eea;
            transition: transform 0.3s ease;
        }}
        .collapsible-header.active .collapsible-icon {{
            transform: rotate(180deg);
        }}
        .collapsible-content {{
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.5s ease-out;
        }}
        .collapsible-content.active {{
            max-height: none;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>CollAgent Search Results</h1>
        {content}
        <p class="timestamp">Generated: {timestamp}</p>
    </div>
    <script>
        document.querySelectorAll('.collapsible-header').forEach(header => {{
            header.addEventListener('click', () => {{
                header.classList.toggle('active');
                const content = header.nextElementSibling;
                content.classList.toggle('active');
            }});
        }});
    </script>
</body>
</html>
'''
