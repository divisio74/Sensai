import argparse
import sys

import requests

from timepred.llm import OLLAMA_URL
from timepred.runner import run


def main():
    parser = argparse.ArgumentParser(description="Sensia: task duration prediction")
    parser.add_argument("task", help="the task to run")
    parser.add_argument("--model", default="qwen2.5:3b")
    parser.add_argument("--url", default=OLLAMA_URL)
    parser.add_argument("--fast", type=float, metavar="SECONDS", help="time budget in seconds")
    args = parser.parse_args()

    if args.fast is not None and args.fast <= 0:
        parser.error("--fast must be > 0")

    try:
        run(args.task, args.model, args.url, args.fast)
    except requests.exceptions.RequestException as error:
        print(f"Ollama error: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
