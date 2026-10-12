# Sensia guide

Test document for the RAG. It contains precise information about the project that the model cannot know without reading this file.

## Starting Sensia

Sensia is started with the command `python3 main.py`.
The default model is `qwen2.5:3b`. Another model can be chosen with the `--model` option.
The default Ollama address is `http://localhost:11434/api/chat`. It can be changed with the `--url` option.

At startup, Sensia checks that the Ollama server responds and that the model exists. If not, the program prints an error and stops.

## Commands

- `quit`: exits Sensia.
- `/code <task>`: Sensia writes Python code for the task, runs it in the sandbox and fixes it if there is an error.
- `/index`: reads the documents in the `knowledge/` folder and builds the search index.
- `/rag <question>`: Sensia answers using the documents in the `knowledge/` folder.

## The sandbox

The sandbox runs the generated code in a separate Python process.
Code that runs for more than 10 seconds is stopped automatically.
The correction loop makes at most 3 attempts. If the code fails 3 times, Sensia gives up and tells the user.
If the model proposes the same code twice, the loop detects it and asks the model to try a different strategy.

## The RAG

Documents must be placed in the `knowledge/` folder.
Only `.md`, `.txt` and `.py` files are read.
Documents are split into chunks of 500 characters, with an overlap of 100 characters.
The embedding model is `nomic-embed-text`. It weighs 274 MB.

## Error handling

If Ollama stops during an answer, Sensia prints a message and keeps running.
Pressing Ctrl+C during an answer only stops the current answer, not the program.
If Ollama does not respond for 120 seconds, the request is abandoned.
