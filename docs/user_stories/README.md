# User stories et traçabilité

## Utilisateur cible

Un **développeur qui travaille en local**, sur sa propre machine, souvent sans carte
graphique : il veut un assistant qui ne fait pas sortir son code ni ses documents, qui
exécute et vérifie le code qu'il propose, et qui s'adapte à son matériel et à ses habitudes.
D'où le choix d'un petit modèle (`qwen2.5:3b`) et d'un fonctionnement entièrement local,
à l'exception assumée de la recherche web.

## Les stories

| Fichier | Fonctionnalité | Stories |
|---|---|---|
| [chat.md](chat.md) | Chatbot en ligne de commande | 2 |
| [profile.md](profile.md) | Profil utilisateur et mémoire | 2 |
| [persona.md](persona.md) | Personas et changement en cours de session | 2 |
| [rag.md](rag.md) | Réponses à partir de mes documents | 2 |
| [code.md](code.md) | Code exécuté, corrigé et isolé dans Docker | 3 |
| [web_search.md](web_search.md) | Recherche web décidée par le modèle | 2 |
| [web.md](web.md) | Interface web | 2 |
| [dev.md](dev.md) | Tâches avec un budget de temps (`/fast`) | 3 |
| [config.md](config.md) | Configuration et paramètres de génération | 2 |

Chaque story a des critères d'acceptation vérifiables : un message exact, une valeur de
`config.toml`, ou un comportement observable dans le terminal.

## Traçabilité : du sujet au code

| Fonctionnalité du sujet | Besoin de l'utilisateur | Stories | Implémentation | Vérification |
|---|---|---|---|---|
| **B1** Chatbot CLI | Discuter avec un modèle local, en direct, sans quitter le terminal | [chat.md](chat.md) 1, 2 | `main.py`, `core/llm.py`, `core/commands.py` | Scénario de démo de la story |
| **M1** Profil persistant | Ne pas répéter qui je suis à chaque session | [profile.md](profile.md) 1, 2 | `persona/user.md`, `core/persona.py`, `/remember` | Scénario de démo de la story. *L'historique des conversations n'est pas encore sauvegardé entre sessions.* |
| **A5** Persona | Changer de type d'aide sans perdre le contexte | [persona.md](persona.md) 1, 2 | `persona/personas/*.md`, `core/persona.py`, `/persona` | Scénario de démo de la story |
| **R1** RAG | Interroger ma documentation, qui ne sort pas de ma machine | [rag.md](rag.md) 1, 2 | `rag/ingest.py`, `rag/embed.py`, `rag/store.py`, `rag/retrieve.py` | Scénario de démo de la story |
| **R2** RAG avancé (score par extrait) | Ne recevoir que des extraits pertinents, avec leurs sources | [rag.md](rag.md) 2 | seuil `threshold`, scores et sources dans `rag/retrieve.py` | Scénario de démo (question hors sujet refusée) |
| **T2** Exécution sandboxée | Recevoir du code qui tourne, sans mettre ma machine en danger | [code.md](code.md) 1, 3 | `tools/sandbox.py` (conteneur Docker), `core/code_extract.py` | 9 critères d'isolation testés un par un (`/home` vide, clé absente, réseau coupé...) ; `fib(42)` corrigé en 2 tentatives |
| **A1** Boucle de raisonnement | Que l'agent corrige ses erreurs et ne tourne pas en rond | [code.md](code.md) 1, 2 | `core/boucle.py` (correction, détection de stagnation par AST) | README, *Measurements* : stagnation, 1 exécution au lieu de 3 |
| **T1** MCP | Que le modèle choisisse lui-même l'outil à appeler | [web_search.md](web_search.md) 1 | `core/mcp_server.py`, `core/mcp_client.py`, `main.py` | Scénario de démo de la story |
| **T3** Recherche web | Répondre sur l'actualité, avec des sources datées | [web_search.md](web_search.md) 1, 2 | outil `web_search` (LangSearch) | Scénario de démo de la story |
| **X1** Interface web | Utiliser Sensia sans terminal | [web.md](web.md) 1, 2 | `web.py`, `web/` | Scénario de démo de la story |
| **T5** Sortie structurée | Un plan fiable, que le code peut lire sans erreur | [dev.md](dev.md) 1 | schéma JSON imposé à Ollama (`timepred/plan.py`) | 36 classements sur 36 au format valide |
| **A3** Humain dans la boucle | Ne rien lancer d'irréversible ou de trop long sans mon accord | [dev.md](dev.md) 1, 2 | confirmations `[y/N]` dans `main.py` et `timepred/budget.py` | Banc de budget : 4 dépassements sur 4 annoncés avant d'arriver |
| `/fast` : budget de temps (proposition de l'équipe) | Savoir avant et pendant si une tâche tient dans mon délai | [dev.md](dev.md) 1, 2, 3 | `timepred/` | Banc de 24 exécutions (budget tenu 20 fois) ; backtest de 70 exécutions |
| Configuration (transverse) | Régler Sensia sans toucher au code ; des générations adaptées à l'usage | [config.md](config.md) 1, 2 | `config.toml`, `core/config.py` | `options` envoyées à Ollama vérifiées par interception des requêtes |

## Ce qui reste à faire

- Des **tests automatisés** pour le RAG et la boucle de code : aujourd'hui, la vérification
  passe surtout par les scénarios de démo et les mesures du README.
- La **sauvegarde de l'historique** entre sessions, pour couvrir entièrement M1.
