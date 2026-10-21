# CLAUDE.md

Projet Python, dépendances via `uv`. Commandes de lancement : voir README.

## Outils

```bash
uv sync                                     # install
uv run pytest                               # tests
uv run ruff format . && uv run ruff check --fix
uv run mypy .                               # typage
uv run mutmut run && uv run mutmut results  # mutation testing
```

Outil de dev manquant (pytest, ruff, mypy, mutmut, hypothesis…) → l'ajouter avec `uv add --dev`.

## Standards

### TDD
- Red → Green → Refactor. Écrire le test qui échoue **avant** le code.
- Lancer le test et le voir échouer pour la bonne raison avant d'implémenter.
- Tester le comportement observable (entrée → sortie), pas l'implémentation.
- Bug = d'abord un test qui le reproduit, puis le fix.

### KISS
- La solution la plus simple qui marche. Pas d'abstraction spéculative (YAGNI).
- Pas d'interface avec une seule implémentation, pas de factory pour un seul produit, pas de config pour une valeur fixe.
- Moins de code > plus de code. Supprimer avant d'ajouter.

### Ne jamais réinventer la roue
- Ordre de préférence : stdlib → feature du framework / lib déjà installée → dépendance reconnue et maintenue → code maison.
- Format ou standard connu (dates, URLs, versions, emails…) → bibliothèque dédiée, pas de regex ou parsing maison.
- Avant d'écrire un utilitaire, vérifier qu'il n'existe pas déjà dans le repo ou une dépendance.

### SOLID
- Une fonction / un module = une responsabilité. Logique métier pure dans son propre module, séparée de la couche HTTP.
- Les handlers HTTP valident l'entrée et délèguent ; pas de logique métier dedans.
- Dépendre d'abstractions seulement quand il existe ≥ 2 implémentations réelles (sinon KISS l'emporte).

### Lint & typage
- `ruff format` + `ruff check` sans erreur.
- `mypy` sans erreur. Annoter toutes les signatures publiques. Pas de `# type: ignore` / `Any` sans justification en commentaire.

### Mutation testing
- Configurer mutmut sur les modules de logique métier (`pyproject.toml`).
- Après modif de cette logique : `uv run mutmut run`. Tout mutant survivant = test manquant ou code mort → ajouter un test ou supprimer le code.

### API HTTP
- Chaque route a des tests : client de test du framework **et** serveur réellement lancé.
- Couvrir : cas nominal, entrée invalide (4xx + message), cas limites.
- Toutes les erreurs HTTP sont en JSON `{"error": "<message>"}`, y compris 404 et 405 (garder le header `Allow`) : error handlers globaux.
- Route JSON : `Content-Type` non JSON → 415 ; body trop gros (> 1 Mo par défaut) → 413.
- Jamais de 5xx sur une entrée client (JSON malformé, très imbriqué, non UTF-8, types inattendus) → 400.
- Vérifier aussi à la main contre le serveur lancé (`curl -i …`) : status code, `Content-Type`, body JSON.

## Definition of Done

Une tâche est finie seulement si **tout** est vrai :

- [ ] Tests écrits avant le code (TDD), et `uv run pytest` est vert.
- [ ] `uv run ruff format .` et `uv run ruff check` : aucune erreur.
- [ ] `uv run mypy .` : aucune erreur.
- [ ] `uv run mutmut run` : aucun mutant survivant sur le code modifié.
- [ ] Route API modifiée/ajoutée → testée via `curl` sur le serveur lancé, sortie vérifiée.
- [ ] Pas de nouvelle dépendance si stdlib ou une dep existante suffit.
- [ ] Code le plus simple possible, pas de code mort ni d'abstraction inutile.
- [ ] README à jour si commandes, routes ou setup changent.
