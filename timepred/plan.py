import json
import re

import requests

from timepred.llm import ask_ollama

CODE_TYPE = "code"
DIRECT_TYPE = "direct"
DELIVERABLE_TYPES = {"text": "write", "code": CODE_TYPE, "explanation": "explain"}
PRODUCTION_TYPES = {"write", CODE_TYPE, "explain", DIRECT_TYPE}
PRUNABLE_TYPES = {"research"}
SHORT_TASK_WORDS = 12

CLASSIFY_SCHEMA = {
    "type": "object",
    "properties": {
        "deliverable": {"type": "string", "enum": list(DELIVERABLE_TYPES)},
    },
    "required": ["deliverable"],
}
CODE_WORDS = re.compile(r"\b(function|fonction|script|programme python|python program|"
                        r"classe python|python class)\b", re.IGNORECASE)
RESEARCH_WORDS = re.compile(r"\b(research|look up|search|recherche|cherche|renseigne)",
                            re.IGNORECASE)
EXPLAIN_WORDS = re.compile(r"\b(explain|explique|expliquer|explication|describe|décris|"
                           r"how it works|comment (ça|il|elle) (marche|fonctionne))", re.IGNORECASE)

CLASSIFY_PROMPT = (
    "You classify a task for a local assistant that can only write text and write and run "
    "Python code.\n"
    "- deliverable: \"code\" if the task asks to write a program, a function or a script, "
    "even when it also asks to research, test or explain; otherwise \"explanation\" if it "
    "asks to explain or compare a topic; otherwise \"text\" (an email, a letter, a post, "
    "a report, a summary...)."
)

STEP_NAMES = {
    "research": "Gather the facts the task needs",
    "write": "Write the complete requested text, ready to use",
    CODE_TYPE: "Write and run the requested code",
    "explain": "Explain the topic clearly and completely",
}

REESTIMATE_SCHEMA = {
    "type": "object",
    "properties": {"weights": {"type": "array", "items": {"type": "integer"}}},
    "required": ["weights"],
}

REESTIMATE_PROMPT = (
    "You re-estimate a plan while it is running. You get the task, the steps already done, "
    "the last result and the remaining steps. Now that you know more, give the relative "
    "effort (1-5) of EVERY step of the plan, done and remaining, in the same order: "
    "exactly one weight per step."
)


def step(step_type, weight, priority, essential, name=None):
    return {"name": name or STEP_NAMES[step_type], "type": step_type, "weight": weight,
            "priority": priority, "essential": essential}


def classify_task(task, model, url):
    try:
        raw = ask_ollama(model, [
            {"role": "system", "content": CLASSIFY_PROMPT},
            {"role": "user", "content": task},
        ], url=url, schema=CLASSIFY_SCHEMA)
        deliverable = json.loads(raw)["deliverable"]
    except (ValueError, KeyError):
        return "text"
    return deliverable if deliverable in DELIVERABLE_TYPES else "text"


def make_plan(task, model, url, allow_direct=True):
    if allow_direct and len(task.split()) <= SHORT_TASK_WORDS:
        return [step(DIRECT_TYPE, 1, 1, True, name=task)]
    deliverable = classify_task(task, model, url)
    if deliverable == "text" and CODE_WORDS.search(task):
        deliverable = "code"
    main = DELIVERABLE_TYPES[deliverable]
    steps = [step("research", 1, 2, False)] if RESEARCH_WORDS.search(task) else []
    steps.append(step(main, 3, 1, True))
    if main == CODE_TYPE and EXPLAIN_WORDS.search(task):
        steps.append(step("explain", 1, 2, True, name="Explain the code written above"))
    return steps


def reestimate_weights(task, steps, done_count, last_result, model, url):
    listing = (f"Task: {task}\n"
               f"Last result (truncated): {last_result[-500:]}\n"
               "Plan:\n"
               + "".join(f"{i}. [{'done' if i <= done_count else 'remaining'}] "
                         f"{step['name']} ({step['type']})\n"
                         for i, step in enumerate(steps, 1)))
    try:
        raw = ask_ollama(model, [
            {"role": "system", "content": REESTIMATE_PROMPT},
            {"role": "user", "content": listing},
        ], url=url, schema=REESTIMATE_SCHEMA)
        weights = json.loads(raw)["weights"]
    except (requests.exceptions.RequestException, ValueError, KeyError):
        return None
    if len(weights) != len(steps) or not all(isinstance(w, int) for w in weights):
        return None
    return [min(max(w, 1), 5) for w in weights]
