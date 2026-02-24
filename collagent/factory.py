"""
CollAgent - Agent Factory

Copyright (C) 2026 Tuomo Sainio
Licensed under AGPL-3.0
"""

import os
from typing import Optional

from .base import CollAgentBase
from .config import get_model_by_id, get_default_model, get_provider_config


def create_agent(model_id: Optional[str] = None, output_console=None,
                 base_url: Optional[str] = None,
                 processing_model_id: Optional[str] = None,
                 processing_base_url: Optional[str] = None,
                 processing_api_key: Optional[str] = None,
                 search_tool_name: Optional[str] = None,
                 search_tool_api_key: Optional[str] = None) -> CollAgentBase:
    """
    Create an agent instance based on model configuration.

    Args:
        model_id: Model ID to use (uses default if not specified)
        output_console: Optional console for output
        processing_model_id: Optional separate model for extraction
        processing_base_url: Base URL for processing model (implies openai_compatible)
        processing_api_key: API key for processing model
        search_tool_name: External search tool name (e.g., "tavily", "brave")
        search_tool_api_key: API key for external search tool

    Returns:
        Appropriate agent instance (CollAgentGoogle or CollAgentOpenAI)

    Raises:
        ValueError: If model not found or API key not set
    """
    # Get model configuration
    if base_url:
        # Custom openai_compatible model (e.g. local Ollama)
        model_config = {"id": model_id or "default", "provider": "openai_compatible", "base_url": base_url}
        provider = "openai_compatible"
        provider_config = {}
    elif model_id:
        model_config = get_model_by_id(model_id)
        if not model_config:
            raise ValueError(f"Unknown model: {model_id}")
        provider = model_config.get("provider")
        provider_config = get_provider_config(provider)
    else:
        model_config = get_default_model()
        if not model_config:
            raise ValueError("No default model configured")
        provider = model_config.get("provider")
        provider_config = get_provider_config(provider)

    # For openai_compatible, base_url comes from model config or parameter
    if provider == "openai_compatible":
        model_base_url = base_url or model_config.get("base_url")
        if not model_base_url:
            raise ValueError(f"No base_url configured for model: {model_id}")
        api_key = os.environ.get("OPENAI_API_KEY", "ollama")
    else:
        env_key = provider_config.get("env_key")
        if not env_key:
            raise ValueError(f"No env_key configured for provider: {provider}")
        api_key = os.environ.get(env_key)
        if not api_key:
            raise ValueError(f"{env_key} environment variable not set")

    # Import and instantiate the appropriate agent
    if provider == "google":
        from .core import CollAgentGoogle
        agent = CollAgentGoogle(api_key, model=model_config["id"], output_console=output_console)
    elif provider == "openai":
        from .openai_agent import CollAgentOpenAI
        agent = CollAgentOpenAI(api_key, model=model_config["id"], output_console=output_console)
    elif provider == "openai_compatible":
        # Use OpenAI agent with custom base_url
        from .openai_agent import CollAgentOpenAI
        from openai import OpenAI
        compat_client = OpenAI(base_url=model_base_url, api_key=api_key)
        agent = CollAgentOpenAI(api_key, model=model_config["id"], output_console=output_console)
        agent.client = compat_client
        # Also set as processing model so extraction uses Chat Completions
        # (openai_compatible models don't support the Responses API)
        agent.set_processing_model("openai_compatible", model_config["id"], client=compat_client)
    else:
        raise ValueError(f"Unknown provider: {provider}")

    # Configure processing model if specified
    if processing_model_id or processing_base_url:
        _configure_processing_model(agent, processing_model_id, processing_base_url,
                                     processing_api_key, provider, api_key)

    # Configure search tool if specified
    if search_tool_name:
        _configure_search_tool(agent, search_tool_name, search_tool_api_key)

    return agent


def _configure_processing_model(agent: CollAgentBase, processing_model_id: Optional[str],
                                 processing_base_url: Optional[str],
                                 processing_api_key: Optional[str],
                                 main_provider: str, main_api_key: str):
    """Configure a separate processing model on the agent."""

    if processing_base_url:
        # openai_compatible processing
        from openai import OpenAI
        proc_api_key = processing_api_key or "ollama"
        proc_client = OpenAI(base_url=processing_base_url, api_key=proc_api_key)
        proc_model = processing_model_id or "default"
        agent.set_processing_model("openai_compatible", proc_model, client=proc_client)
        return

    if not processing_model_id:
        return

    # Look up processing model config
    proc_config = get_model_by_id(processing_model_id)
    if proc_config:
        proc_provider = proc_config.get("provider")
    else:
        # Assume same provider as main model
        proc_provider = main_provider

    if proc_provider == "google":
        from google import genai
        proc_api_key = processing_api_key or os.environ.get("GOOGLE_API_KEY", main_api_key)
        proc_client = genai.Client(api_key=proc_api_key)
        agent.set_processing_model("google", processing_model_id, client=proc_client)

    elif proc_provider == "openai":
        from openai import OpenAI
        proc_api_key = processing_api_key or os.environ.get("OPENAI_API_KEY", main_api_key)
        proc_client = OpenAI(api_key=proc_api_key)
        agent.set_processing_model("openai", processing_model_id, client=proc_client)

    elif proc_provider == "openai_compatible":
        from openai import OpenAI
        proc_base_url = proc_config.get("base_url") if proc_config else None
        if not proc_base_url:
            raise ValueError(f"No base_url for processing model: {processing_model_id}")
        proc_api_key = processing_api_key or "ollama"
        proc_client = OpenAI(base_url=proc_base_url, api_key=proc_api_key)
        agent.set_processing_model("openai_compatible", processing_model_id, client=proc_client)

    else:
        raise ValueError(f"Unknown processing model provider: {proc_provider}")


def _configure_search_tool(agent: CollAgentBase, search_tool_name: str,
                            search_tool_api_key: Optional[str]):
    """Configure an external search tool on the agent."""
    from .search_tools import create_search_tool
    from .config import get_search_tool_config

    # Get API key from parameter, environment, or config
    if not search_tool_api_key:
        tool_config = get_search_tool_config(search_tool_name)
        env_key = tool_config.get("env_key")
        if env_key:
            search_tool_api_key = os.environ.get(env_key)
        if not search_tool_api_key:
            raise ValueError(
                f"No API key for search tool '{search_tool_name}'. "
                f"Set --search-tool-api-key or {env_key} environment variable."
            )

    tool = create_search_tool(search_tool_name, search_tool_api_key)

    # For tool-based search, we need an OpenAI-compatible client for the search LLM.
    # For OpenAI agents, use the existing client. For Google agents, leave client as None
    # (the Google agent's overridden _run_tool_based_search will use genai function calling).
    search_client = None
    search_model = None

    from .openai_agent import CollAgentOpenAI
    if isinstance(agent, CollAgentOpenAI):
        search_client = agent.client
        search_model = agent.model_name

    agent.set_search_tool(tool, client=search_client, model_name=search_model)
