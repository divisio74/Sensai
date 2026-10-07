# Guide de Sensia

Document de test pour le RAG. Il contient des informations précises sur le projet, que le modèle ne peut pas connaître sans lire ce fichier.

## Lancer Sensia

Sensia se lance avec la commande `python3 main.py`.
Le modèle par défaut est `qwen2.5:3b`. On peut en choisir un autre avec l'option `--model`.
L'adresse par défaut d'Ollama est `http://localhost:11434/api/chat`. On peut la changer avec l'option `--url`.

Au démarrage, Sensia vérifie que le serveur Ollama répond et que le modèle existe. Si ce n'est pas le cas, le programme affiche une erreur et s'arrête.

## Les commandes

- `quit` : quitte Sensia.
- `/code <tâche>` : Sensia écrit du code Python pour la tâche, l'exécute dans la sandbox et le corrige s'il y a une erreur.
- `/rag <question>` : Sensia répond en s'appuyant sur les documents du dossier `knowledge/`.

## La sandbox

La sandbox exécute le code généré dans un processus Python séparé.
Un code qui tourne plus de 10 secondes est arrêté automatiquement.
La boucle de correction fait au maximum 3 tentatives. Si le code échoue 3 fois, Sensia abandonne et le dit à l'utilisateur.
Si le modèle propose deux fois le même code, la boucle le détecte et lui demande d'essayer une autre stratégie.

## Le RAG

Les documents doivent être placés dans le dossier `knowledge/`.
Seuls les fichiers `.md`, `.txt` et `.py` sont lus.
Les documents sont découpés en morceaux de 500 caractères, avec un chevauchement de 50 caractères.
Le modèle d'embedding utilisé est `nomic-embed-text`. Il pèse 274 Mo.

## Gestion des erreurs

Si Ollama s'arrête pendant une réponse, Sensia affiche un message et continue à fonctionner.
Un appui sur Ctrl+C pendant une réponse arrête seulement la réponse en cours, pas le programme.
Si Ollama ne répond plus pendant 120 secondes, la requête est abandonnée.


