import requests
import json

from core.config import TIMEOUT, options

def stream_messages(messages, model, url, tools=None, usage=None):
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "options": options(usage),
    }
    if tools:
        payload["tools"] = tools
    response = requests.post(url, json=payload, stream=True, timeout=TIMEOUT)
    response.raise_for_status()
    for line in response.iter_lines():
        if not line:
            continue
        chunk = json.loads(line)
        # Ollama reports a failure during the answer as a chunk, after its 200 status
        if "error" in chunk:
            raise requests.exceptions.RequestException(chunk["error"])
        yield chunk["message"]

def stream_chat(messages, model, url, usage=None):
    for message in stream_messages(messages, model, url, usage=usage):
        yield message["content"]

def chat_with_tools(messages, model, url, tools=None, usage=None):
    full_reply = ""
    tool_calls = []
    try:
        for message in stream_messages(messages, model, url, tools, usage):
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
        print(f"\nOllama error: {e}")
        return None
    except KeyboardInterrupt:
        print("\n[interrupted]")
        return (full_reply, []) if full_reply else None

    print()
    return full_reply, tool_calls


def chat(messages, model, url, usage=None):
    result = chat_with_tools(messages, model, url, usage=usage)
    return result[0] if result else None
