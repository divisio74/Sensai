# Sensia

A local AI assistant built on Ollama, usable from the terminal or a web page, with a
**self-correcting code agent**.

Sensia is a chatbot that can also *act*: given a task, it writes Python code, runs it in a
separate process, reads the real error output, and rewrites the code until it runs — or until
it recognises that it is going in circles.

No LLM framework is used. Every call to the model is a direct HTTP request to the Ollama API.

---

## Who it is for

A **developer working locally**, on their own laptop, usually without a GPU (the reference
machine is a Ryzen 5 5600H with 15 GB of RAM, CPU only). They want an assistant that:

- does not send their code or documents to an online service (everything runs on Ollama,
  except the web search, which is an explicit and documented exception);
- runs and checks the code it proposes instead of only writing it;
- answers questions about their own documentation;
- adapts to their hardware and habits: the time predictions of `/fast` learn from their own
  runs, and the profile remembers their preferences.

Typical context: a student or a developer coding in Python, who often repeats the same kinds
of tasks (small functions, emails, explanations) and works under time constraints.

## Features

| Feature (brief id) | Example | Details |
|---|---|---|
| CLI chatbot with streaming and history (B1) | `python3 main.py`, then any question | [Usage](#usage) |
| Self-correcting code agent, run in a subprocess (T2, A1) | `/code sort [3,1,2] without sorted()` | [The reflection loop](#the-reflection-loop) |
| RAG over local documents, with sources and a relevance threshold (R1, R2) | `/index`, then `/rag Which files are indexed?` | [RAG](#rag) |
| Web search chosen by the model, through an MCP server (T1, T3) | `What is new in Python this week?` | [Web search](#web-search-mcp) |
| Personas, switchable mid-session (A5) | `/persona dev` | [Persona and user profile](#persona-and-user-profile) |
| Persistent user profile and memory (M1) | `/remember I work in Python` | [Persona and user profile](#persona-and-user-profile) |
| Local accounts, one profile per account | `python3 main.py`, then your email | [Accounts](#accounts) |
| Tasks under a time budget, with live prediction (T5, A3) | `/fast 30 Write a reminder email for Monday` | [Time-budgeted tasks](#time-budgeted-tasks-fast) |
| Web interface (X1) | `python3 main.py --web` | [Web interface](#web-interface) |
| One configuration file, generation parameters per usage | edit `config.toml` | [Configuration](#configuration) |

Every feature has its user stories and acceptance criteria in
[`docs/user_stories/`](docs/user_stories/README.md).

---

## Requirements

- Python 3.11+ (`core/config.py` uses `tomllib`; developed on 3.12)
- [Ollama](https://ollama.com) running locally
- A LangSearch API key (optional, only the web search needs it)
- The packages of `requirements.txt`: `requests`, `python-dotenv`, `fastapi`, `uvicorn` and `mcp`
  (`main.py` imports all of them, even in the terminal)
- [Docker](https://docs.docker.com/engine/install/), usable without `sudo`, for the isolated code
  sandbox (without it, Sensia falls back to a local process and says so)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
ollama pull qwen2.5:3b
ollama pull nomic-embed-text
docker pull python:3.12-slim
cp .env.example .env   # then set LANGSEARCH_API_KEY in it
```

`main.py` and the test runner load `.env` with `python-dotenv`; the file is never committed.
Without a key, Sensia runs normally, but a web search returns an error to the model.

## Running

```bash
python3 main.py
python3 main.py --model qwen2.5:7b
python3 main.py --url http://other-host:11434/api/chat
python3 main.py --persona dev
python3 main.py --web
python3 main.py --help
```
`--model` and `--url` work the same way with `--web`. `--persona` must name an existing persona,
but it does not decide the persona of the session: after the login, the one of the account applies
(see [Accounts](#accounts)).

## Accounts

Both interfaces ask you to log in before the chat starts.

- **Terminal**: `python3 main.py` asks for your email, then your password. For an unknown email,
  it offers to create an account: it asks for a password, a persona and a few words about you.
- **Web**: the login page has the same fields. *Log in* uses the email and password, *Create
  account* uses every field. *Log out* is in the top bar of the chat.

Accounts live in `data/`, which is ignored by git: `data/users.json` holds the salted password
hashes (PBKDF2-SHA256) and the persona of each account, and `data/profiles/<email>.md` holds the
profile. There is no password reset.

## Configuration

Every tunable value lives in [`config.toml`](config.toml), grouped by feature and commented:
Ollama URLs and timeouts, RAG threshold and chunk size, code-loop iterations, sandbox mode,
timeout and Docker limits, web-search limits, web server port, `/fast` settings. `--model` and `--url` override
the file for one session.

Generation parameters are sent to Ollama as `options`, with one value per usage:

| Usage | Temperature | Why |
|---|---|---|
| conversation | 0.7 | some variety is welcome |
| code (`/code`, `code` steps of `/fast`) | 0.2 | stable, executable code |
| RAG answer | 0.1 | stick to the document extracts |
| RAG translation, `/fast` plan | 0 | deterministic, a single right answer |

`num_ctx` (4096) is the same for every usage: a different value would make Ollama reload the
model between two calls.

## User stories

The user stories, their acceptance criteria and the traceability table (feature → need →
story → code → verification) are in [`docs/user_stories/`](docs/user_stories/README.md).

## Demo

A replayable demo script, one coherent scenario through every feature (about 12 minutes), with
the exact commands, what to point at and what to do if a step fails:
[`docs/demo.md`](docs/demo.md).

## Tests

`tests/main.py` discovers and runs every `tests/test_*.py` file (with the `.env` loaded):

```bash
python3 tests/main.py
```

The former LangSearch integration test was removed when the web search moved to the MCP server.
Today, features are verified by the scenarios of the user stories and by the measurements
below (benchmarks, `/fast` bench).

## Usage

| Input | Effect | Web |
|---|---|---|
| any text | normal conversation, streamed token by token | ✅ |
| `/help` | lists the commands | ✅ |
| `/clear` | starts a new conversation | ✅ (also the *New chat* button) |
| `/undo` | removes the last question and answer | ✅ |
| `/retry` | generates a new answer to the last question | ✅ |
| `/index` | indexes the documents of `knowledge/documents/` | ✅ |
| `/rag <question>` | answers from the documents and lists the sources | ✅ |
| `/code <task>` | runs the self-correcting code agent on `<task>` (Python only) | ✅ (code and output shown) |
| `/fast <seconds> <task>` | runs a task within a time budget | ❌ terminal only |
| `/persona` | shows the current persona and the available ones | ✅ |
| `/persona <name>` | switches persona mid-conversation, the history is kept | ✅ |
| `/remember <fact>` | saves a fact in the user profile, used right away and in later sessions | ✅ |
| `quit` | exits | — |
| `Ctrl+C` / `Ctrl+D` | exits cleanly | — |

```
You: /code sort [3,1,2] without using sorted() and print the result
===== Attempt 1/3 =====
...
Succeeded in 1 attempt(s)
Output: [1, 2, 3]

You: explain what you just did
Sensia: This code implements a bubble sort...
```

The second turn matters: the result of `/code` is injected back into the chat history, so the
assistant can talk about code it produced in a *separate* conversation.

---

## Web interface

`python3 main.py --web` starts a small FastAPI server on http://127.0.0.1:4040, which serves a
login page, then the chat page. The page sends what the user types to the server, which answers
with the same code as the terminal.

```
browser (web/index.html, css, js)          web.py (FastAPI)
   POST /api/chat {text}  ───────────────►  handle_command()  ──► /help, /clear, /rag, /code...
   ◄─────────────── {output, messages}  (JSON)
                                             or stream_chat()  ──► Ollama
   ◄─────────────── the answer, piece by piece  (text stream)
   GET /api/history  ────────────────────►  the conversation (to redraw it after a reload)
   POST /api/login, /api/register, /api/logout  ──►  core/auth.py, opens or closes the session
```

### Technical decisions

**Same backend as the terminal.** The commands live in `core/commands.py` and *return* their text
instead of printing it. The terminal prints it, the web sends it to the page. Each command is
written once and behaves the same in both interfaces.

**The conversation is kept by the server.** Like `main.py`, `web.py` keeps one `messages` list.
The page only displays what the server returns, so `/undo` or `/clear` need no logic in
JavaScript, and reloading the page does not lose the conversation. Sensai is a local, single-user
assistant, so one list and one logged-in account at a time are enough.

**Streaming with a Python generator.** `stream_chat()` in `core/llm.py` *yields* each piece of
the answer as Ollama produces it. The terminal prints the pieces, the web sends them through a
FastAPI `StreamingResponse`, and the page reads them with `response.body.getReader()`. The answer
appears word by word instead of after several seconds of waiting. Commands still answer in JSON,
so the page knows which kind of answer it gets from the `Content-Type` header.

**HTML, CSS and plain JavaScript, no build step.** The page is served as-is by FastAPI: no
Node.js, no compilation, one command to start everything. TypeScript or React would have brought
type checking, at the cost of a toolchain far heavier than this interface needs.

### Limitations

- The answers of `/rag`, `/code` and `/retry` are shown at once, not streamed.
- Reloading the page while an answer is streaming loses that answer.
- In the web, the chat does not pass the MCP tools to the model, so it cannot search the web.
- `/fast` only works in the terminal: in the web, it is sent to the model as a plain message.
- All browser tabs share the same conversation and the same account. There is no session cookie:
  the server remembers one logged-in account, for every browser that reaches it. Logging in again
  replaces that account and starts a new conversation.
- Restarting the server logs out and loses the conversation.
- Command bubbles (`/help`, sources of `/rag`...) are saved by the browser, not by the server.

---

## Persona and user profile

The system prompt (the first message of the conversation) is built from two Markdown files:
who the assistant is, and who the user is.

```
persona/personas/<name>.md   the assistant: name (first "# " line), tone, role, values
data/profiles/<email>.md     the user: about me, preferences, remembered facts (local, not versioned)
```

```
messages[0] = {"role": "system", "content":
    <persona/personas/sensia.md>
    Today's date is 2026-10-29.
    About the user you are talking to. Their preferences below override your default behavior:
    <data/profiles/<email>.md>
}
```

```
You: /persona dev                    switch mid-conversation
Switched to SENSIA — developer mode (conversation kept)
You: /remember I am allergic to penicillin
Fact remembered.
```

User stories: [`docs/user_stories/persona.md`](docs/user_stories/persona.md) and
[`docs/user_stories/profile.md`](docs/user_stories/profile.md).

### Technical decisions

**Markdown files, not strings in the code.** A new assistant is a new file in
`persona/personas/`: no Python to change. The terminal name is read from the `# ` title, so the
name shown and the name the model is told are always the same. Markdown is plain text the model
reads as-is and a human edits easily, so no parser is needed.

**Switching only replaces `messages[0]`.** The persona is just the first message of the list.
`/persona` rebuilds it and leaves every other message untouched, so the new persona keeps the
whole conversation. `/remember` uses the same mechanism to refresh the profile immediately.

**One profile per account, outside git.** A profile holds personal information, so `data/` is
ignored by git. The profile is created with the account, from what the user wrote about themselves,
and is loaded at login.

**Two files: the assistant is read-only, the user profile is writable.** `/remember` only ever
writes to the profile of the account. If facts could be written into the persona file, a user could make
the assistant "remember" that it has no rules anymore, and that change would be permanent.

**Only listed personas can be loaded.** `/persona` checks the name against `list_personas()`
(the files of `persona/personas/`) before reading anything, so `/persona ../user` cannot load
another file as a persona.

**The profile comes after the persona, with a priority sentence.** The persona sets the default
behaviour, the profile adapts it to one user. The heading "About the user you are talking to"
tells the model the facts describe the user, not itself.

### Measurements

| Test (`llama3.2`, 4 runs) | Result |
|---|---|
| Profile preference that adds to the persona (a nickname: "Always call me ...") | applied 3/4 |
| Profile preference that contradicts the persona ("never give me the answer" vs "give short, working examples") | applied 0/4 |
| Fact given before `/persona dev`, asked after | remembered |
| Fact saved with `/remember`, asked after restarting Sensia | remembered |

### Limitations

- When the profile contradicts the persona, a small model follows the persona, even with the
  priority sentence: the profile works for preferences that complete the persona.
- Saying "remember that..." in plain language does nothing: `/remember` must be typed. A
  `remember` tool called by the model, like `web_search`, is the natural next step.
- The persona of a session is the one chosen when the account was created. `--persona` does not
  change it, and `/persona <name>` only lasts until the next login.
- Facts are appended at the end of the profile, so `## Remembered facts` must stay the last
  section, and the profile grows without limit in a 4096-token context.
- The profile is a local file: it is not shared between machines (it is ignored by git on
  purpose, since it holds personal information).

---

## RAG

```
/index    knowledge/documents/*.md|txt|py ──► chunks of 500 chars (overlap 100)
          ──► "search_document: <chunk>" ──► nomic-embed-text ──► knowledge/index/index.json

/rag q    q ──► translated to English ──► "search_query: <q>" ──► nomic-embed-text
          ──► cosine similarity with every chunk ──► top 3, kept only if ≥ 0.65
          ──► answer from the extracts only, in the language of q + "Sources: file - line - score"
```

```
You: /rag Which files are read by the RAG?
SENSIA: Only .md, .txt and .py files are read...
Sources: knowledge/documents/sensia_guide.md - line 27 - score 0.71
```

### Technical decisions

**Two models, two jobs.** `qwen2.5:3b` generates, `nomic-embed-text` (274 MB, 768 dimensions)
embeds. An embedding model is trained to place texts with the same meaning close together; a
generative model is not, and would be slower for this job.

**Asymmetric prefixes.** `nomic-embed-text` was trained with a task prefix: documents are
embedded as `search_document: ...` and questions as `search_query: ...`. Without them, a short
question and a long passage land in different regions of the space and scores drop.

**The question is translated to English before the embedding.** `nomic-embed-text` was trained
mostly on English text, so a French question is matched less well against English documents.
The generative model translates it first (temperature 0), and the answer prompt asks to reply
in the language of the original question, so the user never sees the translation.

**A threshold rather than "always the top 3".** Below 0.65, the chunks are not about the
question: injecting them anyway pushes the model to answer from irrelevant text. With no chunk
above the threshold, Sensia says so and does not generate an answer.

**The similarity is a cosine.** `nomic-embed-text` returns unit vectors (measured length:
1.0000), so their dot product *is* the cosine similarity, in [-1, 1], which is the scale the
0.65 threshold refers to.

**A JSON file, not a vector database.** The corpus is a few local documents: scoring every
chunk takes milliseconds, and a JSON file needs no extra service to install.

**The answer prompt only allows the extracts** and asks to say "I don't know" otherwise, with
a low temperature (0.1): the goal is to quote the documentation, not to improvise.

### Limitations

- No reranking and no metadata filtering (date, author).
- `/index` recomputes the whole index; the translation adds one model call per question.

---

## Web search (MCP)

The web search is a tool exposed by an MCP server (`core/mcp_server.py`, `web_search`, backed
by LangSearch). At start-up, `main.py` launches the server, lists its tools and passes them to
Ollama in the `tools` field. **The model decides by itself** to call the tool, with a native
tool call; Sensia runs it, returns the result as a `tool` message, and the model continues.

```
You: What is new in Python this week?
[Tool web_search: {'query': 'Python news', 'freshness': 'oneWeek'}]
SENSIA: This week, ... (dates) ... Sources: ...
```

### Technical decisions

**Native tool calls instead of a parsed JSON answer.** The first version asked the model to
answer with a JSON list of queries, and any answer that parsed as a JSON list triggered a
search, even when it was not meant to. A structured tool call removes that ambiguity.

**MCP rather than a Python function.** The tool follows a standard protocol: the same server
works with any MCP client, and Sensia can use other MCP servers without new code.

**Results are kept short and dated**: 3 results, each with its title, URL, publication date and
a summary of at most 2,000 characters, so they fit in a 4,096-token context. The persona asks
for a summary with dates, then the sources, never a bare list of links.

### Limitations

- **Privacy**: the query leaves the machine and goes to LangSearch, unlike the rest of Sensia.
  This is the only external call; it needs a key in `.env` and can be avoided by not asking
  for recent information.
- Each tool call starts the MCP server process again (about 1 s).
- Not available in the web interface yet.

---

## Time-budgeted tasks (`/fast`)

`/fast <seconds> <task>` runs a task within a time budget, predicts how long it will take
before and while it runs, and adapts to keep the budget.

```
You: /fast 8 Explain how HTTP caching works and compare it with a CDN for a beginner audience
Initial prediction (history only): 13s ± 6s = 1s of setup (...) + 12s of work
  ✂ answer shortened to ~65 words to fit the budget (~6s instead of ~12s)
  ⏳  47 tokens | p= 54% | -> 8±1s total
Budget: 8s -> kept
```

- **The plan**: the model only classifies the deliverable (`text`, `code`, `explanation`) with a
  JSON schema; the plan itself is built in Python (`write`, `code` [+ `explain`], `explain`,
  preceded by `research` when asked). Letting a 3B model plan freely produced five steps for an
  email and impossible actions ("send the email"); on 5 real tasks, the built plans took
  69 s instead of 243 s and delivered the expected result 5 times out of 5 instead of 3.
- **The prediction**: a Bayesian fusion of two estimates. The history estimate uses the speed
  of the machine (tokens/s) and the usual length of the answer, both learned from past runs;
  the live estimate extrapolates the elapsed time from the progress, measured in tokens while
  the model writes.
- **The budget**: checked before starting (`Continue anyway? [y/N]`), kept by asking for a
  shorter answer when the usual one does not fit, and checked again during generation, where
  the user can stop the task and keep what is done.
- **Code steps** go through `code_cycle`: the code is run and verified.

Measured (CPU only): budget kept in 20 of 24 runs, and the 4 overruns were all announced
before they happened; prediction error 37 % for a new task, 24 % for a task already run twice,
9 % when 90 % of the answer is written. Details: [`docs/user_stories/dev.md`](docs/user_stories/dev.md).

---

## Model choice and local benchmark

`qwen2.5:3b` (Q4_K_M) is the default because, on the reference laptop (CPU only), it is the
largest model that stays interactive:

| Model | Memory | Generation | Median answer | Code loop |
|---|---|---|---|---|
| qwen2.5:1.5b | 1.2 GB | 35.8 tokens/s | 8.6 s | 4/5 |
| **qwen2.5:3b** | **2.2 GB** | **18.2 tokens/s** | **20.1 s** | **4/5** |
| qwen2.5:7b | 5.1 GB | 8.4 tokens/s | 48.9 s | 5/5 |
| llama3.2:3b (other family) | 2.6 GB | 19.0 tokens/s | 6.0 s | 5/5 |

The 7B is a bit more reliable, but more than twice as slow: a typical answer takes almost a
minute, which breaks both the conversation and the `/fast` budgets. At the same size, Llama 3.2
runs at the same speed but writes answers three times shorter. The full analysis (speed
versus size, quantization, other model families) and every measurement of the harness are in
[`benchmarks/README.md`](benchmarks/README.md).

---

## Architecture

```
main.py                  CLI, chat history, command dispatch, tool-call loop
│
├── core/config.py       reads config.toml, builds the Ollama options of each usage
├── core/commands.py     commands shared by the CLI and the web (/help, /undo, /rag, /code...)
├── core/llm.py          HTTP transport to Ollama, NDJSON streaming, tools (stream_chat, chat)
├── core/persona.py      persona and user profile -> system prompt
├── core/auth.py         local accounts: register, login, path of each profile
├── core/boucle.py       the reflection loop  (code_cycle)
├── core/code_extract.py pulls Python out of the model's markdown answer
├── core/mcp_client.py   starts the MCP server, lists and calls its tools
├── core/mcp_server.py   MCP server exposing web_search (LangSearch)
├── tools/sandbox.py     runs code in a subprocess  (run_python)
├── rag/                 ingest -> embed -> store -> retrieve
├── timepred/            /fast: plan, prediction, live budget, learning
└── web.py               web server (--web), uses the same commands and stream_chat()
```

### The reflection loop

```
        task
         │
         ▼
   generate code ──► execute ──► exit_code == 0 ? ──yes──► done
         ▲                            │
         │                           no
         │                            ▼
         └─── reinject stderr ◄── same code as before ? ──yes──► ask for
              as a user message         (AST compare)            another approach
                                                                 (skip execution)
```

Everything flows through one list of `{role, content}` messages. A tool result is not a special
kind of object — it is just another message in the conversation. That is the whole mechanism.

---

## Technical decisions

### `subprocess` instead of `exec()`

Generated code is neither malicious nor trustworthy. With `exec()`, an infinite loop freezes the
agent permanently — Python has no way to interrupt a running statement. A child process can be
killed by the OS, which gives us a timeout, protects our own variables from being overwritten,
and separates stdout/stderr for free.

### A Docker container per execution

A child process still runs with the user's rights: it can read their files, open a network
connection, and read the environment variables, including the LangSearch key that `main.py`
loads from `.env`. Each generated program therefore runs in a throw-away container
(`tools/sandbox.py`, settings in `[code.docker]` of `config.toml`):

| Protection | How |
|---|---|
| No access to the user's files | only the image's file system, read-only (`--read-only`); the only writable place is a 64 MB `/tmp` in memory |
| No network | `--network none` |
| No secret | the container does not inherit Sensia's environment: no `LANGSEARCH_API_KEY` |
| No privileges | user `nobody` (`--user 65534`), `--cap-drop ALL`, `--security-opt no-new-privileges` |
| Bounded resources | 256 MB of RAM swap included, 1 CPU, 64 processes |
| Bounded time | `timeout` inside the container, and the container is killed if it does not stop |
| Nothing left behind | `--rm`: the container is deleted after each run |

The cost is small: **0.2 to 0.5 s** per execution. The trade-off is that the image only has the
standard library: code that imports `numpy` fails, and the loop then tries without it.

Without Docker (for instance on a teammate's machine), the code falls back to a local process,
with a warning. That process is hardened too (empty temporary directory, cleaned environment
without the key, Python in isolated mode `-I`), but it is not isolated from the machine.
`fallback_to_process = false` refuses to run code without Docker.

### Execution-grounded reflection, not self-critique

The loop could ask the model to review its own output. It does not. The feedback signal is the
interpreter's real `stderr` — a fact, not an opinion. A 3B model is a poor judge of its own work;
a traceback does not lie.

### A uniform return contract

`run_python` always returns `{stdout, stderr, exit_code, timed_out}` — on success, on crash, and
on timeout. On timeout there is no real result to report (the process was killed), so the values
are *fabricated*: an explicit message stating the limit, and `exit_code = 124` (the convention of
the Unix `timeout` command). The caller never has to check the return type before using it.

### Prompt *and* parsing (defence in depth)

The system prompt asks for a bare ```python block. Measured over 6 runs on a simple task, the
model complied 6/6. But compliance is probabilistic, not guaranteed: on the third attempt of a
harder task — with a long, noisy history — it prefixed its answer with a paragraph of prose.
`extract_code` caught it. The prompt handles the common case, the parser handles the rest, and a
fallback returns the raw text when no code block is present at all.

### AST comparison for stagnation, not bytecode

To detect the model going in circles, we compare a structural fingerprint of each generated
snippet (`ast.dump(ast.parse(code))`) rather than the raw text. This ignores whitespace,
line breaks and comments.

Comparing compiled bytecode was tested and **rejected**: the module-level `co_code` of
`def f(n): return n + 1` and `def f(n): return n * 999999` is *identical*, because the module
bytecode only says "build a function and bind it" — the body lives in a separate code object.
It looks like a stronger measure and is in fact meaningless at that level.

The AST does not catch pure renamings (`fib(n)` vs `fibonacci(x)`). That is an accepted limit:
normalising identifiers costs significantly more for a rare case.

### Escalation on stagnation, not immediate abandon

There is a direct tension: a low temperature makes code generation reliable but *reproducible* —
which is exactly what causes the model to regenerate the same failing code. Rather than picking
one setting, the loop reacts: on the first repeat it tells the model explicitly that it has
already tried this and asks for a different approach (or to say so if the request is impossible).
The model does not know it is repeating itself — it only sees its history.

Detecting a repeat also **skips the execution**: the result is already known, so running it again
would burn CPU (up to a full 10s timeout) for information we already have.

### Three distinct statuses

`code_cycle` returns `success`, `failed` or `unavailable`. The last one is not a failure of the
model — it means Ollama did not answer at all. The caller must be able to react differently:
rephrase the task in one case, restart the server in the other. Collapsing both into "failed"
would destroy that information.

### Output truncation at 1500 characters

`ollama ps` reports the model loaded with a **4096 token** context window (the model itself
supports 32768 — 4096 is Ollama's runtime default). At roughly 3 characters per token for code
and tracebacks, that is about 12 000 characters for *everything*: system prompt, task, and every
attempt's code and traceback.

Truncation keeps the **end** of the output, because a Python traceback puts the error message on
its last line — truncating from the start would discard exactly the part the model needs.

Ollama does not expose a tokenizer endpoint, so the limit is enforced in characters. Since a
token is always at least one character, an N-character cap is a guaranteed upper bound of N
tokens — the approximation only ever errs on the safe side.

### System prompt in French vs English

Tested: 6/6 format compliance with a French system prompt, 6/6 with the English equivalent, on
the same task and model. No measurable gain, so the choice was made on readability grounds rather
than on a belief about training data.

---

## Measurements

| What | Result |
|---|---|
| Self-correction, naive `fib(42)` | success in 3 attempts, 36.8 s (2 timeouts, then memoisation) |
| Stagnation detection (fake `chat`, always same code) | `run_python` called **1×** instead of 3× |
| Docker sandbox: `os.listdir('/home')` | `[]` (the jury's example, which used to list the real folders) |
| Docker sandbox: `LANGSEARCH_API_KEY` visible | `False` |
| Docker sandbox: network, write outside `/tmp` | `Network is unreachable`, `Read-only file system` |
| Docker sandbox: infinite loop, 400 MB allocation, process bomb | stopped at the timeout, killed at 256 MB, blocked after 62 processes |
| Docker sandbox: cost of a run | 0.2 to 0.5 s; naive `fib(42)` still corrected in 2 attempts (18 s) |
| Format compliance, FR vs EN system prompt | 6/6 vs 6/6 |
| Effective context window | 4096 tokens (`ollama ps`), model capacity 32768 |

The stagnation detection is tested with a stub `chat` function that always returns the same
answer. A real model is non-deterministic: it cannot be asked to repeat itself on demand, so the
scenario is not reproducible against a live LLM. The stub makes the test deterministic and
instant, and isolates the loop from both the model and the sandbox.

---

## Known limitations

These are deliberate, not oversights.

**The oracle problem.** `exit_code == 0` proves the code did not crash — not that it is correct.
A program that computes a product instead of a sum exits cleanly and returns a confident wrong
answer. Verifying correctness requires a reference *external* to the system that produced the
code (user-provided tests, invariants, a second implementation). Sensia does not have one, so
`success` should be read as *"ran without error"*, not *"is correct"*.

**The sandbox depends on Docker.** With Docker, generated code cannot see the user's files,
the network or the API key (see [A Docker container per execution](#a-docker-container-per-execution)).
A container shares the host's kernel: it protects against *accidentally destructive or
indiscreet LLM output*, not against a determined attacker exploiting a kernel flaw, which would
need a virtual machine. Without Docker, the fallback process is hardened but runs with the
user's rights. The image only contains the Python standard library.

**Contradictory tasks.** A task can be impossible as stated (e.g. "compute fib(42) with naive
recursion" cannot finish within the execution budget). The model then oscillates between the
user's constraint and the execution feedback. The stagnation message explicitly allows it to say
the request is impossible, but this is mitigation, not a solution.

**Small-model fragility.** `qwen2.5:3b` was chosen for fast iteration on CPU. It is weaker at
instruction-following and role tracking than a 7B. The model is selectable at runtime
(`--model`) precisely so this can be traded off without touching the code. See
[Model choice](#model-choice-and-local-benchmark) for the measured trade-off.

**One external call.** Everything runs locally except the web search: the query is sent to
LangSearch. It is the price of answering about recent events, and the only data that leaves
the machine.

**The context is not budgeted.** The history grows without limit and tokens are not counted:
a long session eventually exceeds the 4,096-token context, and Ollama then silently drops the
oldest part of the prompt.

---

## Not implemented

- Persistence of the conversation history across sessions (the user profile and remembered
  facts do persist)
- Context compaction for long conversations (the chat history grows unbounded)

Implemented since the mid-term review: the configuration file (`config.toml`), structured
output (JSON schema for the `/fast` plan), native tool calling through MCP, persona switching
mid-session, the isolated Docker sandbox.

---

## Project layout

```
main.py                  entry point, CLI, chat loop (--web starts the web interface)
web.py                   FastAPI server: /api/chat, /api/history, login routes, static files
web/
    index.html           chat page
    login.html           login and account creation page
    css/style.css        design
    js/app.js            sends the text, reads the stream, redraws the conversation
    js/login.js          sends the login and account creation forms
config.toml              every tunable value: Ollama, generation options, RAG, code, web...
core/
    config.py            CONFIG, options(usage), TIMEOUT
    commands.py          handle_command(text, messages, model, url, user) -> str | None
    llm.py               stream_chat(messages, model, url) -> yields str
                         chat(messages, model, url) -> str | None
    boucle.py            code_cycle(task, model, url, max_iterations=3) -> dict
    code_extract.py      extract_code(text) -> str
    persona.py           load_persona(id), list_personas(), get_persona_name(id),
                         load_user_profile(file), remember(fact, file), build_system_prompt(...)
    auth.py              register(...), login(email, password), user_exists(email), profile_path(email)
    mcp_client.py        get_tools(), call_tool(name, arguments)
    mcp_server.py        MCP server: web_search(query, freshness)
rag/
    ingest.py            reads knowledge/documents/, chunk_text()
    embed.py             embed(texts), similarity(a, b)
    store.py             save_index(), load_index()
    retrieve.py          translate(), retrieve(question), build_prompt()
timepred/                /fast: runner, plan, history, fusion, budget, worker, executor
benchmarks/
    models.py            speed, memory and code-loop success of several models
persona/
    personas/*.md        one file per assistant persona (sensia, dev)
    user.example.md      empty profile template, used by /remember if a profile file is missing
data/                    accounts and profiles (git-ignored)
    users.json           salted password hashes and the persona of each account
    profiles/<email>.md  the profile of each account, completed by /remember
docs/user_stories/       user stories of every feature + traceability table
tools/
    sandbox.py           run_python(code, timeo) -> dict: Docker container, or hardened process
```
