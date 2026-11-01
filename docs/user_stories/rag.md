# User story — Réponses à partir de mes documents (R1, R2)

## Persona

Un développeur qui a sa propre documentation (guides internes, notes, code) et qui veut
interroger Sensia dessus : le modèle ne la connaît pas, et elle ne doit pas sortir de sa
machine.

## User story 1 — Indexer mes documents

> En tant que développeur, je veux indexer les documents d'un dossier en une commande, afin
> que Sensia puisse ensuite y chercher des réponses.

### Critères d'acceptation

| # | Critère |
|---|---|
| 1 | `/index` lit les fichiers `.md`, `.txt` et `.py` du dossier `knowledge/documents/` (réglable dans `config.toml`, section `[rag]`). |
| 2 | Chaque document est découpé en morceaux de 500 caractères qui se chevauchent de 100 caractères (`chunk_size`, `overlap`). Chaque morceau garde son fichier et son numéro de ligne. |
| 3 | Les morceaux sont transformés en vecteurs par `nomic-embed-text`, un modèle d'embedding distinct du modèle de conversation, avec le préfixe `search_document:` attendu par ce modèle. |
| 4 | L'index est enregistré localement dans `knowledge/index/index.json` : aucun document n'est envoyé à l'extérieur. |
| 5 | Sensia affiche la progression (`32/120 chunks embedded`), puis `N chunks indexed.` |
| 6 | Dossier vide : `No documents found in knowledge/documents/`. Fichier illisible : `Cannot read <fichier>, skipped`, et les autres sont indexés. |

## User story 2 — Poser une question et voir les sources

> En tant que développeur, je veux poser une question sur mes documents et savoir d'où vient
> la réponse, afin de pouvoir la vérifier dans le document d'origine.

### Critères d'acceptation

| # | Critère |
|---|---|
| 1 | `/rag <question>` traduit d'abord la question en anglais (température 0), puis la transforme en vecteur avec le préfixe `search_query:`. |
| 2 | Les 3 morceaux les plus proches sont gardés (`top_k`), à condition que leur similarité atteigne 0,65 (`threshold`). |
| 3 | Le modèle répond uniquement à partir de ces extraits, dans la langue de la question, avec une température basse (0,1, section `[generation.rag]`). |
| 4 | Si la réponse n'est pas dans les extraits, le modèle dit qu'il ne sait pas au lieu d'inventer. |
| 5 | Les sources sont affichées sous la réponse : `Sources: <fichier> - line <n> - score <s>`. |
| 6 | Aucun extrait au-dessus du seuil : `Nothing relevant found in the documents`, et aucune réponse n'est générée. |
| 7 | Sans index : `No index found (run /index first) or Ollama is not reachable.` |
| 8 | Dans l'historique, la question est gardée telle que l'utilisateur l'a écrite, pas le long prompt d'extraits : la suite de la conversation reste lisible. |

## User story 3 — Ne garder que les extraits assez proches

> En tant que développeur, je veux que chaque extrait reçoive un score et que je puisse régler
> le niveau exigé, afin que le modèle ne réponde jamais à partir d'extraits hors sujet.

### Critères d'acceptation

| # | Critère |
|---|---|
| 1 | Chaque morceau de l'index reçoit un score : sa similarité cosinus avec la question. |
| 2 | Les morceaux sont classés du score le plus haut au plus bas. Seuls les `top_k` premiers sont examinés, et ceux sous `threshold` sont écartés : le modèle peut donc recevoir moins de 3 extraits. |
| 3 | `top_k` et `threshold` se règlent dans la section `[rag]` de `config.toml`, sans toucher au code ; la nouvelle valeur s'applique au redémarrage de Sensia. |
| 4 | Le prompt ne contient que les extraits gardés, numérotés, avec leur fichier et leur ligne. |
| 5 | Le score de chaque extrait gardé est affiché à deux décimales sous la réponse. |

### Scénario de démo

```
Avec threshold = 0.65 :
You: /rag Quels fichiers sont lus par le RAG ?
Sources: knowledge/documents/sensia_guide.md - line 27 - score 0.71

Avec threshold = 0.80, après redémarrage :
You: /rag Quels fichiers sont lus par le RAG ?
Nothing relevant found in the documents
```

## Scénario de démo

```
You: /index
5/5 chunks embedded
5 chunks indexed.
You: /rag Quels fichiers sont lus par le RAG ?
SENSIA: Seuls les fichiers .md, .txt et .py sont lus...
Sources: knowledge/documents/sensia_guide.md - line 27 - score 0.71
You: /rag Quelle est la capitale du Pérou ?
Nothing relevant found in the documents
```

## Hors périmètre

- Pas de reranking ni de filtrage par métadonnées (date, auteur) : de R2, seul le score par extrait est couvert.
- L'index est entièrement recalculé à chaque `/index`.
