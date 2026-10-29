# User story — Chatbot en ligne de commande (B1)

## Persona

Un développeur qui travaille dans son terminal, sur sa propre machine, et qui veut
discuter avec un modèle local sans quitter son environnement ni envoyer ses questions à un
service en ligne.

## User story 1 — Discuter avec un modèle local, en direct

> En tant que développeur, je veux poser mes questions dans le terminal et voir la réponse
> s'écrire au fur et à mesure, afin de lire le début de la réponse sans attendre la fin de la
> génération.

### Critères d'acceptation

| # | Critère |
|---|---|
| 1 | `python3 main.py` démarre une conversation avec le modèle de `config.toml` (`qwen2.5:3b` par défaut). `--model` et `--url` remplacent ces valeurs sans toucher au code. |
| 2 | La réponse s'affiche token par token (appel `/api/chat` d'Ollama en streaming), précédée du nom du persona (`SENSIA: ...`). |
| 3 | L'historique de la session est conservé : une information donnée au premier message est retrouvée au suivant. |
| 4 | Aucun framework LLM n'est utilisé : les appels sont des requêtes HTTP directes vers Ollama. |
| 5 | Si Ollama est injoignable au démarrage, Sensia affiche `Server unreachable` et s'arrête proprement, sans trace d'erreur Python. |
| 6 | Si Ollama tombe pendant une réponse, Sensia affiche `Connection lost with Ollama`, retire la question sans réponse de l'historique, et la conversation continue. |
| 7 | `Ctrl+C` pendant une réponse affiche `[interrupted]` et garde la partie déjà écrite ; `Ctrl+C` ou `Ctrl+D` à l'invite affiche `Goodbye`. |

## User story 2 — Garder la main sur la conversation

> En tant que développeur, je veux annuler, relancer ou repartir de zéro, afin de corriger
> une question mal posée ou une mauvaise réponse sans redémarrer Sensia.

### Critères d'acceptation

| # | Critère |
|---|---|
| 1 | `/help` affiche la liste des commandes disponibles. |
| 2 | `/clear` vide la conversation (le prompt système est gardé) et affiche `Conversation cleared.` |
| 3 | `/undo` retire la dernière question et sa réponse et affiche `Last exchange removed.` ; sans échange, il affiche `Nothing to undo.` |
| 4 | `/retry` génère une nouvelle réponse à la dernière question ; si le modèle ne répond pas, l'ancienne réponse est gardée. |
| 5 | Une commande inconnue (`/truc`) affiche `Unknown command, type /help`, sans être envoyée au modèle. |
| 6 | `quit` quitte Sensia. |

## Scénario de démo

```
python3 main.py
You: Je m'appelle Pierre et je code en Python.
SENSIA: ...
You: Quel langage j'utilise ?
SENSIA: ... Python ...            → l'historique est gardé
You: /undo
Last exchange removed.
You: /truc
Unknown command, type /help
```

## Hors périmètre

- L'historique n'est pas sauvegardé entre deux sessions (seul le profil utilisateur l'est).
- La taille du contexte n'est pas encore comptée ni plafonnée.
