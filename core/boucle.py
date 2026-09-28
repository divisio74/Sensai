from core.llm import chat
from core.code_extract import extract_code
from tools.sandbox import run_python

PROMPT = (
    "Tu es un générateur de code Python. "
    "Réponds UNIQUEMENT avec du code Python exécutable dans un bloc ```python. "
    "Aucune explication, aucun texte avant ou après."
)


def code_boucle(tache, model, url, max_iterations=3):
    messages = [
        {"role": "system", "content": PROMPT},
        {"role": "user",   "content": tache},
    ]

    for tentative in range(1, max_iterations + 1):
        print(f"\n===== Tentative {tentative}/{max_iterations} =====")

        reponse = chat(messages, model, url)
        code = extract_code(reponse)
        resultat = run_python(code)

        if resultat["exit_code"] == 0:
            print(f"\nRéussi en {tentative} tentative(s)")
            print("Sortie :", resultat["stdout"])
            return {"status": "success", "code": code, "tentatives": tentative}

        print(f"\nÉchec : {resultat['stderr'][:300]}")

        messages.append({"role": "assistant", "content": reponse})     # ② ce que le MODÈLE a produit
        messages.append({"role": "user", "content":               # ③ ce que TOI tu lui dis
            f"Code error with execution :\n{resultat['stderr']}\n"
            f"fix it and return a corrected one"})

    print(f"\nMax try reached with {max_iterations} max iterations")
    return {"status": "failed", "code": code, "tentatives": max_iterations}

