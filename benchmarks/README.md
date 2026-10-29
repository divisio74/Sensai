# Benchmarks

Measurements of the local models on our hardware, and of the Sensia harness itself.

| Script | What it measures | Writes |
|---|---|---|
| `python3 -m benchmarks.models [model ...]` | speed, memory, load time and code-loop success of local models | `benchmarks/results/models.json` |
| `python3 -m benchmarks.timepred_backtest` | accuracy of the `/fast` time prediction, replayed on the recorded history | nothing (read-only) |
| `python3 -m benchmarks.timepred_budget` | how often `/fast` keeps its budget, on 24 real runs | the runs, in `knowledge/history/` |

**Reference machine**: AMD Ryzen 5 5600H (6 cores, 12 threads), 15.8 GB of RAM, **no GPU used**
(CPU inference), Ollama 0.34.4, context window `num_ctx = 4096`. Every number below comes from
this machine; on another one, run the scripts again.

---

## 1. Local models

Each model is unloaded first (cold start), answers 4 fixed prompts (two conversations, one
code request, one RAG-style question) with the temperatures of `config.toml` and `seed = 42`,
then runs the self-correcting code loop (`code_cycle`) on 5 reference tasks.

| Model | Parameters | Quantization | Disk | Memory | Cold load | Prompt reading | Generation | Median answer | Code loop | Attempts | Code time |
|---|---|---|---|---|---|---|---|---|---|---|---|
| qwen2.5:1.5b | 1.5B | Q4_K_M | 0.99 GB | 1.17 GB | 4.2 s | 251.5 tok/s | 35.8 tok/s | 8.6 s | 4/5 | 1.0 | 2.8 s |
| **qwen2.5:3b** | 3.1B | Q4_K_M | 1.93 GB | 2.16 GB | 4.2 s | 96.9 tok/s | 18.2 tok/s | 20.1 s | 4/5 | 1.0 | 6.7 s |
| qwen2.5:7b | 7.6B | Q4_K_M | 4.68 GB | 5.06 GB | 11.1 s | 41.4 tok/s | 8.4 tok/s | 48.9 s | 5/5 | 1.0 | 7.7 s |
| llama3.2:3b | 3.2B | Q4_K_M | 2.02 GB | 2.56 GB | 5.4 s | 105.6 tok/s | 19.0 tok/s | 6.0 s | 5/5 | 1.4 | 5.3 s |

*Memory*: size of the loaded model reported by Ollama (`/api/ps`). *Attempts*: mean number of
attempts of the code loop for the tasks that succeeded. *Code time*: median time of one
`code_cycle`. Measured on 2026-10-29.

### What the numbers show

**On a CPU, generation speed is set by memory bandwidth, not by computing power.** Multiply
the generation speed by the size of the model: 35.8 × 0.99 = 35, 18.2 × 1.93 = 35,
8.4 × 4.68 = 39, 19.0 × 2.02 = 38 GB/s. The product is almost constant: to produce each token,
the processor reads all the weights of the model once from RAM. A model twice as big is twice as
slow, whatever its family.

**Reading the prompt is much faster than writing the answer** (97 against 18 tokens/s for the
3B): the prompt tokens are processed in parallel, the answer tokens one after the other. A long
RAG prompt costs much less than a long answer.

**The length of the answer matters as much as the speed.** `llama3.2:3b` generates at the same
speed as `qwen2.5:3b`, but its answers are about three times shorter, so it answers in 6 s
instead of 20 s. For the user, the waiting time depends on what the model chooses to write.
This is also why `/fast` learns the usual length of the answers, not only the speed.

**Memory follows the file size**, plus 0.2 to 0.5 GB for the context (the KV cache of 4,096
tokens) and the runtime. The 7B fits in 15.8 GB, but leaves less room for the embedding model,
the browser and the IDE.

**A bigger model loads more slowly**: 11 s for the 7B against 4 s for the 3B. Ollama unloads a
model after 5 minutes of inactivity, so this cost comes back regularly.

**Quality: the 5 code tasks are too easy to separate the models.** All of them succeed 4 or 5
times out of 5. The 7B is the only Qwen to succeed 5 times out of 5; Llama succeeds 5 times too,
but needed corrections more often (1.4 attempts on average): the code loop compensated for its
mistakes. Differences in instruction following, French or persona respect are not measured by
this bench.

### Quantization

All the models are in **Q4_K_M**: the weights are stored on about 4 to 6 bits instead of 16,
by blocks that share a scale factor (*k-quants*, *medium* variant, which keeps a few sensitive
tensors at higher precision). For `qwen2.5:3b`, that is 1.93 GB instead of about 6.2 GB in
16-bit floats, so about 5 bits per weight.

On this machine, it is what makes local models usable:

- **Memory**: the 7B would need about 15 GB in 16-bit, more than the machine can spare; in
  Q4_K_M it takes 5 GB.
- **Speed**: since generation is limited by memory bandwidth (see above), a model three times
  smaller is about three times faster.
- **Cost**: a small loss of precision in the weights. It is generally considered small for
  Q4_K_M, but we did not measure it against a higher-precision version (Q8_0 or FP16).

### Model families

At the same size (3B), **Qwen 2.5** (Alibaba) and **Llama 3.2** (Meta) run at the same speed:
the family does not change the cost per token, only the behaviour (answer length, number of
corrections). We keep `qwen2.5:3b` as the default because the whole harness was developed and
measured with it: native tool calls for the MCP web search, JSON schemas for the `/fast` plan,
and the learned `/fast` history. Llama 3.2 3B is a credible alternative according to this
bench, to evaluate on French and on tool calls before switching.

Other families were not measured (for example Phi-3.5-mini, Gemma 2 2B or Mistral 7B). Adding
one only takes `ollama pull <model>` and `python3 -m benchmarks.models <model>`.

### The choice

`qwen2.5:3b` is the **largest model that stays interactive** on this hardware: 18 tokens/s is
faster than a human reads, and a typical answer takes 20 s. The 7B is a bit more reliable, but a
typical answer takes almost a minute and breaks the `/fast` budgets; the 1.5B is twice as fast
and as reliable on these 5 code tasks, but smaller models are generally weaker at following
instructions, which this bench does not measure. The model can be changed
without touching the code (`--model qwen2.5:7b`, or `config.toml`) when quality matters more than
time.

---

## 2. The harness

### 2.1 The `/fast` plan: free planning against a built plan

Measured on 2026-10-20 on 5 complete tasks, with the free planner of the previous version (no
longer in the code) and the current one, where the model only classifies the deliverable and
Python builds the plan.

| Task | Free plan | Built plan |
|---|---|---|
| Reminder email | 68.6 s, 4 steps | **8.8 s**, 1 step |
| Meeting report "and send it" | 24.9 s, no report delivered | **9.2 s**, report delivered |
| Prime numbers function | 65.1 s, 4 steps | **6.3 s**, 1 step |
| Bank account class + explanation | 52.1 s, truncated code | **32.6 s**, code + explanation |
| Explain HTTP caching | 32.6 s, 3 steps | **11.7 s**, 1 step |
| **Total** | **243 s**, 3/5 expected results | **69 s**, 5/5 expected results |

- Planning time: about 1 s instead of 7 to 24 s.
- Classification: correct in 34 of 36 plans (12 requests × 3 runs), and 36/36 valid JSON; the 2
  errors (code tasks classified as text) are fixed by a keyword rule.
- Impossible actions ("send the email", "publish on LinkedIn") in a plan: 0 of 36, against 4
  of 14 plans with the free planner, even with explicit rules in its prompt.

### 2.2 Accuracy of the `/fast` prediction (`timepred_backtest.py`)

127 recorded runs, 83 usable (tokens recorded, answer not shortened, no failed step). Each one
is predicted again without itself, with the runner's own functions. Measured on 2026-10-29.

| When | Median error | In seconds |
|---|---|---|
| Before starting, new task, raw durations | 42 % | 2.9 s |
| Before starting, new task, answer length ÷ machine speed | **36 %** | 2.7 s |
| Before starting, task already run once | 35 % | 3.2 s |
| Before starting, task already run twice or more | **24 %** | 1.9 s |
| During generation, 25 % of the answer written | 20 % | 1.9 s |
| During generation, 50 % written | 17 % | 2.1 s |
| During generation, 75 % written | 17 % | 1.8 s |
| During generation, 90 % written | **9 %** | 1.1 s |

The prediction **improves with use** (36 % → 24 % once a task is known) and **during the run**
(20 % → 9 %). The errors are small in seconds because the tasks are short: 9 s in median.
The "never run before" line in the real order of the history only has 5 runs; the robust figure
for a new task is the 36 % above, computed on all 83 runs with their copies removed.

### 2.3 Keeping the budget (`timepred_budget.py`)

24 real runs: 8 tasks, each with a comfortable, a tight and a very tight budget; every question
is answered "yes". Measured on 2026-10-21.

| Result | Value |
|---|---|
| Budget kept | **20 / 24** (comfortable budgets: 8 / 8) |
| Overruns announced before they happened | **4 / 4** |
| Overruns without warning | **0** |
| Answers shortened to fit the budget | 13 / 24 |

### 2.4 The self-correcting code loop

| What | Result |
|---|---|
| Naive `fib(42)` (too slow on purpose) | success in 3 attempts, 36.8 s: 2 timeouts, then memoisation |
| Stagnation detection (stub model, always the same code) | code executed 1 time instead of 3 |
| 5 reference tasks, `qwen2.5:3b` | 4/5 successes, 1 attempt on average |
| 5 reference tasks, `llama3.2:3b` | 5/5 successes, 1.4 attempts: corrections made the difference |

Not measured yet: the success rate on the same tasks **without** the loop (a single attempt),
which would isolate the gain brought by the correction.

### 2.5 Generation parameters

The `options` actually sent to Ollama were checked by intercepting the HTTP requests:
conversation 0.7, code 0.2, RAG answer 0.1, translation 0, `/fast` plan 0, `/fast` text steps
0.7, always with `num_ctx = 4096`.

---

## Limits of these measurements

- **One machine.** Speeds depend on the memory bandwidth: a laptop with faster RAM, or a GPU,
  changes every number of section 1.
- **Small samples.** 5 code tasks, 24 budget runs, 83 replayed runs: enough to see orders of
  magnitude and trends, not to rank close models.
- **Non-determinism.** Even with a fixed seed, the length of an answer varies from one run to
  the next; this is the main source of error of the `/fast` prediction.
- **Quality is barely measured.** Section 1 measures cost and code success; it does not measure
  the quality of the text, the French, or the respect of the persona.
