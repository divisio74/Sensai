# Sensia

A local CLI AI assistant built on Ollama, with a **self-correcting code agent**.

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
python3 main.py --model qwen2.5:7b #not the default model
python3 main.py --url http://other-host:11434/api/chat
python3 main.py --help
```

## Tests

The LangSearch integration test can be launched independently:

```bash
python3 tests/main.py
```

## Usage

| Input | Effect |
|---|---|
| any text | normal conversation, streamed token by token |
| `/code <task>` | runs the self-correcting code agent on `<task>` |
| `/internet_search <query>` | searches the web and feeds the results to agent |
| `quit` | exits |
| `Ctrl+C` / `Ctrl+D` | exits cleanly |

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

## Architecture

```
main.py                  CLI, chat history, command dispatch
│
├── core/llm.py          HTTP transport to Ollama, NDJSON streaming
├── core/boucle.py       the reflection loop  (code_cycle)
├── core/code_extract.py pulls Python out of the model's markdown answer
└── tools/sandbox.py     runs code in a subprocess  (run_python)
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

**No timeout on the HTTP request.** If Ollama hangs mid-stream, the loop waits indefinitely. A
`timeout=(connect, read)` on `requests.post` would bound it.

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
- Persistence across sessions
- Context compaction for long conversations (the chat history grows unbounded)

---

## Project layout

```
main.py                  entry point, CLI, chat loop
core/
    llm.py               chat(messages, model, url) -> str | None
    boucle.py            code_cycle(task, model, url, max_iterations=3) -> dict
    code_extract.py      extract_code(text) -> str
tools/
    sandbox.py           run_python(code, timeo=10) -> dict
info.md                  team task split
```
