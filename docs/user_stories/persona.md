# User story — Persona de l'assistant (A5)

## Persona

Deux utilisateurs différents :

- **Un membre de l'équipe** qui veut créer un nouvel assistant (un tuteur, un assistant de
  revue de code…) sans toucher au Python.
- **Un utilisateur** qui discute avec Sensia et qui, en cours de route, a besoin d'un autre
  type d'aide (plus technique, plus pédagogique) sans devoir réexpliquer son contexte.

## User story 1 — Configurer l'assistant sans modifier le code

> En tant que membre de l'équipe, je veux définir le nom, le ton, le rôle et les valeurs de
> l'assistant dans un simple fichier Markdown, afin de créer un nouvel assistant sans
> modifier le code.

### Critères d'acceptation

| # | Critère |
|---|---|
| 1 | Un persona est un fichier `persona/personas/<nom>.md`. En ajouter un suffit à le rendre disponible : aucune ligne de Python à modifier. |
| 2 | Le contenu du fichier est envoyé au modèle comme premier message (`role: system`) de la conversation. |
| 3 | Le nom affiché dans le terminal (`SENSIA: ...`) est lu sur la première ligne qui commence par `# `. Sans titre, le nom affiché est `Assistant`. |
| 4 | Le persona se choisit à la création du compte et revient à chaque connexion. `--persona` n'est plus qu'une vérification du nom : après la connexion, le persona du compte le remplace. |
| 5 | Un nom de persona inconnu affiche `Unknown persona '<nom>'. Available: dev, sensia`, sans planter. |
| 6 | La date du jour est ajoutée au prompt système, quel que soit le persona. |

## User story 2 — Changer de persona en pleine conversation

> En tant qu'utilisateur, je veux passer d'un persona à un autre au milieu d'une
> conversation, afin d'obtenir un autre type d'aide sans perdre ni réexpliquer ce que j'ai
> déjà dit.

### Critères d'acceptation

| # | Critère |
|---|---|
| 1 | `/persona dev` change de persona et affiche `Switched to SENSIA — developer mode (conversation kept)`. |
| 2 | Seul le prompt système (`messages[0]`) est remplacé : tout l'historique de la conversation est conservé. |
| 3 | Après le changement, l'assistant se souvient de ce qui a été dit avant (une information donnée sous `sensia` est retrouvée sous `dev`). |
| 4 | Le nom affiché change immédiatement (`SENSIA — developer mode: ...`). |
| 5 | Le nouveau persona s'applique partout : nom affiché, `/remember` et `/fast` (avec `dev`, `/fast` planifie toujours la tâche). |
| 6 | Le profil utilisateur (`data/profiles/<email>.md`) est conservé lors du changement. |
| 7 | `/persona` seul affiche le persona actuel et la liste : `Current persona: sensia. Available: dev, sensia`. |
| 8 | Un nom inconnu (`/persona toto`) ou un chemin (`/persona ../user`) est refusé : la liste s'affiche, rien ne change. Seuls les fichiers de `persona/personas/` peuvent être chargés. |

## Scénario de démo

```
python3 main.py
Email: ...
Password:

You: My name is Romain and I love Rust.
SENSIA: ...

You: /persona
Current persona: sensia. Available: dev, sensia

You: /persona dev
Switched to SENSIA — developer mode (conversation kept)

You: What language do I love?
SENSIA — developer mode: Captain, you love Rust.
     → nouveau nom, historique conservé, profil toujours appliqué

You: /persona ../user
Current persona: dev. Available: dev, sensia
     → refusé : seuls les personas de persona/personas/ sont chargeables
```

## Hors périmètre (plus tard)

- `/persona` ne change le persona que pour la session : il n'est pas enregistré dans le compte.
- Les consignes d'outils (recherche web, commandes) sont écrites dans chaque fichier de
  persona : un nouveau persona doit les recopier pour en profiter.
- Après un changement, les anciennes réponses restent dans l'historique avec le ton de
  l'ancien persona : un petit modèle peut continuer à les imiter pendant quelques messages.
