# User story — Code exécuté et corrigé automatiquement (T2, A1)

## Persona

Un développeur qui veut du code Python qui **tourne**, pas seulement du code qui a l'air
correct, et qui ne veut pas copier-coller lui-même chaque erreur pour la faire corriger.

## User story 1 — Obtenir du code qui s'exécute

> En tant que développeur, je veux que Sensia écrive le code, l'exécute et corrige ses
> propres erreurs, afin de recevoir un programme qui tourne déjà.

### Critères d'acceptation

| # | Critère |
|---|---|
| 1 | `/code <tâche>` demande au modèle uniquement du code Python dans un bloc ```` ```python ````, avec une température basse (0,2, section `[generation.code]`). |
| 2 | Le code extrait est exécuté dans un processus séparé (`python3 -c`), jamais avec `exec()` dans le processus de Sensia. |
| 3 | En cas d'erreur, la trace (`stderr`) est renvoyée au modèle avec la consigne de corriger, jusqu'à 3 tentatives (`max_iterations` dans `config.toml`). |
| 4 | Un code qui dépasse 10 s est arrêté (`execution_timeout`) et le modèle reçoit le message `Timeout: the code did not finish within 10 seconds. Retry with a lower algorithmic complexity`. |
| 5 | Les sorties sont tronquées à 1 500 caractères (`max_output`) pour ne pas saturer le contexte. |
| 6 | En cas de réussite : `Succeeded in N attempt(s)`, puis le code et sa sortie réelle sont affichés. |
| 7 | Après `/code`, le code et sa sortie sont dans l'historique : on peut demander « explique ce que tu viens de faire ». |

## User story 2 — Ne pas tourner en rond

> En tant que développeur, je veux que Sensia s'arrête ou change d'approche quand elle
> répète la même erreur, afin de ne pas attendre des tentatives inutiles.

### Critères d'acceptation

| # | Critère |
|---|---|
| 1 | Chaque code est comparé aux précédents par son arbre syntaxique (AST) : un code identique, même reformaté ou commenté autrement, n'est pas réexécuté. |
| 2 | En cas de répétition, le modèle reçoit la consigne d'essayer une autre stratégie, ou de dire que la demande est impossible. |
| 3 | Après 3 tentatives sans succès : `Max try reached with 3 max iterations`, et le modèle est informé de l'échec pour l'expliquer à l'utilisateur, au lieu de présenter un code faux. |
| 4 | Si le modèle ne répond pas : statut `unavailable`, sans plantage. |
| 5 | Trois statuts distincts sont renvoyés : `success`, `failed`, `unavailable`. |

## Scénario de démo

```
You: /code compute fib(42) with naive recursion and print it
===== Attempt 1/3 =====
Failure: Timeout: the code did not finish within 10 seconds...
===== Attempt 2/3 =====
...
Succeeded in 3 attempt(s)          → mesuré : 36,8 s, mémoïsation au 3e essai
```

## Hors périmètre

- **Le sandbox isole le processus, pas la machine** : le code tourne avec les droits de
  l'utilisateur et peut lire ses fichiers ou ouvrir une connexion réseau (voir les limites
  du README).
- `exit_code == 0` prouve que le code n'a pas planté, pas qu'il est juste.
- Seul Python est exécuté.
