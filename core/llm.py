import requests
import json

def stream_chat(messages, model, url):
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
    }
    response = requests.post(url, json=payload, stream=True, timeout=(5, 120))
    response.raise_for_status()
    for line in response.iter_lines():
        if not line:
            continue
        chunk = json.loads(line)
        yield chunk["message"]["content"]

def chat(messages, model, url):
    full_reply = ""
    try:
        for morceau in stream_chat(messages, model, url):
            print(morceau, end="", flush=True)
            full_reply += morceau
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
        return full_reply or None

    print()
    return full_reply
