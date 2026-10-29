"""Budget bench of /fast: real runs with a comfortable, a tight and a very tight budget.

    python3 -m benchmarks.timepred_budget

Every question asked by Sensia is answered "y", to measure how far a run would go.
Warning: the runs are recorded in knowledge/history/, like normal /fast runs.
"""
import contextlib
import io
import sys

from core.config import CONFIG
from timepred.runner import run

MODEL, URL = CONFIG["ollama"]["model"], CONFIG["ollama"]["chat_url"]
BENCH = [
    ("Écris un mail de relance pour la réunion de lundi avec l'équipe produit", (30, 8, 4)),
    ("Rédige un mail d'invitation à la réunion d'équipe de vendredi à 14h en salle B", (30, 8, 4)),
    ("Résume en 5 points les avantages du télétravail pour une présentation à la direction", (30, 8, 4)),
    ("Explain how HTTP caching works and compare it with a CDN for a beginner audience", (30, 10, 5)),
    ("Explain the difference between REST and GraphQL APIs for a junior developer", (30, 10, 5)),
    ("Write a Python function that checks if a string is a palindrome and test it on 5 words", (30, 8, 4)),
    ("Write a Python function that returns the first 15 Fibonacci numbers and prints them", (30, 8, 4)),
    ("Write a Python class for a bank account with deposit and withdraw, run 3 operations, "
     "then explain how it works", (60, 15, 8)),
]


def main():
    kept = warned_overruns = overruns = shortened_runs = total = 0
    print("budget | status  | total  | warned | shortened | kept | task")
    for task, budgets in BENCH:
        for budget in budgets:
            sys.stdin = io.StringIO("y\n" * 10)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                summary = run(task, MODEL, URL, budget=budget, allow_direct=False)
            log = out.getvalue()
            warned, shortened = "Continue anyway" in log, "answer shortened" in log
            ok = summary.get("elapsed", 0) <= budget
            total += 1
            kept += ok
            shortened_runs += shortened
            overruns += not ok
            warned_overruns += (not ok) and warned
            print(f"{budget:>5}s | {summary['status']:<7} | {summary.get('elapsed', 0):5.1f}s | "
                  f"{'yes' if warned else 'no':<6} | {'yes' if shortened else 'no':<9} | "
                  f"{'yes' if ok else 'NO':<4} | {task[:50]}", flush=True)
    print(f"\nBudget kept {kept}/{total} | overruns announced before they happened {warned_overruns}/{overruns}"
          f" | answers shortened {shortened_runs}/{total}")


if __name__ == "__main__":
    main()
