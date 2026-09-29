import subprocess

MAX_OUTPUT = 1500


def contexte_limite(texte, maximum=MAX_OUTPUT, garder="fin"):
    if len(texte) <= maximum:
       return texte
    return "truncated start" + texte[-maximum:]

def run_python(code, timeo=10):
    try:
        resultat = subprocess.run(
            ["python3", "-c", code],
            capture_output=True,
            text=True,
            timeout=timeo,
        )
    except (subprocess.TimeoutExpired):
        return {"stdout": "",
            "stderr": f"Timeout: the code did not finish within {timeo} seconds. Retry with a lower algorithmic complexity",
            "exit_code": 124,
            "timed_out": True
        }
    return {
        "stdout": contexte_limite(resultat.stdout),
        "stderr": contexte_limite(resultat.stderr),
        "exit_code": resultat.returncode,
        "timed_out": False,
    }



