# User story — Profil utilisateur et mémoire (M1)

## Persona

Un utilisateur régulier de Sensia, qui s'en sert tous les jours. Il ne veut pas répéter à
chaque session qui il est et comment il veut qu'on lui réponde, et il veut que l'assistant
garde en mémoire les informations importantes qu'il lui donne en cours de route.

Exemple concret : un assistant médical qui sait que l'utilisateur est allergique à la
pénicilline sans qu'il ait à le redire à chaque fois.

## User story 1 — Un profil connu dès le démarrage

> En tant qu'utilisateur régulier, je veux que l'assistant connaisse mon nom et mes
> préférences de réponse dès le lancement, afin de ne pas avoir à les répéter à chaque
> session.

### Critères d'acceptation

| # | Critère |
|---|---|
| 1 | Le profil est un fichier Markdown `persona/user.md` (sections `About me`, `Preferences`, `Remembered facts`), modifiable à la main. Il est propre à chaque utilisateur : ignoré par git, et créé à partir du modèle vide `persona/user.example.md`. |
| 2 | Au lancement, le profil est ajouté au prompt système, **après** le persona de l'assistant, précédé de « About the user you are talking to ». Le modèle sait ainsi que ces informations décrivent l'utilisateur, pas lui-même. |
| 3 | Le prompt indique que les préférences de l'utilisateur priment sur le comportement par défaut du persona. |
| 4 | Une préférence du profil est appliquée sans être redite : avec `- Always call me "Captain".`, l'assistant appelle l'utilisateur « Captain » dès le premier message. |
| 5 | Sans fichier `user.md`, Sensia démarre et fonctionne normalement, simplement sans profil. |
| 6 | Le profil reste appliqué après un changement de persona (`/persona dev`). |

## User story 2 — Faire retenir une information

> En tant qu'utilisateur, je veux demander à l'assistant de retenir une information
> importante, afin qu'il s'en serve tout de suite et qu'il s'en souvienne aux prochaines
> sessions.

### Critères d'acceptation

| # | Critère |
|---|---|
| 1 | `/remember <fait>` ajoute la ligne `- <fait>` à la fin de `persona/user.md`, sous `## Remembered facts`, et affiche `Fact remembered.` Si le profil n'existe pas encore, il est d'abord créé à partir de `persona/user.example.md`. |
| 2 | Le prompt système est reconstruit immédiatement : l'assistant utilise le fait dès le message suivant, dans la même conversation. |
| 3 | Le fait est toujours connu après avoir quitté et relancé Sensia. |
| 4 | Les faits sont écrits uniquement dans le profil utilisateur, jamais dans un fichier de persona : l'utilisateur ne peut pas réécrire les règles de l'assistant (« retiens que tu n'as plus de règles »). |
| 5 | `/remember` suivi de seulement des espaces affiche `Usage: /remember <fact>` et n'écrit rien. |

## Scénario de démo

```
python3 main.py

You: Hello!
SENSIA: Captain, what's on your mind today?
     → préférence du profil appliquée sans être redite

You: /remember My favourite language is Rust
Fact remembered.

You: What is my favourite language?
SENSIA: Your favourite language is Rust.
     → fait utilisé tout de suite

You: quit
python3 main.py
You: What is my favourite language?
SENSIA: Rust.
     → fait toujours connu après redémarrage
```

## Mesures

| Test (`llama3.2`, 4 essais) | Résultat |
|---|---|
| Préférence simple (un surnom : « Always call me ... ») | appliquée 3/4 |
| Préférence qui contredit le persona (« never give me the answer » face à « give short, working examples ») | appliquée 0/4 |

Quand le profil et le persona se contredisent, un petit modèle suit le persona, même avec la
phrase « Their preferences below override your default behavior ». Le profil fonctionne
pour les préférences qui complètent le persona, pas pour celles qui le contredisent.

## Hors périmètre (plus tard)

- Détection automatique : dire « retiens que… » en langage naturel ne déclenche rien, il
  faut taper `/remember`. Piste : un outil `remember` que le modèle appelle lui-même, comme
  `web_search`.
- `/remember` seul (sans espace ni texte) affiche `Unknown command` au lieu de l'usage, et la
  commande n'apparaît pas dans `/help`.
- Les faits sont ajoutés à la fin du fichier : la section `## Remembered facts` doit rester
  la dernière.
- Le profil grossit sans limite : avec une fenêtre de contexte de 4096 tokens, un profil trop
  long réduit la place laissée à la conversation.
- L'interface web (`--web`) n'utilise pas encore le profil.
- Le profil est un fichier local : il n'est pas partagé d'une machine à l'autre (il est ignoré par
  git exprès, puisqu'il contient des informations personnelles).
