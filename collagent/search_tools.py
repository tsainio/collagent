"""
CollAgent - External Search Tool Plugins

Copyright (C) 2026 Tuomo Sainio
Licensed under AGPL-3.0
"""

import gzip
import json
from abc import ABC, abstractmethod
from urllib.request import Request, urlopen
from urllib.parse import urlencode


class SearchTool(ABC):
    """Abstract base class for external search tools."""

    @abstractmethod
    def search(self, query: str, max_results: int = 10) -> list:
        """
        Search the web and return results.

        Args:
            query: Search query string
            max_results: Maximum number of results to return

        Returns:
            List of dicts with keys: title, url, content
        """
        pass


class TavilySearch(SearchTool):
    """Search using Tavily REST API."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def search(self, query: str, max_results: int = 10) -> list:
        payload = json.dumps({
            "query": query,
            "max_results": max_results,
            "api_key": self.api_key,
        }).encode("utf-8")

        req = Request(
            "https://api.tavily.com/search",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        results = []
        for item in data.get("results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "content": item.get("content", ""),
            })
        return results


class BraveSearch(SearchTool):
    """Search using Brave Search REST API."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def search(self, query: str, max_results: int = 10) -> list:
        params = urlencode({"q": query, "count": min(max_results, 20)})
        url = f"https://api.search.brave.com/res/v1/web/search?{params}"

        req = Request(
            url,
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": self.api_key,
            },
        )

        with urlopen(req, timeout=30) as resp:
            raw = resp.read()
            if resp.headers.get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
            data = json.loads(raw.decode("utf-8"))

        results = []
        for item in data.get("web", {}).get("results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "content": item.get("description", ""),
            })
        return results


# Registry of available search tools
SEARCH_TOOLS = {
    "tavily": TavilySearch,
    "brave": BraveSearch,
}


def create_search_tool(name: str, api_key: str) -> SearchTool:
    """
    Create a search tool instance by name.

    Args:
        name: Search tool name (e.g., "tavily", "brave")
        api_key: API key for the search service

    Returns:
        SearchTool instance

    Raises:
        ValueError: If search tool name is unknown
    """
    cls = SEARCH_TOOLS.get(name)
    if cls is None:
        available = ", ".join(SEARCH_TOOLS.keys())
        raise ValueError(f"Unknown search tool: {name}. Available: {available}")
    return cls(api_key)
