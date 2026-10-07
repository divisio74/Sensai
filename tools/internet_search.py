import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def internet_search(query):
    api_key = os.getenv("LANGSEARCH_API_KEY")
    if not api_key:
        raise RuntimeError("LANGSEARCH_API_KEY is not set")

    request = Request(
        "https://api.langsearch.com/v1/web-search",
        data=json.dumps({
            "query": query,
            "count": 5,
            "contents": {"text": True},
            "freshness": "noLimit",
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

    sources = result["data"]["webPages"]["value"]
    for source in sources:
        print(f"- {source['name']}: {source['url']}")
    return sources
