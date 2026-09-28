import requests
import json

def chat(messages, model, url):
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
    }
    try:
        response = requests.post(url, json=payload, stream=True)
    except requests.exceptions.ConnectionError:
        print("Server non joignable")
        return None

    if response.status_code != 200:
        print("Bad url OR model ! : ", response.status_code)
        return None

    full_reply = ""
    for line in response.iter_lines():
        chunk = json.loads(line)
        morceau = chunk["message"]["content"]
        print(morceau, end="", flush=True)
        full_reply += morceau
    print()
    return full_reply
