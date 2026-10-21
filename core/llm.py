import requests
import json

def chat(messages, model, url):
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
    }
    full_reply = ""
    try:
        response = requests.post(url, json=payload, stream=True, timeout=(5, 120))

        if response.status_code != 200:
            print("Bad url OR model ! : ", response.status_code)
            return None

        for line in response.iter_lines():
            if not line:
                continue
            chunk = json.loads(line)
            morceau = chunk["message"]["content"]
            print(morceau, end="", flush=True)
            full_reply += morceau
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
