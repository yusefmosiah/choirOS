
import os
import httpx
from typing import Optional, List, Dict, Any

class WebSearch:
    """Web search tool using Tavily API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("TAVILY_API_KEY")
        self.base_url = "https://api.tavily.com"

    async def search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """
        Execute a web search.

        Args:
            query: The search query.
            max_results: Maximum number of results to return.

        Returns:
            Dict containing 'results' (list of strings) or 'error'.
        """
        if not self.api_key:
            return {"error": "TAVILY_API_KEY not configured"}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/search",
                    json={
                        "api_key": self.api_key,
                        "query": query,
                        "search_depth": "basic",
                        "max_results": max_results,
                        "include_answer": True,
                        "include_domains": []
                    },
                    timeout=10.0
                )

                if response.status_code != 200:
                    return {"error": f"Search API returned {response.status_code}: {response.text}"}

                data = response.json()
                results = []

                # Add the direct answer if available
                if data.get("answer"):
                    results.append(f"Direct Answer: {data['answer']}")

                # Format individual results
                for result in data.get("results", []):
                    title = result.get("title", "No Title")
                    url = result.get("url", "")
                    content = result.get("content", "")
                    results.append(f"Title: {title}\nURL: {url}\nSnippet: {content}")

                return {
                    "results": results,
                    "raw": data # Keep raw for advanced usage if needed
                }

        except Exception as e:
            return {"error": f"Search failed: {str(e)}"}
