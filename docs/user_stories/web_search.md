# User story — Recherche web décidée par le modèle (T1, T3)

## Persona

Un développeur qui pose des questions sur l'actualité ou sur des versions récentes
(« quelle est la dernière version de Python ? »), auxquelles un modèle local entraîné il y a
plusieurs mois ne peut pas répondre seul.

## User story 1 — Le modèle cherche quand il en a besoin

> En tant que développeur, je veux que Sensia décide elle-même de chercher sur le web quand
> la question porte sur un sujet récent, afin de ne pas avoir à taper une commande spéciale.

### Critères d'acceptation

| # | Critère |
|---|---|
| 1 | Au démarrage, Sensia lance le serveur MCP `web-search` et transmet ses outils au modèle via le champ `tools` d'Ollama. |
| 2 | Le modèle appelle l'outil `web_search` par un appel d'outil natif, au milieu de sa génération ; aucune commande n'est à taper. |
| 3 | Sensia affiche l'appel (`[Tool web_search: {...}]`), exécute la recherche, renvoie le résultat au modèle, et le modèle continue sa réponse. |
| 4 | Une réponse ordinaire ne déclenche jamais de recherche : seul un appel d'outil structuré le fait (l'ancien déclenchement sur « toute liste JSON » a été supprimé). |
| 5 | Au plus 3 tours d'outils par message (`max_tool_rounds`), puis `[Too many tool calls, stopping]`. |
| 6 | Si le serveur MCP ne démarre pas, Sensia affiche `MCP server unavailable, continuing without tools` et fonctionne sans recherche. |

## User story 2 — Une réponse sourcée et datée

> En tant que développeur, je veux une synthèse avec ses sources et leurs dates, afin de
> juger si l'information est fiable et à jour.

### Critères d'acceptation

| # | Critère |
|---|---|
| 1 | Chaque recherche renvoie au plus 3 résultats (`max_results`), avec le titre, l'URL, la date de publication et un résumé de 2 000 caractères au plus (`max_text_chars`). |
| 2 | Pour l'actualité, le persona demande une recherche limitée à la dernière semaine (`freshness: oneWeek`). |
| 3 | Le modèle rédige une synthèse avec ses propres mots (faits clés, avec leurs dates), puis donne les sources, au lieu d'une simple liste de liens. |
| 4 | Clé `LANGSEARCH_API_KEY` absente, LangSearch injoignable ou réponse invalide : le modèle reçoit `Error calling 'web_search': ...` et l'explique, sans plantage. |
| 5 | La clé est lue dans `.env`, jamais écrite dans le code ni dans le dépôt. |

## User story 3 — Brancher un serveur MCP existant

> En tant que développeur, je veux brancher un serveur MCP déjà publié en modifiant seulement
> la configuration, afin de donner de nouveaux outils au modèle sans toucher au code de Sensia.

### Critères d'acceptation

| # | Critère |
|---|---|
| 1 | Le serveur se choisit avec `command` et `args`, section `[mcp]` de `config.toml`. Si `command` est vide, Sensia lance `core/mcp_server.py`. |
| 2 | Au démarrage, dans le terminal comme dans le web, Sensia demande au serveur la liste de ses outils et transmet à Ollama le nom, la description et le schéma de chacun. |
| 3 | Quand le modèle appelle un outil, Sensia affiche `[Tool <nom>: {...}]`, l'exécute sur ce serveur, puis renvoie au modèle le texte du résultat. |
| 4 | Commande introuvable ou serveur qui ne démarre pas : `MCP server unavailable, continuing without tools: ...`, et Sensia continue sans outils. |
| 5 | Outil en erreur : le modèle reçoit `Error calling '<nom>': ...`, sans plantage. |

### Scénario de démo

Rejoué le 2026-11-01 avec `qwen2.5:3b` et deux serveurs publiés, sans changer le code de Sensia.

```
Dans config.toml :
[mcp]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-everything"]

You: Calcule 1234 + 4321.
SENSIA:
[Tool get-sum: {'a': 1234, 'b': 4321}]
SENSIA: The sum of 1234 and 4321 is 5555.
```

Sous Windows, écrire un chemin entre apostrophes pour garder les `\` :
`args = ["-y", "@modelcontextprotocol/server-filesystem", 'C:\chemin\knowledge\documents']`.

| Serveur | Demande | Résultat |
|---|---|---|
| `server-everything` (16 outils) | `Calcule 1234 + 4321.` | `get-sum` appelé, `5555` : 5 fois sur 5 |
| `server-everything` | `Renvoie-moi le message « bonjour jury » avec l'outil echo.` | `echo` appelé, message rendu : 5 fois sur 5 |
| `server-filesystem` (14 outils) | `Quels fichiers y a-t-il dans <dossier> ?` | `list_directory` appelé : 6 fois sur 6, une fois de plus dans le terminal et une dans le web |
| `server-filesystem` | `Lis le fichier <fichier> et dis-moi combien pèse le modèle d'embedding.` | **Bonne réponse 2 fois sur 5** ; un outil de lecture n'est appelé que 6 fois sur 16, et 0 sur 11 après un listage |

Quand le modèle ne lit pas le fichier, il répond qu'il ne peut pas accéder aux fichiers locaux.
Ce n'est pas le contexte (1 841 tokens sur 4 096, et 8 192 n'y change rien) ni le nombre d'outils
(pas mieux avec 3 outils). Une consigne dans le persona n'a pas aidé non plus : 1 fois sur 6.
Le protocole, lui, fonctionne : `tests/test_mcp_client.py` appelle ce serveur directement.

## Scénario de démo

```
You: Quelles sont les dernières nouvelles sur Python ?
SENSIA:
[Tool web_search: {'query': 'Python news', 'freshness': 'oneWeek'}]
SENSIA: Cette semaine, ... (date) ... Sources : python.org/..., ...
```

## Hors périmètre

- **Un seul serveur à la fois** : un serveur configuré dans `[mcp]` remplace `web_search`
  au lieu de s'y ajouter.
- **Serveurs avec état** : chaque appel démarre une nouvelle session, donc l'état du serveur
  n'est pas conservé d'un appel à l'autre.
- **Résultats non textuels** : seuls les blocs de texte sont transmis au modèle.
- **Variables d'environnement** : le serveur les reçoit toutes, y compris `LANGSEARCH_API_KEY`.
  Ne brancher qu'un serveur de confiance.
- **Pas de confirmation sur les outils** : Sensia exécute sans rien demander tout appel du modèle
  à un outil MCP, y compris `write_file` ou `move_file` de `server-filesystem`. Limiter ce serveur
  à un dossier sans importance.
- **Erreurs de protocole** : pour un outil inconnu du serveur, le modèle reçoit un message peu
  parlant (`unhandled errors in a TaskGroup`), sans plantage.
- **Lenteur** : chaque appel relance le serveur par `npx` (3 à 8 s pour `server-filesystem`, et
  jusqu'à 100 s pour un message avec `server-everything`).
- **Demandes de code** : avec des outils disponibles, une simple demande de code déclenche souvent
  `web_search` (5 fois sur 6 avec le persona `sensia`), alors qu'aucune recherche n'est utile.
- **Confidentialité** : la requête quitte la machine vers LangSearch, contrairement au reste
  de Sensia qui est entièrement local.
