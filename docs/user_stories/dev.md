# User story — Tâches avec un budget de temps (`/fast`, T5)

## Persona

Un développeur qui utilise Sensia en local, sur sa propre machine (CPU, petit modèle), et
qui fait souvent le même genre de tâches. Il veut du code qui marche, rapidement, et savoir
**avant et pendant** l'exécution si sa demande tiendra dans le temps dont il dispose.

## User story 1 — Savoir avant de lancer si ça tient

> En tant que développeur, je veux donner une tâche avec un budget de temps et voir tout de
> suite combien de temps elle va prendre, afin de ne lancer que ce qui tient dans mon délai.

### Critères d'acceptation

| # | Critère |
|---|---|
| 1 | `/fast <secondes> <tâche>` lance la tâche ; sans budget ou avec un budget nul : `Usage: /fast <seconds> <task>`. |
| 2 | Le modèle choisit seulement le type de livrable (`text`, `code` ou `explanation`), en JSON contraint par un schéma ; le plan est construit en Python : `write`, `code` (+ `explain` si la demande dit « explain » ou « explique »), ou `explain`, précédé de `research` si la demande dit « research » ou « cherche ». |
| 3 | Le plan ne contient jamais d'action impossible (« envoyer », « publier ») ni d'étape qui reformule la demande. |
| 4 | Avec le persona dev, la tâche est toujours planifiée ; avec `sensia`, une demande de 12 mots ou moins est traitée en une seule étape directe. |
| 5 | La prédiction de départ est affichée en distinguant le temps du plan, déjà écoulé, et le travail prévu : `Initial prediction: 20s ± 4s = 1s of setup (...) + 19s of work`. |
| 6 | Si même le minimum prévu dépasse le budget, Sensia demande `Continue anyway? [y/N]` avant de lancer quoi que ce soit ; `n` affiche `Cancelled.` |
| 7 | Les étapes `code` passent par `code_cycle` : le code est exécuté dans le sandbox et corrigé jusqu'à 3 fois. |
| 8 | À la fin, Sensia affiche la durée réelle et `Budget: <n>s -> kept` ou `exceeded`, puis le livrable complet, sans le remplacer par un commentaire de vérification. |
| 9 | Si l'utilisateur demande en langage naturel une tâche dans un temps donné, le modèle peut lancer `/fast` lui-même avec l'outil natif `fast`, proposé au persona `dev` seulement ; la commande comprise est affichée et n'est exécutée qu'après `y`. Au plus une exécution par message. |

## User story 2 — Tenir le budget pendant l'exécution

> En tant que développeur, je veux que Sensia surveille le temps pendant qu'elle travaille
> et s'adapte, afin de ne jamais dépasser mon budget sans le savoir.

### Critères d'acceptation

| # | Critère |
|---|---|
| 1 | Pendant la génération, une ligne `⏳ <tokens> tokens | p=<avancement> | -> <total prévu>` est mise à jour environ deux fois par seconde. |
| 2 | L'avancement `p` combine les étapes faites (poids corrigés) et la part de la réponse déjà écrite (tokens écrits / tokens attendus). |
| 3 | Si la réponse habituelle ne tient pas dans le temps restant, Sensia la demande plus courte et l'annonce : `✂ answer shortened to ~N words to fit the budget (~6s instead of ~12s)`. |
| 4 | Dès 60 % d'avancement, ou dès que le temps est écoulé, la prédiction est comparée au budget ; en cas de dépassement, Sensia demande une seule fois `Continue anyway? [y/N]`. |
| 5 | Sur `n`, Sensia s'arrête, même en pleine génération, garde ce qui est fait (`[… stopped here to respect the time budget]`), et la note envoyée au chat indique que le résultat est incomplet. |
| 6 | Une étape `code`, `write` ou `explain` n'est jamais retirée pour tenir le budget : seule l'étape `research` peut l'être. |
| 7 | Ollama injoignable ou `Ctrl+C` pendant `/fast` : un message, pas de plantage. |

## User story 3 — Des prédictions qui s'améliorent avec l'usage

> En tant que développeur qui refait souvent les mêmes tâches, je veux que Sensia apprenne
> de mes exécutions, afin que ses prédictions deviennent plus justes sur ma machine.

### Critères d'acceptation

| # | Critère |
|---|---|
| 1 | Chaque exécution est enregistrée localement (`knowledge/history/`, ignoré par git) : durées, tokens, vitesse de génération, et embedding de la demande. |
| 2 | Sensia affiche ce qu'il a appris : `Learned speed: 19.2 tokens/s, latency 1.0s | expected answer length: ...`. |
| 3 | Les tâches semblables déjà lancées sont retrouvées par similarité d'embeddings et listées (`Similar past tasks`). |
| 4 | Une réponse raccourcie pour tenir un budget n'entre pas dans l'apprentissage, pour ne pas fausser la longueur normale. |
| 5 | Mesuré : l'erreur de la prédiction de départ passe de 37 % pour une tâche nouvelle à 24 % pour une tâche déjà lancée au moins deux fois (70 exécutions rejouées). |

## User story 4 — Un plan dans un format fiable

> En tant que développeur, je veux que le modèle réponde dans un format imposé quand il prépare
> une tâche, afin que Sensia puisse toujours lire sa réponse et construire le plan.

### Critères d'acceptation

| # | Critère |
|---|---|
| 1 | La classification envoie à Ollama un schéma JSON dans le champ `format` : un objet avec un champ obligatoire `deliverable`. |
| 2 | `deliverable` ne peut valoir que `text`, `code` ou `explanation`. |
| 3 | La classification utilise une température de 0 (section `[generation.plan]`). |
| 4 | Réponse qui n'est pas du JSON, sans `deliverable` ou avec une valeur hors liste : la tâche est classée `text`, sans plantage. |
| 5 | Si le modèle répond `text` alors que la demande contient un mot comme `function` ou `script`, une règle en Python la reclasse en `code`. |
| 6 | Mesuré : 36 réponses sur 36 au format valide, et 34 classements corrects sur 36 ; les 2 erreurs sont corrigées par la règle du critère 5. |

### Scénario de démo

```
python3 -c "from core.config import CONFIG; from timepred.plan import make_plan; print([s['type'] for s in make_plan('Write a Python function that checks prime numbers, then explain how it works', CONFIG['ollama']['model'], CONFIG['ollama']['chat_url'], allow_direct=False)])"
['code', 'explain']
```

## Scénario de démo

```
python3 main.py --persona dev

You: /fast 30 Écris un mail de relance pour lundi
     → plan : [write] · Initial prediction: 7s · ⏳ ... · Budget: 30s -> kept

You: /fast 8 Explain how HTTP caching works and compare it with a CDN for a beginner audience
     → ✂ answer shortened to ~65 words (~6s instead of ~12s) · Budget: 8s -> kept

You: /fast 15 Write a Python class for a bank account, run 3 operations, then explain how it works
     → plan : [code → explain] · code vérifié · "Budget: 15s -> updated prediction: 18s"
     → n : arrêt, le code vérifié est gardé
```

## Mesures

Banc de 24 exécutions réelles (8 tâches × budget confortable, serré, très serré) : budget
tenu 20 fois sur 24, et les 4 dépassements avaient tous été annoncés avant d'arriver.

## Hors périmètre

- Les étapes `code` ne sont pas suivies en direct : le budget est revérifié à leur fin.
- `/fast` n'est pas disponible dans l'interface web.
- Sans limite de temps, le modèle peut quand même appeler l'outil `fast` (4 fois sur 10 sur
  « Écris une fonction Python qui inverse une chaîne. ») : la question `Run it? [y/N]` protège,
  et répondre `n` suffit.
- L'étape `research` ne cherche pas encore sur le web : le modèle répond de mémoire.
