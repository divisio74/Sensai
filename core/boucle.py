from core.config import CONFIG
from core.llm import chat
from core.code_extract import extract_code
from tools.sandbox import run_python
import ast

PROMPT = (
    "You are a Expert Python code generator. "
    "Reply ONLY with executable Python code inside a ```python block. "
    "No comments, NO explanations, NO text before or after."
)

def make_ast(code):
    try:
        return ast.dump(ast.parse(code))
    except SyntaxError:
        return code


def code_cycle(tache, model, url, max_iterations=CONFIG["code"]["max_iterations"]):
    messages = [
        {"role": "system", "content": PROMPT},
        {"role": "user",   "content": tache},
    ]
    code = None
    ast_tab = []
    attempts = []
    for tentative in range(1, max_iterations + 1):
        print(f"\n===== Attempt {tentative}/{max_iterations} =====")

        reponse = chat(messages, model, url, usage="code")
        if reponse is None:
            print("the model is not responding")
            return {"status": "unavailable", "code": code, "tentatives": tentative, "attempts": attempts}
        code = extract_code(reponse)

        new_ast = make_ast(code)
        if new_ast in ast_tab:
            attempts.append({"code": code, "error": "Same code as a previous attempt, skipped."})
            messages.append({"role": "assistant", "content": reponse})
            messages.append({"role": "user", "content":
                f"You have already try this strategy and it was a fail So try an diferent strategy or ask the user to modify the demand if its not possible, "})
            continue
        ast_tab.append(new_ast)

        resultat = run_python(code)

        if resultat["exit_code"] == 0:
            attempts.append({"code": code, "error": None})
            print(f"\nSucceeded in {tentative} attempt(s)")
            print("Output:", resultat["stdout"])
            return {"status": "success", "code": code, "tentatives": tentative, "stdout": resultat["stdout"], "attempts": attempts}
        print(f"\nFailure: {resultat['stderr'][:300]}")
        attempts.append({"code": code, "error": resultat["stderr"]})

        messages.append({"role": "assistant", "content": reponse})
        messages.append({"role": "user", "content":
            f"Code error with execution :\n{resultat['stderr']}\n"
            f"fix it and return a corrected one"})

    print(f"\nMax try reached with {max_iterations} max iterations")
    return {"status": "failed", "code": code, "tentatives": max_iterations, "attempts": attempts}

