import requests
import json

def stream_messages(messages, model, url, tools=None):
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
    }
    if tools:
        payload["tools"] = tools
    response = requests.post(url, json=payload, stream=True, timeout=(5, 120))
    response.raise_for_status()
    for line in response.iter_lines():
        if not line:
            continue
        chunk = json.loads(line)
        yield chunk["message"]

def stream_chat(messages, model, url):
    for message in stream_messages(messages, model, url):
        yield message["content"]

def chat_with_tools(messages, model, url, tools=None):
    full_reply = ""
    tool_calls = []
    try:
        for message in stream_messages(messages, model, url, tools):
            morceau = message["content"]
            print(morceau, end="", flush=True)
            full_reply += morceau
            tool_calls.extend(message.get("tool_calls") or [])
    except requests.exceptions.HTTPError as e:
        print("Bad url OR model ! : ", e.response.status_code)
        return None
    except requests.exceptions.Timeout:
            print("\nOllama stopped responding (timeout)")
            return None
    except (requests.exceptions.ChunkedEncodingError, requests.exceptions.ConnectionError):
        print("\nConnection lost with Ollama")
        return None
    except requests.exceptions.RequestException as e:
        print(f"\nInvalid request: {e}")
        return None
    except KeyboardInterrupt:
        print("\n[interrupted]")
        return (full_reply, []) if full_reply else None

    print()
    return full_reply, tool_calls


def chat(messages, model, url):
    result = chat_with_tools(messages, model, url)
    return result[0] if result else None
