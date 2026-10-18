import json

from timepred.llm import ask_ollama

STEP_TYPES = {
    "research": "find information that is not in the task",
    "analyse": "understand the request, compare options or decide",
    "write": "produce new content (an email, a document, a function...)",
    "transform": "rework existing content (summarize, translate, refactor, format...)",
    "check": "verify, test or review a result",
    "explain": "explain something to the user",
}
CODE_TYPE = "code"
DIRECT_TYPE = "direct"
PRUNABLE_TYPES = {"analyse", "research", "check"}
SHORT_TASK_WORDS = 12

PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "steps": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "type": {"type": "string", "enum": list(STEP_TYPES)},
                    "outputs_code": {"type": "boolean"},
                    "weight": {"type": "integer"},
                    "priority": {"type": "integer"},
                    "essential": {"type": "boolean"},
                },
                "required": ["name", "type", "outputs_code", "weight", "priority", "essential"],
            },
        }
    },
    "required": ["steps"],
}

PLAN_PROMPT = (
    "You are a planner. Split the user's task into 1 to 5 sequential steps. "
    "Use a single step when the task is simple.\n"
    "Step types:\n"
    + "".join(f"- {name}: {meaning}\n" for name, meaning in STEP_TYPES.items())
    + "For each step give: name, type, outputs_code (true if the result of this step "
    "is source code), weight (1-5, relative effort), priority (1 = most important), "
    "essential (true if the final result is wrong or missing without this step).\n"
    "Any step that produces an element explicitly requested in the task MUST be essential."
)


def make_plan(task, model, url, allow_direct=True):
    if allow_direct and len(task.split()) <= SHORT_TASK_WORDS:
        return [{"name": task, "type": DIRECT_TYPE, "weight": 1, "priority": 1, "essential": True}]
    raw = ask_ollama(model, [
        {"role": "system", "content": PLAN_PROMPT},
        {"role": "user", "content": task},
    ], url=url, schema=PLAN_SCHEMA)
    steps = json.loads(raw)["steps"]
    for step in steps:
        step["weight"] = min(max(step["weight"], 1), 5)
        if step.pop("outputs_code"):
            step["type"] = CODE_TYPE
    return merge_code_steps(steps)


def merge_code_steps(steps):
    merged = []
    for step in steps:
        previous = merged[-1] if merged else None
        if previous and previous["type"] == CODE_TYPE and step["type"] == CODE_TYPE:
            previous["name"] += "; " + step["name"]
            previous["weight"] += step["weight"]
            previous["priority"] = min(previous["priority"], step["priority"])
            previous["essential"] = previous["essential"] or step["essential"]
        else:
            merged.append(step)
    return merged
