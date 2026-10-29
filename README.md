# Sensia

A local AI assistant built on Ollama, usable from the terminal or a web page, with a
**self-correcting code agent**.

Sensia is a chatbot that can also *act*: given a task, it writes Python code, runs it in a
separate process, reads the real error output, and rewrites the code until it runs — or until
it recognises that it is going in circles.

No LLM framework is used. Every call to the model is a direct HTTP request to the Ollama API.

---

## Requirements

- Python 3.10+ (developed on 3.12)
- [Ollama](https://ollama.com) running locally
- A LangSearch API key
- `requests` and `python-dotenv`
- `fastapi` and `uvicorn` (only for the web interface)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
ollama pull qwen2.5:3b
ollama pull nomic-embed-text
```

Set `LANGSEARCH_API_KEY` in a `.env` file at the project root. The test runner loads this file
with `python-dotenv`.

## Running

```bash
python3 main.py
python3 main.py --model qwen2.5:7b
python3 main.py --url http://other-host:11434/api/chat
python3 main.py --persona dev
python3 main.py --web
python3 main.py --help
```
`--model`, `--url` and `--persona` work the same way with `--web`.

## Configuration

Every tunable value lives in [`config.toml`](config.toml), grouped by feature and commented:
Ollama URLs and timeouts, RAG threshold and chunk size, code-loop iterations and sandbox
timeout, web-search limits, web server port, `/fast` settings. `--model` and `--url` override
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

## Tests

The LangSearch integration test can be launched independently:

```bash
python3 tests/main.py
```

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
| `/persona` | shows the current persona and the available ones | ❌ terminal only |
| `/persona <name>` | switches persona mid-conversation, the history is kept | ❌ terminal only |
| `/remember <fact>` | saves a fact in the user profile, used right away and in later sessions | ❌ terminal only |
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

`python3 main.py --web` starts a small FastAPI server and serves a chat page on
http://127.0.0.1:4040. The page sends what the user types to the server, which answers with the
same code as the terminal.

```
browser (web/index.html, css, js)          web.py (FastAPI)
   POST /api/chat {text}  ───────────────►  handle_command()  ──► /help, /clear, /rag, /code...
   ◄─────────────── {output, messages}  (JSON)
                                             or stream_chat()  ──► Ollama
   ◄─────────────── the answer, piece by piece  (text stream)
   GET /api/history  ────────────────────►  the conversation (to redraw it after a reload)
```

### Technical decisions

**Same backend as the terminal.** The commands live in `core/commands.py` and *return* their text
instead of printing it. The terminal prints it, the web sends it to the page. Each command is
written once and behaves the same in both interfaces.

**The conversation is kept by the server.** Like `main.py`, `web.py` keeps one `messages` list.
The page only displays what the server returns, so `/undo` or `/clear` need no logic in
JavaScript, and reloading the page does not lose the conversation. Sensai is a local, single-user
assistant, so one list is enough.

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
- In the web, the normal chat does not run the automatic internet search: when the model asks
  for a search, the request is shown as is. `/fast` only works in the
  terminal for now.
- All browser tabs share the same conversation, which is lost when the server restarts.
- Command bubbles (`/help`, sources of `/rag`...) are saved by the browser, not by the server.

---

## Persona and user profile

The system prompt (the first message of the conversation) is built from two Markdown files:
who the assistant is, and who the user is.

```
persona/personas/<name>.md   the assistant: name (first "# " line), tone, role, values
persona/user.md              the user: about me, preferences, remembered facts
```

```
messages[0] = {"role": "system", "content":
    <persona/personas/sensia.md>
    Today's date is 2026-10-29.
    About the user you are talking to. Their preferences below override your default behavior:
    <persona/user.md>
}
```

```
python3 main.py --persona dev        start with another persona
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

**Two files: the assistant is read-only, the user profile is writable.** `/remember` only ever
writes to `persona/user.md`. If facts could be written into the persona file, a user could make
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
| Profile preference that adds to the persona ("Always call me Daddy Boy") | applied 3/4 |
| Profile preference that contradicts the persona ("never give me the answer" vs "give short, working examples") | applied 0/4 |
| Fact given before `/persona dev`, asked after | remembered |
| Fact saved with `/remember`, asked after restarting Sensia | remembered |

### Limitations

- When the profile contradicts the persona, a small model follows the persona, even with the
  priority sentence: the profile works for preferences that complete the persona.
- Saying "remember that..." in plain language does nothing: `/remember` must be typed. A
  `remember` tool called by the model, like `web_search`, is the natural next step.
- `/remember` alone (no text) answers `Unknown command`, and `/persona` and `/remember` are not
  listed in `/help`.
- The web interface uses the persona chosen at launch, but neither the user profile nor
  `/persona` / `/remember`.
- Facts are appended at the end of `user.md`, so `## Remembered facts` must stay the last
  section, and the profile grows without limit in a 4096-token context.
- `persona/user.md` is versioned, so the whole team shares one profile.

---

## Architecture

```
main.py                  CLI, chat history, command dispatch
│
├── core/commands.py     commands shared by the CLI and the web (/help, /undo, /rag, /code...)
├── core/llm.py          HTTP transport to Ollama, NDJSON streaming (stream_chat, chat)
├── core/persona.py      persona and user profile -> system prompt
├── core/boucle.py       the reflection loop  (code_cycle)
├── core/code_extract.py pulls Python out of the model's markdown answer
├── tools/sandbox.py     runs code in a subprocess  (run_python)
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
and separates stdout/stderr for free. It is also the only form that *could* later be given
resource limits or filesystem isolation.

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

**The sandbox isolates the process, not the system.** `subprocess` protects the agent from
crashes, infinite loops and variable collisions. It does **not** prevent generated code from
writing to the filesystem or opening a network connection — it runs with the user's own rights.
The threat model covered here is *accidentally destructive LLM output*, not a determined
attacker. Filesystem isolation (temporary working directory), a cleaned environment and
`resource.setrlimit` caps are the natural next step.

**Contradictory tasks.** A task can be impossible as stated (e.g. "compute fib(42) with naive
recursion" cannot finish within the execution budget). The model then oscillates between the
user's constraint and the execution feedback. The stagnation message explicitly allows it to say
the request is impossible, but this is mitigation, not a solution.

**Small-model fragility.** `qwen2.5:3b` was chosen for fast iteration on CPU. It is weaker at
instruction-following and role tracking than a 7B. The model is selectable at runtime
(`--model`) precisely so this can be traded off without touching the code.

---

## Not implemented

- Configuration file (the spec allows *CLI argument **or*** config file; only CLI is implemented)
- Structured output / JSON schema-constrained decoding
- Native tool calling
- Persistence of the conversation history across sessions (the user profile and remembered
  facts do persist)
- Context compaction for long conversations (the chat history grows unbounded)

---

## Project layout

```
main.py                  entry point, CLI, chat loop (--web starts the web interface)
web.py                   FastAPI server: /api/chat, /api/history, static files
web/
    index.html           chat page
    css/style.css        design
    js/app.js            sends the text, reads the stream, redraws the conversation
core/
    commands.py          handle_command(text, messages, model, url) -> str | None
    llm.py               stream_chat(messages, model, url) -> yields str
                         chat(messages, model, url) -> str | None
    boucle.py            code_cycle(task, model, url, max_iterations=3) -> dict
    code_extract.py      extract_code(text) -> str
    persona.py           load_persona(id), list_personas(), get_persona_name(id),
                         load_user_profile(), remember(fact), build_system_prompt(...)
persona/
    personas/*.md        one file per assistant persona (sensia, dev)
    user.md              the user profile, completed by /remember
docs/user_stories/       user stories (dev, persona, profile)
tools/
    sandbox.py           run_python(code, timeo=10) -> dict
info.md                  team task split
```
