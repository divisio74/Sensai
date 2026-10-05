import json
from urllib.request import Request, urlopen

def internet_search(query):
    request = Request(
        "https://api.langsearch.com/v1/web-search",
        data=json.dumps({
            "query": query,
            "count": 5, "contents": {"text": True}, "freshness": "noLimit"
        }).encode(),
        headers={
            "Authorization": "Bearer LANGSEARCH_API_KEY",
            "Content-Type": "application/json"
        }
    )
    with urlopen(request, timeout=30) as response:
        result = json.load(response)
    print("Input tokens:", result["usage"]["input_tokens"])
    print("Output tokens:", result["usage"]["output_tokens"])
    for source in result["data"]["webPages"]["value"]:
        print(source["name"], source["url"])
    return result["data"]["webPages"]["value"]
