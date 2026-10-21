# Plan : POST /next-version

Réf. specs : [next-version-spec.md](next-version-spec.md). Règles : CLAUDE.md (TDD, KISS, lint, typage, mutation, API HTTP).

## Fichiers

- `versions.py` : logique pure (parse, précédence, bump). Aucune dépendance Flask.
- `specs.py` : handler fin + error handlers JSON globaux.
- `tests/test_versions.py` : tests unitaires de la logique.
- `tests/test_next_version.py` : tests de la route via le client de test Flask.
- `tests/test_server_live.py` : tests contre un gunicorn réellement lancé.
- `pyproject.toml` : dev deps (`mypy`, `mutmut`, `hypothesis`), config mypy et mutmut (module `versions.py`).
- `README.md` : documentation de la route.

## Étapes (chaque étape : Red → Green → Refactor)

1. **Outillage** : `uv add --dev mypy mutmut hypothesis` ; config mutmut sur `versions.py` ; `uv run pytest` vert à vide.
2. **Parse / validation** (`parse_tag(tag) -> Version | None`)
   - Rouge : valides (`1.2.3`, `v1.2.3`, `0.0.0`, `1.2.3-rc.1`, `1.2.3-rc.01`, `1.2.3+a-b.c`, `1.2.3-rc.1+x`) ; invalides (`V1.2.3`, `01.2.3`, `1.2`, `1.2.3.4`, `1.2.3-`, `1.2.3+`, `1.2.3-a..b`, espaces, `\n` final, chiffres Unicode, 16 chiffres).
   - Vert : regex ASCII avec `re.fullmatch` (pas de `$`), `\A`/`\Z` inutiles avec `fullmatch`, classes `[0-9]` explicites.
3. **Précédence** (clé de tri sur `Version`)
   - Rouge : `1.10.0 > 1.9.0`, `1.3.0-rc.1 < 1.3.0`, `1.3.0-rc.1 > 1.2.9`, `rc.2 < rc.10`, numérique < alphanumérique, `rc < rc.1`, build ignorée, égalité `v1.2.3 == 1.2.3`.
   - Vert : clé `(x, y, z, release_flag, prerelease_key)` ; ids numériques par (longueur, chaîne).
4. **Bump** (`next_version(tags, bump) -> str`)
   - Rouge : tableau de la spec (patch/minor/major, pré-release, préfixe `v` sur égalité, sortie sans build ni pré-release).
   - Vert : base = max ; `patch` sur pré-release → `X.Y.Z` ; sinon bump normal ; préfixe `v` si au moins un tag de précédence égale au max l'a.
5. **Propriété** (`hypothesis`) : le résultat est strictement supérieur à tous les tags finaux valides, et est invariant à l'ordre des tags.
6. **Route** `POST /next-version`
   - Rouge (client Flask) : 200 nominal ; 400 pour chaque message de la spec avec l'ordre de validation ; 415 ; 413 ; JSON malformé, non UTF-8, imbriqué très profond, types inattendus → 400 (jamais 5xx) ; `GET` → 405 + `Allow` ; 404 JSON.
   - Vert : `request.get_json` en mode strict avec capture des erreurs (`RecursionError` incluse), handlers globaux 404/405/413/415/400 → `{"error": ...}`, `MAX_CONTENT_LENGTH = 1 Mo`. Le handler valide puis délègue à `versions.py`.
7. **Serveur réel** : tests qui lancent gunicorn sur un port libre et appellent la route (nominal, invalide, 404, 405, 415).
8. **Qualité** : `ruff format`, `ruff check --fix`, `mypy .`, `mutmut run` (zéro mutant survivant sur `versions.py` : ajouter un test ou supprimer le code mort).
9. **Vérification manuelle** : `curl -i` sur le serveur lancé (200, 400 chacun, 404, 405, 413, 415) ; contrôle du status, de `Content-Type` et du body JSON.
10. **README** : route, exemples `curl`, commandes dev (tests, lint, typage, mutation).

## Répartition en agents

- **Agent implémentation** (nouveau) : étapes 1 à 6 et 10, en TDD.
- **Agent tests** (dédié) : étapes 7 à 9 et la revue des mutants survivants.

## Definition of Done

Celle de CLAUDE.md : pytest vert, ruff et mypy sans erreur, zéro mutant survivant, `curl` vérifié, pas de dépendance inutile, README à jour.
