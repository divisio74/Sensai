# User story — Développeur

## Persona

Un développeur qui utilise Sensia en local, sur sa propre machine (CPU, petit modèle).
Il veut du code qui marche, rapidement, et savoir **avant de lancer** si sa demande tient
dans le temps dont il dispose.

## User story

> En tant que développeur, je veux demander une tâche de code avec un budget de temps,
> afin d'obtenir du code **exécuté et vérifié** dans ce délai — ou d'être prévenu avant
> le lancement si c'est impossible.

## Critères d'acceptation

| # | Critère |
|---|---|
| 1 | Sensia se lance avec le persona dev : `python3 main.py --persona dev`. Un nom de persona inconnu affiche la liste des personas disponibles, sans planter. |
| 2 | Le persona dev connaît les commandes `/code` et `/fast` et les propose quand c'est pertinent. |
| 3 | Avec le persona dev, `/fast` planifie toujours la tâche (pas de raccourci « tâche courte »), pour que le code passe par la vérification. |
| 4 | Les étapes de type `code` sont exécutées par `code_cycle` : le code tourne dans le sandbox et il est corrigé jusqu'à 3 fois. |
| 5 | Une étape `code` n'est réussie que si `code_cycle` renvoie `success`. |
| 6 | La durée d'une étape `code` inclut toutes ses tentatives, et elle est enregistrée dans l'historique sous le type `code`. |
| 7 | Seules les étapes de préparation et de vérification (`analyse`, `research`, `check`) peuvent être élaguées. Les étapes qui produisent (`write`, `transform`, `code`, `explain`) ne le sont jamais. |
| 8 | Si même les étapes essentielles dépassent le budget, Sensia demande avant de lancer. |
| 9 | Après l'exécution, Sensia sait dire ce qu'elle a fait, combien de temps ça a pris, et si le code a été vérifié. |
| 10 | Ollama injoignable, plan illisible ou Ctrl+C pendant `/fast` : un message, pas de plantage. |
| 11 | Si l'utilisateur demande explicitement, en langage naturel, d'exécuter une tâche dans un temps donné, Sensia déclenche `/fast` elle-même via le format réservé `{"tool": "fast", "seconds": ..., "task": ...}`, après avoir affiché la commande comprise et obtenu la confirmation de l'utilisateur. Un refus n'exécute rien. Au plus une exécution par message. |

## Scénario de démo

```
python3 main.py --persona dev

You: /fast 120 Write a Python function that parses a CSV string, keeps the rows where age >= 18, and prints how many rows were kept
     → le plan contient une étape [code]
     → code_cycle : "===== Attempt 1/3 =====", exécution dans le sandbox
     → prédiction mise à jour à chaque étape

You: Was the code actually run, and how long did it take?
Sensia: (répond avec la durée réelle et le fait que le code a été exécuté et vérifié)
```

## Hors périmètre (plus tard)

- Les autres personas (secrétaire, etc.).
- Changer de budget pendant l'exécution (pause entre deux étapes).
- Isoler chaque sous-agent dans son propre processus : `code_cycle` tourne dans le processus
  principal, seul le code qu'il génère est isolé dans le sandbox.
- Les étapes `check` (tests) passent encore par le worker de démo : les tests sont écrits,
  pas exécutés.
- Les échecs de `code_cycle` (3 tentatives ratées) ne sont pas enregistrés dans l'historique,
  qui sous-estime donc le coût des tâches difficiles.
