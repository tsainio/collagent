"""
CollAgent - OpenAI Agent Implementation

Copyright (C) 2026 Tuomo Sainio
Licensed under AGPL-3.0
"""

import concurrent.futures
import json
from datetime import datetime
from typing import Optional

from openai import OpenAI
from rich.panel import Panel

from .base import CollAgentBase


class CollAgentOpenAI(CollAgentBase):
    """Research Collaborator Search Agent using OpenAI API with web search."""

    def __init__(self, api_key: str, model: str = "gpt-5.2", output_console=None):
        super().__init__(api_key, model, output_console)
        self.client = OpenAI(api_key=api_key)

    def _get_response_text(self, response) -> str:
        """Extract text from OpenAI Responses API response."""
        texts = []
        for item in response.output:
            if item.type == "message":
                for content in item.content:
                    if content.type == "output_text":
                        texts.append(content.text)
        return "\n".join(texts)

    def _get_citations(self, response) -> list:
        """Extract citations from response annotations."""
        citations = []
        for item in response.output:
            if item.type == "message":
                for content in item.content:
                    if hasattr(content, 'annotations') and content.annotations:
                        for ann in content.annotations:
                            if hasattr(ann, 'url_citation') and ann.url_citation:
                                citations.append(ann.url_citation.url)
        return citations

    def _run_web_search(self, system_instruction: str, user_message: str,
                        continue_message: str, max_turns: int,
                        phase_name: str, error_context: str) -> str:
        """
        Run a multi-turn web search using OpenAI Responses API.
        Returns accumulated research text.
        """
        accumulated_text = []
        last_response_length = 0
        previous_response_id = None

        for turn in range(1, max_turns + 1):
            self.console.print(f"[dim]{phase_name} turn {turn}/{max_turns}...[/dim]")

            try:
                request_params = {
                    "model": self.model_name,
                    "tools": [{"type": "web_search_preview"}],
                    "instructions": system_instruction,
                }

                # GPT-5.2 requires reasoning_effort for tool calls to work
                if "gpt-5" in self.model_name.lower():
                    request_params["reasoning"] = {"effort": "medium"}

                if previous_response_id:
                    # Continue conversation using previous response ID
                    request_params["previous_response_id"] = previous_response_id
                    request_params["input"] = continue_message
                else:
                    # First turn
                    request_params["input"] = user_message

                response = self.client.responses.create(**request_params)
                previous_response_id = response.id

            except Exception as e:
                if self._handle_api_error(e, error_context):
                    return ""  # Fatal error - abort completely
                break

            response_text = self._get_response_text(response)
            if response_text:
                accumulated_text.append(response_text)
                if len(response_text) > 400 and hasattr(self.console, 'record'):
                    self.console.print(f"[dim]{response_text[:400]}...[/dim]", _record=False)
                    self.console.record(f"[dim]{response_text}[/dim]")
                else:
                    self.console.print(f"[dim]{response_text}[/dim]")

                # Check for stop phrase
                if "SEARCH COMPLETE" in response_text.upper():
                    self.console.print("[dim]Search complete signal received.[/dim]")
                    break

                # Check for diminishing returns
                if last_response_length > 0 and len(response_text) < last_response_length * 0.3:
                    self.console.print("[dim]Diminishing returns detected, stopping.[/dim]")
                    break

                last_response_length = len(response_text)
            else:
                self.console.print("[dim]No text in response.[/dim]")
                if accumulated_text:
                    self.console.print("[dim]Stopping - already have research data.[/dim]")
                    break

        return "\n\n".join(accumulated_text)

    def _run_extraction_loop(self, system_instruction: str, user_message: str,
                              save_func_schema: dict, save_func_name: str,
                              on_save: callable, progress_message: str,
                              error_context: str, max_turns: int = 5) -> list:
        """
        Run a function-calling extraction loop using Responses API.

        Args:
            system_instruction: System prompt for extraction
            user_message: User prompt with research text
            save_func_schema: JSON schema for the save function
            save_func_name: Name of the save function to match
            on_save: Callback(args) -> (display_name, score, result_message)
            progress_message: Message to show during extraction
            error_context: Context for error messages
            max_turns: Maximum extraction turns

        Returns:
            List of extracted items
        """
        finish_func_schema = {
            "type": "function",
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

        # Convert save_func_schema to Responses API format
        save_func = save_func_schema.get("function", save_func_schema)
        save_tool = {
            "type": "function",
            "name": save_func.get("name", save_func_name),
            "description": save_func.get("description", ""),
            "parameters": save_func.get("parameters", {})
        }

        tools = [save_tool, finish_func_schema]
        items = []

        # Initial request
        self.console.print(f"[dim]{progress_message}[/dim]")
        try:
            request_params = {
                "model": self.model_name,
                "tools": tools,
                "instructions": system_instruction,
                "input": user_message,
            }
            # GPT-5.2 requires reasoning_effort for tool calls to work
            if "gpt-5" in self.model_name.lower():
                request_params["reasoning"] = {"effort": "medium"}

            response = self.client.responses.create(**request_params)
        except Exception as e:
            self._handle_api_error(e, error_context)
            return items

        for turn in range(max_turns):
            # Process output items
            tool_calls_to_process = []
            finished = False

            for item in response.output:
                if item.type == "function_call":
                    tool_calls_to_process.append(item)

            if not tool_calls_to_process:
                # No function calls, model is done
                break

            # Process each function call and build results
            tool_outputs = []
            for tc in tool_calls_to_process:
                name = tc.name
                try:
                    args = json.loads(tc.arguments) if tc.arguments else {}
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

                tool_outputs.append({
                    "type": "function_call_output",
                    "call_id": tc.call_id,
                    "output": json.dumps({"result": result})
                })

            if finished:
                break

            # Submit tool outputs and get next response
            if tool_outputs:
                self.console.print(f"[dim]{progress_message}[/dim]")
                try:
                    request_params = {
                        "model": self.model_name,
                        "previous_response_id": response.id,
                        "input": tool_outputs,
                        "tools": tools,
                        "instructions": system_instruction,
                    }
                    # GPT-5.2 requires reasoning_effort for tool calls to work
                    if "gpt-5" in self.model_name.lower():
                        request_params["reasoning"] = {"effort": "medium"}

                    response = self.client.responses.create(**request_params)
                except Exception as e:
                    self._handle_api_error(e, "submitting tool outputs")
                    break

        return items

    def phase1_research(self, profile: str, institution: Optional[str] = None,
                        focus_areas: Optional[list] = None, max_turns: int = 10) -> str:
        """
        Phase 1: Use web search to research potential collaborators.
        Returns accumulated research text.
        """
        search_method = "external search tool" if self.search_tool else "web search"
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

        return self._run_web_search(
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

        save_collaborator_schema = {
            "type": "function",
            "function": {
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
        }

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
        if self.processing_provider in ("openai_compatible",):
            self._run_chat_completions_extraction(
                system_instruction=system_instruction,
                user_message=user_message,
                save_func_schema=save_collaborator_schema,
                save_func_name="save_collaborator",
                on_save=on_save_collaborator,
                progress_message="Extracting data...",
                error_context="Phase 2"
            )
        elif self.processing_provider == "openai":
            # Use Responses API with the processing model
            orig_model = self.model_name
            orig_client = self.client
            self.model_name = self.processing_model_name
            self.client = self.processing_client

            try:
                self._run_extraction_loop(
                    system_instruction=system_instruction,
                    user_message=user_message,
                    save_func_schema=save_collaborator_schema,
                    save_func_name="save_collaborator",
                    on_save=on_save_collaborator,
                    progress_message="Extracting data...",
                    error_context="Phase 2"
                )
            finally:
                self.model_name = orig_model
                self.client = orig_client
        elif self.processing_provider == "google":
            self._run_genai_extraction(
                system_instruction=system_instruction,
                user_message=user_message,
                save_func_schema=save_collaborator_schema,
                save_func_name="save_collaborator",
                on_save=on_save_collaborator,
                progress_message="Extracting data...",
                error_context="Phase 2"
            )
        else:
            # Default: use native Responses API extraction with main model
            self._run_extraction_loop(
                system_instruction=system_instruction,
                user_message=user_message,
                save_func_schema=save_collaborator_schema,
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
        Uses web search to find relevant universities and research groups.
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

        return self._run_web_search(
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

        save_institution_schema = {
            "type": "function",
            "function": {
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
        }

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

        # Route to appropriate extraction method based on processing provider
        if self.processing_provider in ("openai_compatible",):
            institutions = self._run_chat_completions_extraction(
                system_instruction=system_instruction,
                user_message=user_message,
                save_func_schema=save_institution_schema,
                save_func_name="save_institution",
                on_save=on_save_institution,
                progress_message="Extracting institutions...",
                error_context="Institution Extraction"
            )
        elif self.processing_provider == "openai":
            # Use Responses API with the processing model
            orig_model = self.model_name
            orig_client = self.client
            self.model_name = self.processing_model_name
            self.client = self.processing_client

            try:
                institutions = self._run_extraction_loop(
                    system_instruction=system_instruction,
                    user_message=user_message,
                    save_func_schema=save_institution_schema,
                    save_func_name="save_institution",
                    on_save=on_save_institution,
                    progress_message="Extracting institutions...",
                    error_context="Institution Extraction"
                )
            finally:
                self.model_name = orig_model
                self.client = orig_client
        elif self.processing_provider == "google":
            institutions = self._run_genai_extraction(
                system_instruction=system_instruction,
                user_message=user_message,
                save_func_schema=save_institution_schema,
                save_func_name="save_institution",
                on_save=on_save_institution,
                progress_message="Extracting institutions...",
                error_context="Institution Extraction"
            )
        else:
            # Default: use native Responses API extraction with main model
            institutions = self._run_extraction_loop(
                system_instruction=system_instruction,
                user_message=user_message,
                save_func_schema=save_institution_schema,
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
        self.searched_institutions = institutions

        self.console.print(f"\n[bold]Will search {len(institutions)} institutions in parallel:[/bold]")
        for inst in institutions:
            self.console.print(f"  • {inst.get('name', 'Unknown')} ({inst.get('country', 'Unknown')})")

        # Search institutions in parallel (limit to 5 concurrent to avoid rate limits)
        turns_per_inst = max(3, max_turns // len(institutions))

        def search_institution(inst_data):
            inst_name = inst_data.get("name", "Unknown Institution")
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
        Phase 1: Web search for research
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

        # Phase 1: Research with web search
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
        """Generate a markdown report of findings."""
        if not self.collaborators:
            return "No collaborators found."

        sorted_collabs = sorted(
            self.collaborators,
            key=lambda x: x.get("alignment_score", 0),
            reverse=True
        )

        report = f"""# Collaborator Search Report

Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}
Model: OpenAI ({self.model_name})
Search: Web Search (OpenAI Responses API)

## Summary

Found **{len(sorted_collabs)}** potential collaborators"""

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
            by_institution = {}
            for c in sorted_collabs:
                inst = c.get("institution", "Unknown")
                if inst not in by_institution:
                    by_institution[inst] = []
                by_institution[inst].append(c)

            report += "## Collaborators by Institution\n\n"

            collab_num = 1
            for inst_name, collabs in by_institution.items():
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
