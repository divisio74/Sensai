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
| 2 | Le code extrait est exécuté hors du processus de Sensia, jamais avec `exec()` : dans un conteneur Docker jetable (voir la story 3), ou dans un processus local si Docker est absent. |
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

## User story 3 — Ne pas mettre ma machine en danger

> En tant que développeur, je veux que le code écrit par le modèle ne puisse ni lire mes
> fichiers ni mes secrets, ni contacter Internet, ni saturer ma machine, afin de pouvoir lancer
> `/code` sans relire chaque programme avant.

### Critères d'acceptation

| # | Critère |
|---|---|
| 1 | Avec `sandbox = "docker"` (par défaut), chaque exécution a lieu dans un conteneur `python:3.12-slim` supprimé juste après (`--rm`). |
| 2 | Les fichiers de l'utilisateur sont invisibles : `os.listdir('/home')` renvoie `[]`. |
| 3 | Les secrets ne passent pas : `LANGSEARCH_API_KEY` est absente de l'environnement du code, alors que Sensia l'a chargée. |
| 4 | Pas de réseau : toute connexion échoue avec `Network is unreachable`. |
| 5 | Le système de fichiers est en lecture seule (`Read-only file system`), sauf un `/tmp` de 64 Mo en mémoire. |
| 6 | Le code tourne sous l'utilisateur `nobody`, sans privilège (`--cap-drop ALL`, `no-new-privileges`). |
| 7 | Les ressources sont bornées : au-delà de 256 Mo, le code est tué et le modèle reçoit `Killed: the code exceeded the memory limit of the sandbox (256m)` ; au-delà de 64 processus, la création échoue ; au-delà du délai, le conteneur est arrêté. Aucun conteneur ne reste après l'exécution. |
| 8 | Ces limites sont réglables dans `config.toml`, section `[code.docker]`. |
| 9 | Sans Docker, Sensia affiche `[sandbox] Docker unavailable: the code runs in a local process, NOT isolated.` et exécute le code dans un processus durci (dossier temporaire, environnement sans la clé) ; avec `fallback_to_process = false`, elle refuse d'exécuter. |

## Scénarios de démo

```
You: /code compute fib(42) with naive recursion and print it
===== Attempt 1/3 =====
Failure: Timeout: the code did not finish within 10 seconds...
===== Attempt 2/3 =====
Succeeded in 2 attempt(s)          → mesuré : 18 s, algorithme corrigé au 2e essai

You: /code Print the list of folders in /home, then print True or False depending on whether the environment variable LANGSEARCH_API_KEY exists
Succeeded in 1 attempt(s)
Output: []
False                              → ni les dossiers, ni la clé ne sont visibles
```

## Vérification

Mesuré le 2026-10-29 : les 9 critères de la story 3 ont été testés un par un (`/home` vide,
clé absente, réseau coupé, lecture seule, boucle infinie arrêtée, 400 Mo tués à 256 Mo, bombe de
processus bloquée après 62, aucun conteneur restant, repli sans Docker). Coût d'une exécution :
0,2 à 0,5 s.

## Hors périmètre

- Un conteneur partage le noyau de la machine : il protège contre un code maladroit ou
  indiscret, pas contre une attaque qui exploiterait une faille du noyau (il faudrait une
  machine virtuelle).
- L'image ne contient que la bibliothèque standard : un code qui importe `numpy` échoue.
- `exit_code == 0` prouve que le code n'a pas planté, pas qu'il est juste.
- Seul Python est exécuté.
