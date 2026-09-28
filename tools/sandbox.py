import subprocess

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
            "stderr": "Timeout for subprocesses",
            "exit_code": 124,
            "timed_out": True
        }
    return {
        "stdout": resultat.stdout,
        "stderr": resultat.stderr,
        "exit_code": resultat.returncode,
        "timed_out": False,
    }


# testes facile pour la sandbox
if __name__ == "__main__":
    print("1)", run_python("print(2 + 2)"))
    print("2)", run_python("print(x)"))
    print("3)", run_python("while True: pass"))

