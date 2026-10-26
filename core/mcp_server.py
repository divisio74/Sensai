import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from mcp.server.fastmcp import FastMCP


MAX_RESULTS = 3
MAX_TEXT_CHARS = 2000

mcp = FastMCP("web-search")


@mcp.tool()
def web_search(query):
    api_key = os.getenv("LANGSEARCH_API_KEY")
    if not api_key:
        raise RuntimeError("LANGSEARCH_API_KEY is not set")

    request = Request(
        "https://api.langsearch.com/v1/web-search",
        data=json.dumps({
            "query": query,
            "count": MAX_RESULTS,
            "contents": {"text": True},
        }).encode(),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=10) as response:
            result = json.load(response)
    except HTTPError as error:
        raise RuntimeError(f"LangSearch returned HTTP {error.code}") from error
    except (URLError, TimeoutError) as error:
        raise RuntimeError(f"Unable to reach LangSearch: {error}") from error
    except (json.JSONDecodeError, ValueError) as error:
        raise RuntimeError("Invalid response from LangSearch") from error

    try:
        sources = result["data"]["webPages"]["value"]
    except (KeyError, TypeError):
        sources = []
    return json.dumps([
        {
            "name": source.get("name", ""),
            "url": source.get("url", ""),
            "text": (source.get("text") or "")[:MAX_TEXT_CHARS],
            "datePublished": source.get("datePublished", ""),
            "displayUrl": source.get("displayUrl", ""),
        }
        for source in sources[:MAX_RESULTS]
    ], ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()
