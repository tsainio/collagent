"""
CollAgent - Agent Factory

Copyright (C) 2026 Tuomo Sainio
Licensed under AGPL-3.0
"""

import os
from typing import Optional

from .base import CollAgentBase
from .config import get_model_by_id, get_default_model, get_provider_config


def create_agent(model_id: Optional[str] = None, output_console=None) -> CollAgentBase:
    """
    Create an agent instance based on model configuration.

    Args:
        model_id: Model ID to use (uses default if not specified)
        output_console: Optional console for output

    Returns:
        Appropriate agent instance (CollAgentGoogle or CollAgentOpenAI)

    Raises:
        ValueError: If model not found or API key not set
    """
    # Get model configuration
    if model_id:
        model_config = get_model_by_id(model_id)
        if not model_config:
            raise ValueError(f"Unknown model: {model_id}")
    else:
        model_config = get_default_model()
        if not model_config:
            raise ValueError("No default model configured")

    provider = model_config.get("provider")
    provider_config = get_provider_config(provider)
    env_key = provider_config.get("env_key")

    if not env_key:
        raise ValueError(f"No env_key configured for provider: {provider}")

    api_key = os.environ.get(env_key)
    if not api_key:
        raise ValueError(f"{env_key} environment variable not set")

    # Import and instantiate the appropriate agent
    if provider == "google":
        from .core import CollAgentGoogle
        return CollAgentGoogle(api_key, model=model_config["id"], output_console=output_console)
    elif provider == "openai":
        from .openai_agent import CollAgentOpenAI
        return CollAgentOpenAI(api_key, model=model_config["id"], output_console=output_console)
    else:
        raise ValueError(f"Unknown provider: {provider}")
