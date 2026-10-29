# User story — Configuration et paramètres de génération

## Persona

Un membre de l'équipe, ou un utilisateur avancé, qui veut adapter Sensia à sa machine et à
son usage (un modèle plus gros, un seuil RAG plus strict, plus de tentatives pour le code)
sans chercher les valeurs dans le code.

## User story 1 — Tout régler dans un seul fichier

> En tant que membre de l'équipe, je veux trouver tous les réglages de Sensia dans un seul
> fichier, afin de les changer sans modifier le code ni risquer de casser une fonctionnalité.

### Critères d'acceptation

| # | Critère |
|---|---|
| 1 | Tous les réglages sont dans `config.toml`, à la racine, regroupés par fonctionnalité : `[ollama]`, `[generation]`, `[chat]`, `[rag]`, `[code]`, `[web_search]`, `[web]`, `[timepred]`. |
| 2 | Chaque valeur est commentée : son rôle et son unité. |
| 3 | Les valeurs que le jury avait relevées comme codées en dur viennent de ce fichier : seuil de pertinence RAG, `max_output`, délais d'expiration (Ollama, sandbox, LangSearch, étapes de `/fast`), nombre d'itérations. |
| 4 | `--model` et `--url` remplacent les valeurs de `[ollama]` pour une session, sans modifier le fichier. |
| 5 | Fichier absent ou mal écrit : Sensia s'arrête avec `Configuration file not found: ...` ou `Invalid configuration file ...: <erreur>`, au lieu d'une trace Python. |

## User story 2 — Des paramètres de génération adaptés à chaque usage

> En tant qu'utilisateur, je veux que Sensia génère du code et des réponses documentaires de
> façon stable, et des conversations plus variées, afin d'avoir le bon comportement selon
> ce que je demande.

### Critères d'acceptation

| # | Critère |
|---|---|
| 1 | Chaque appel à `/api/chat` envoie des `options` à Ollama : les valeurs communes de `[generation]`, remplacées par celles de l'usage concerné. |
| 2 | Températures par défaut : conversation 0,7 ; code (`/code`, étapes `code` de `/fast`) 0,2 ; réponse RAG 0,1 ; traduction RAG 0 ; classement du plan de `/fast` 0 ; étapes texte de `/fast` 0,7. |
| 3 | La taille de contexte (`num_ctx = 4096`) est la même pour tous les usages : la changer d'un appel à l'autre forcerait Ollama à recharger le modèle. |
| 4 | Ajouter un paramètre Ollama (par exemple `top_p` ou `seed`) dans une section suffit à l'envoyer, sans toucher au code. |

## Vérification

Les `options` réellement envoyées ont été vérifiées en interceptant les requêtes HTTP :
`chat` 0,7 · `rag` 0,1 · `code` 0,2 · `translate` 0 · `plan` 0 · `task` 0,7, toujours avec
`num_ctx = 4096`.

## Hors périmètre

- Pas de rechargement à chaud : un changement de `config.toml` s'applique au lancement suivant.
- Les constantes internes des algorithmes (par exemple les coefficients de la fusion de
  `/fast`) restent dans le code, à côté de leur explication.
