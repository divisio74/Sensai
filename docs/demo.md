# Script de démo — Sensia

**Durée** : environ 12 minutes (15 avec l'interface web).
**Le fil rouge** : un développeur Python, sur son portable sans carte graphique, utilise Sensia
pendant une journée de travail. Chaque acte répond à un besoin et montre une fonctionnalité du
sujet. Les commandes sont à taper telles quelles ; la colonne « On doit voir » dit quoi montrer
au jury.

---

## Avant la démo

À faire la veille, puis à revérifier 10 minutes avant :

- [ ] `pip install -r requirements.txt` (les paquets `mcp`, `fastapi` et `uvicorn` sont nécessaires).
- [ ] `ollama list` affiche `qwen2.5:3b` et `nomic-embed-text`.
- [ ] `docker pull python:3.12-slim` est fait, et `docker ps` répond sans `sudo`.
- [ ] `.env` contient `LANGSEARCH_API_KEY=...` (pour l'acte 4).
- [ ] **Créer le compte de démo** : `python3 main.py`, saisir un e-mail, répondre `y` à `No account for this email. Create one?`, choisir un mot de passe (il ne s'affiche pas), le persona `sensia`, puis se présenter, par exemple `My name is Pierre.`. Le compte et le profil sont dans `data/`, local et ignoré par git.
- [ ] `python3 main.py` démarre sans erreur et accepte ce compte, puis `quit`.
- [ ] **Faire chauffer le modèle** : lancer une fois `/fast 30 Écris un mail de relance pour lundi`. Sinon, le premier appel coûte environ 10 s de chargement.
- [ ] **Remplir l'historique de `/fast`** : `knowledge/history/` est ignoré par git, donc il est vide sur un nouveau clone. Lancer deux fois les 3 commandes `/fast` de l'acte 6 et répondre `y` aux questions. Sinon, l'acte 6 ne suit pas ce script : `Similar past tasks: 0/0`, et la tâche est annulée dès le départ si on répond `n`.
- [ ] Ne pas vider `knowledge/history/` : c'est lui qui rend les prédictions de `/fast` précises.
- [ ] Fermer les applications lourdes : sur CPU, la vitesse dépend de la mémoire disponible.

---

## Acte 1 — Un assistant local qui me connaît (B1, M1)

*Besoin : discuter avec un modèle local, sans que mon code sorte de ma machine, et ne pas répéter qui je suis.*

| Je tape | On doit voir | Ce que ça montre |
|---|---|---|
| `python3 main.py`, puis l'e-mail et le mot de passe du compte de démo | `Email:`, `Password:`, puis `You:` | Démarrage, vérification d'Ollama, connexion |
| `Bonjour, qui es-tu et comment je m'appelle ?` | `SENSIA: ...` qui s'écrit mot à mot, et qui donne ton prénom | Streaming, persona, profil injecté dès le premier message |
| `/remember Je code surtout en Python` | `Fact remembered.` | Mémoire persistante |
| `Quel langage j'utilise ?` | `... Python ...` | Le fait est utilisé tout de suite |

> **À dire** : « Tout tourne en local sur Ollama, sans framework LLM : uniquement des appels HTTP.
> Le profil est un fichier Markdown injecté dans le prompt système. »

---

## Acte 2 — Interroger ma propre documentation (R1, R2)

*Besoin : poser des questions sur ma documentation, que le modèle ne connaît pas, et savoir d'où vient la réponse.*

| Je tape | On doit voir | Ce que ça montre |
|---|---|---|
| `/index` | `5/5 chunks embedded` puis `5 chunks indexed.` | Découpage, embeddings `nomic-embed-text`, index local |
| `/rag Que se passe-t-il si le code tourne en boucle dans le sandbox ?` | « arrêté au bout de 10 secondes... 3 tentatives » et `Sources: knowledge/documents/sensia_guide.md - line 17 - score 0.75` | Réponse tirée du document, avec sa source et son score |
| `/rag Combien pèse le modèle d'embedding ?` | `274 MB`, avec sa source | Un fait précis que le modèle ne peut pas inventer |
| `/rag Quelle est la capitale du Pérou ?` | `Nothing relevant found in the documents` | Le seuil de pertinence (0,65) : pas de réponse hors des documents |

> **À dire** : « La question est traduite en anglais avant l'embedding, parce que nomic-embed-text
> est surtout entraîné sur de l'anglais, et la réponse revient dans la langue de la question.
> Les préfixes `search_query` et `search_document` sont ceux attendus par le modèle. »

---

## Acte 3 — Passer en mode développeur sans perdre le fil (A5)

*Besoin : changer de type d'aide sans réexpliquer mon contexte.*

| Je tape | On doit voir | Ce que ça montre |
|---|---|---|
| `/persona dev` | `Switched to SENSIA — developer mode (conversation kept)` | Changement de persona en cours de session |
| `Rappelle-moi quel langage j'utilise` | `SENSIA — developer mode: ... Python ...` | Historique et profil conservés |

> **À dire** : « Seul le prompt système change ; tout le reste de la conversation est gardé.
> Un nouveau persona, c'est un nouveau fichier Markdown, sans une ligne de Python. »

Ce changement ne dure que la session : à la connexion suivante, Sensia reprend le persona du compte.

---

## Acte 4 — Le modèle choisit ses outils (T1, T3)

*Besoin : répondre sur l'actualité, qu'un modèle local ne connaît pas.*

| Je tape | On doit voir | Ce que ça montre |
|---|---|---|
| `Quelles sont les nouveautés de Python cette semaine ?` | `[Tool web_search: {...}]`, puis une synthèse datée et ses sources | Appel d'outil natif décidé par le modèle, serveur MCP |

> **À dire** : « Personne n'a tapé de commande : le modèle a décidé d'appeler l'outil `web_search`
> exposé par notre serveur MCP. C'est la seule donnée qui quitte la machine, et c'est documenté
> dans les limites. »

**Sans clé LangSearch, ne pas jouer cet acte** : le modèle appelle bien l'outil, mais il reçoit une
erreur et peut ensuite inventer une actualité (vu dans le web : une « nouveauté » de 2023).

---

## Acte 5 — Du code qui tourne vraiment (T2, A1)

*Besoin : recevoir du code qui s'exécute, pas seulement du code plausible.*

| Je tape | On doit voir | Ce que ça montre |
|---|---|---|
| `/code Write a Python function that returns the first 15 Fibonacci numbers and print them` | `Succeeded in 1 attempt(s)` et la vraie sortie `[0, 1, 1, 2, 3, 5, 8, ...]` | Génération, exécution dans un processus séparé |
| `/code Compute fib(42) with naive recursion and print it` | `Attempt 1/3`, `Failure: Timeout: the code did not finish within 10 seconds...`, puis `Succeeded in 2 attempt(s)` et `267914296` (environ 18 s) | La boucle de correction : l'erreur réelle est renvoyée au modèle, qui change d'algorithme |
| `Explique pourquoi la deuxième tentative est plus rapide que la première` | récursif contre itératif | Le résultat de `/code` est dans l'historique |
| `/code Print the list of folders in /home, then print True or False depending on whether the environment variable LANGSEARCH_API_KEY exists` | `Output: []` puis `False` | Le code tourne dans un conteneur Docker : il ne voit ni tes fichiers, ni ta clé, ni Internet |

> **À dire** : « Le modèle ne se juge pas lui-même : c'est la vraie trace de l'interpréteur qui lui
> est renvoyée. Si le modèle repropose le même code, on le détecte en comparant les arbres
> syntaxiques, et on ne le réexécute pas. Et ce code tourne dans un conteneur jetable : sans
> réseau, en lecture seule, sous `nobody`, limité à 256 Mo et 64 processus, pour 0,2 à 0,5 s de
> surcoût seulement. Sur la machine de mi-parcours, ce même `/home` listait nos dossiers. »

---

## Acte 6 — Tenir un budget de temps (`/fast` : T5, A3)

*Besoin : savoir avant et pendant si une tâche tient dans mon délai.*

| Je tape | On doit voir | Ce que ça montre |
|---|---|---|
| `/fast 30 Écris un mail de relance pour lundi` | `PLAN [write]`, `Learned speed: ~19 tokens/s`, `Initial prediction: ~7s`, la ligne `⏳` qui bouge, `Budget: 30s -> kept` | Plan construit en Python, prédiction apprise sur cette machine |
| `/fast 8 Explain how HTTP caching works and compare it with a CDN for a beginner audience` | `✂ answer shortened to ~65 words to fit the budget (~6s instead of ~12s)`, puis `Budget: 8s -> kept`, ou `Continue anyway? [y/N]` → `n` si le temps manque | Sensia réduit la tâche à l'essentiel pour tenir le budget, et le dit quand ça ne suffit pas |
| `/fast 15 Write a Python class for a bank account with deposit and withdraw, run 3 operations, then explain how it works` | `PLAN [code → explain]`, code vérifié, puis `Budget: 15s -> updated prediction: 18s`, `Continue anyway? [y/N]` → répondre `n` | Revérification en cours de route ; l'utilisateur garde la main |

> **À dire** : « La prédiction fusionne deux estimations : ce que la machine fait d'habitude, et le
> rythme observé sur cette tâche, mesuré en tokens pendant que le modèle écrit. Plus on utilise
> Sensia, plus elle est juste : 36 % d'erreur sur une tâche nouvelle, 24 % sur une tâche déjà
> faite deux fois. »

Si l'avertissement du dernier cas n'apparaît pas, refaire avec `/fast 12 ...`. Si la question
arrive dès le départ, répondre `y` pour atteindre celle du milieu.

---

## Acte 7 — Quand c'est le modèle qui propose (A3)

*Besoin : demander en langage naturel, sans connaître les commandes.*

| Je tape | On doit voir | Ce que ça montre |
|---|---|---|
| `Écris-moi une fonction Python qui inverse une chaîne, en moins de 40 secondes` | `[Sensia wants to run: /fast 40 ...]` puis `Run it? [y/N]` → `y` | Le modèle déclenche l'outil, mais rien ne s'exécute sans confirmation |

Cet acte demande le persona `dev`, actif depuis l'acte 3 : seul ce persona décrit cet outil au
modèle. S'il est joué seul, taper d'abord `/persona dev`.

**Ne pas jouer cet acte** : il n'a marché dans aucune des 6 prises. Avec les outils MCP actifs, le
JSON `{"tool": "fast", ...}` ne revient jamais à Sensia : la réponse est vide ou sans appel d'outil.
Pour montrer la confirmation, utiliser `Continue anyway? [y/N]` de l'acte 6.

---

## Acte 8 (optionnel) — L'interface web (X1)

| Je tape | On doit voir | Ce que ça montre |
|---|---|---|
| `quit`, puis `python3 main.py --web` | le serveur sur `http://127.0.0.1:4040` | Interface découplée, même backend |
| ouvrir l'adresse, puis se connecter avec le compte de démo | la page de connexion, puis la page de discussion | Le même compte et le même profil que dans le terminal |
| une question, puis `/code Write a Python function that returns the first 15 Fibonacci numbers and print them` | la réponse en streaming, puis le code et sa sortie dans la page | Les mêmes commandes que le terminal |
| `Quelles sont les nouveautés de Python cette semaine ?` | `[Tool web_search: {...}]` pendant le streaming, puis la synthèse datée | Le même serveur MCP que dans le terminal |

`/persona` et `/remember` fonctionnent aussi dans le web. `/fast` n'est pas disponible : il y part
vers le modèle comme un message ordinaire, donc ne pas le taper ici.

---

## Acte 9 — Les preuves

À ouvrir à la fin, ou pour répondre aux questions du jury :

- [`benchmarks/README.md`](../benchmarks/README.md) : 1.5B, 3B, 7B et Llama 3B mesurés sur cette machine ; pourquoi le 3B ; la quantification ; la précision de `/fast` et le banc de budget (20 sur 24, les 4 dépassements annoncés).
- [`docs/user_stories/README.md`](user_stories/README.md) : chaque fonctionnalité, son besoin, ses stories, son code et sa vérification.
- [`config.toml`](../config.toml) : tous les réglages et les températures par usage.

---

## Si quelque chose rate

| Problème | Que faire |
|---|---|
| Le premier appel est très lent | Le modèle se charge (environ 10 s) : c'est pour ça qu'on le fait chauffer avant |
| `Wrong password.` ou `No account for this email` | Faute de frappe : répondre `n` si besoin, relancer `python3 main.py` et ressaisir l'e-mail du compte de démo |
| `Nothing relevant found` sur une question attendue | Relancer `/index`, puis reposer la question |
| `MCP server unavailable` ou erreur `web_search` | Vérifier `.env` et `pip install -r requirements.txt` ; sinon, passer l'acte 4 |
| `fib(42)` réussit dès la 1re tentative | C'est possible : le dire, et montrer les mesures de la boucle dans `benchmarks/README.md` |
| Une réponse part en anglais | Sans gravité : le modèle de 3B suit la langue la plupart du temps, pas toujours |
| Une étape bloque | `Ctrl+C` arrête la réponse en cours, pas Sensia |
| `/rag` sur le modèle d'embedding répond qu'il ne trouve pas (2 prises sur 10) | La bonne source reste affichée : reposer la question |
| Le test `/home` affiche `True` (1 prise sur 10) | Le code généré a créé la variable lui-même : le montrer dans le code, puis relancer la commande |
| `/fast 15` finit par `Max try reached` et un `RESULT` vide (5 prises sur 10) | Le code généré retire plus que le solde et plante à chaque tentative : le dire, puis passer à l'acte suivant |

**Après la démo** : `/remember` a écrit dans `data/profiles/<email>.md`. Ce dossier est ignoré par
git : rien ne part dans un commit, mais on peut retirer la ligne pour la démo suivante.

---

## État des vérifications (2026-11-01)

Rejoué 10 fois en entier sur la vraie application, dans un vrai terminal, sous Windows (`python`
au lieu de `python3`), avec Docker. **Ce n'est pas la machine de démo** : environ 47 tokens/s,
contre environ 18 sur la machine de référence. Les temps de `/fast` y seront donc différents.

Une partie de ces prises tournait avec un essai de correctif de l'acte 7, retiré depuis, qui ajoutait
un outil au persona `dev`. Les messages libres de ce persona (actes 3, 4 et 5) sont donc à revérifier.

| Acte | Résultat |
|---|---|
| 1 (profil) | Oui. Avec l'ancienne question `Bonjour, qui es-tu ?`, le prénom manquait dans 4 prises sur 6 ; avec la nouvelle, 0 sur 4 |
| 2 (RAG) | Oui : scores 0,75 et 0,67, question hors sujet refusée 10 fois sur 10. `274 MB` manque dans 2 prises sur 10 |
| 3 (persona) | Oui, 10 fois sur 10 |
| 4 (outil décidé par le modèle) | **Partiel** : `web_search` appelé 10 fois sur 10, mais sans clé LangSearch. La synthèse datée et ses sources restent à vérifier avec une clé |
| 5 (`/code`) | Oui, dans le sandbox Docker : Fibonacci en 1 tentative, `fib(42)` en 2 tentatives. `/home` et clé : `[]`, `False` dans 9 prises sur 10. L'ancienne question `Explique ce que tu viens de faire` faisait inventer au modèle une fausse correction |
| 6 (`/fast`) | Oui avec un historique rempli, sauf `/fast 8`, tenu dans 2 prises sur 10 seulement : ici, la préparation prend déjà 5 s |
| 7 (confirmation) | **Non** : 0 prise sur 6, réponse vide ou sans appel d'outil |
| 8 (web) | Une prise : connexion, question, `/code`, `/persona`, `/remember` fonctionnent. Recherche sans clé : voir l'acte 4 |

**Reste à faire** : rejouer sur la machine de démo avec la clé LangSearch, et remplacer la diapo
d'attendu de la keynote par les vraies captures.
