# User story — Interface web (X1)

## Persona

Un utilisateur qui préfère une fenêtre de discussion à un terminal, par exemple pour une
démonstration ou pour lire plus confortablement des blocs de code.

## User story 1 — Discuter dans le navigateur

> En tant qu'utilisateur, je veux discuter avec Sensia dans mon navigateur, avec la réponse
> qui s'écrit en direct, afin de profiter de Sensia sans terminal.

### Critères d'acceptation

| # | Critère |
|---|---|
| 1 | `python3 main.py --web` démarre le serveur sur `http://127.0.0.1:4040` (`host`, `port` dans `config.toml`). |
| 2 | La réponse s'affiche au fur et à mesure de la génération (streaming HTTP). |
| 3 | Les blocs de code (```` ``` ````) sont affichés dans un cadre à part, le reste en paragraphes. |
| 4 | La conversation est gardée côté serveur : recharger la page réaffiche tout l'historique. |
| 5 | `--model` et `--url` fonctionnent comme dans le terminal. Le persona et le profil sont ceux du compte connecté. |
| 6 | Serveur arrêté : `The server is not reachable.` ; Ollama arrêté : `[Sensai could not answer (is Ollama running?)]`, et la page reste utilisable. |
| 7 | Sans connexion, `/` affiche la page de connexion, qui permet aussi de créer un compte. Les routes de discussion répondent `401`. Le bouton de déconnexion ramène à cette page. |

## User story 2 — Les mêmes commandes que dans le terminal

> En tant qu'utilisateur, je veux utiliser les commandes de Sensia depuis l'interface web,
> afin de ne pas perdre de fonctionnalités en quittant le terminal.

### Critères d'acceptation

| # | Critère |
|---|---|
| 1 | `/help`, `/clear`, `/undo`, `/retry`, `/index`, `/rag`, `/code`, `/persona` et `/remember` passent par le même code que dans le terminal (`core/commands.py`) : la logique n'est pas dupliquée. |
| 2 | Le bouton *New chat* vide la conversation, comme `/clear`. |
| 3 | `/code` affiche le code et sa sortie réelle dans la page. |
| 4 | Le résultat d'une commande reste affiché à sa place dans la conversation après un rechargement de la page. |

## Hors périmètre

- `/fast` et la recherche web ne sont disponibles que dans le terminal : dans la page, `/fast`
  part vers le modèle comme un message ordinaire.
- Une seule session : un seul compte connecté et une seule conversation, partagés par tous les
  onglets ouverts.
