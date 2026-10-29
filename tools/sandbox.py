import subprocess

from core.config import CONFIG

MAX_OUTPUT = CONFIG["code"]["max_output"]

def tronque_code_cycle(texte, maximum=MAX_OUTPUT, garder="fin"):
    if len(texte) <= maximum:
       return texte
    return "truncated start" + texte[-maximum:]

def run_python(code, timeo=CONFIG["code"]["execution_timeout"]):
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
        "stdout": tronque_code_cycle(resultat.stdout),
        "stderr": tronque_code_cycle(resultat.stderr),
        "exit_code": resultat.returncode,
        "timed_out": False,
    }



