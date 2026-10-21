# Plan — `POST /next-version`

Spec de référence : [`docs/specs/next-version.md`](../specs/next-version.md). Toute règle, tout message d'erreur et tout cas limite vient de là.

Chaque étape suit le cycle TDD du `CLAUDE.md` : écrire le test, le lancer et le voir échouer pour la bonne raison, puis implémenter au plus simple, puis refactorer.

## Fichiers

| Fichier | Rôle |
| --- | --- |
| `versioning.py` (nouveau) | Logique métier pure : `next_version(tags: list[str], bump: str) -> str`. Aucun import Flask. |
| `specs.py` | Route `POST /next-version` : lit et valide le body, délègue à `versioning`, mappe les erreurs. Error handlers globaux. |
| `tests/test_versioning.py` (nouveau) | Tests unitaires de la logique. |
| `tests/test_next_version_api.py` (nouveau) | Tests de la route via `app.test_client()`. |
| `tests/test_next_version_server.py` (nouveau) | Tests de la route contre un serveur réellement lancé (sous-processus sur un port libre). |
| `pyproject.toml` | Dépendances et configuration de mypy et mutmut. |
| `README.md` | Documentation de la route et des commandes de dev. |

## Étape 0 — Outillage

1. `uv add semver` (dépendance runtime, décision Q4).
2. `uv add --dev mypy mutmut`.
3. Dans `pyproject.toml`, configurer mutmut sur `versioning.py` seulement.
4. Vérifier que `uv run pytest`, `uv run mypy .` et `uv run ruff check` passent sur le code existant. Annoter `create_app() -> Flask` si mypy le demande.

## Étape 1 — Logique métier (`versioning.py`)

Interface :

```python
class InvalidTagsError(ValueError):
    """Message: 'invalid tags: a, b' (ordre d'entrée, doublons conservés)."""


def next_version(tags: list[str], bump: Literal["major", "minor", "patch"]) -> str: ...
```

- Une liste vide lève `ValueError("tags must not be empty")`.
- Un ou plusieurs tags invalides lèvent `InvalidTagsError`. Le message liste tous les tags invalides dans l'ordre d'entrée.

Implémentation visée, en moins de 30 lignes :

- Retirer le préfixe `v` s'il est présent, puis appeler `semver.Version.parse`. Un `ValueError` du parse signifie que le tag est invalide.
- Choisir la base avec `max(..., key=lambda t: (version, has_v))`. Si deux tags ont la même précédence SemVer (build ignorée), celui qui a le préfixe `v` l'emporte.
- Calculer `next` avec `version.next_version(bump)`, ce qui donne la sémantique npm et retire la build. Remettre ensuite le préfixe de la base.

Les tests, dans l'ordre TDD :
1. Bump nominal : patch, minor et major sur `1.2.3`.
2. Comparaison numérique : `1.9.0` contre `1.10.0`.
3. Pré-releases : chaque ligne concernée du tableau « Use cases » de la spec.
4. Préfixe : celui du plus haut tag, `v` en cas d'égalité, y compris avec une build metadata.
5. Build metadata supprimée du résultat.
6. Tags invalides, paramétrés : `V1.2.3`, `1.2`, `01.2.3`, ` 1.2.3`, `1.2.3\n`, `1.2.3-`, `1.2.3+`, `1.2.3-01`, `1.2.3+a..b`, `vv1.2.3`, `""`, `١.2.3`.
7. Message de `InvalidTagsError` : ordre d'entrée et doublons conservés.
8. Une liste vide lève `ValueError` avec le bon message.

Lancer ensuite `uv run mutmut run`. Il ne doit rester aucun mutant survivant.

## Étape 2 — Socle HTTP (`specs.py`)

D'abord les tests (client de test), puis l'implémentation :

- `MAX_CONTENT_LENGTH = 1 Mo`.
- Un error handler global pour `HTTPException` qui renvoie `{"error": <message>}` avec le code d'origine et conserve ses headers (`Allow` sur un 405).
  - 404 → `not found`
  - 405 → `method not allowed`
  - 413 → `request body too large`
  - 415 → `content type must be application/json`
- Vérifier aussi que `/hello` reste inchangé et qu'un 404 ou 405 sur `/hello` renvoie bien du JSON.

## Étape 3 — Route `POST /next-version`

Le handler valide dans l'ordre de la spec et renvoie la première erreur rencontrée :
1. `request.is_json`, sinon 415.
2. Lire le body avec `request.get_data()`, puis `json.loads`. Intercepter `ValueError` (JSON malformé, non UTF-8) et `RecursionError` (JSON trop imbriqué) pour renvoyer 400 `body must be valid JSON`. Ne pas utiliser `request.get_json()`, qui laisse passer `RecursionError` en 500.
3. La racine doit être un `dict`, sinon `body must be a JSON object`.
4. Champs inconnus : `unknown fields: …` dans l'ordre du body.
5. `tags` doit être présent, puis être une liste de `str`.
6. `bump` doit être présent, puis être dans `("major", "minor", "patch")`. La comparaison est sensible à la casse et refuse les valeurs non-string.
7. Déléguer à `next_version`. Un `ValueError` donne 400 avec `str(e)`.

Les tests (client de test) couvrent :

- chaque ligne du tableau d'erreurs de la spec ;
- un cas nominal par type de bump ;
- les priorités, par exemple `[]` avec `"PATCH"` qui renvoie l'erreur de bump ;
- un JSON imbriqué sur 100 000 niveaux, qui doit renvoyer 400 et non 500 ;
- des octets non UTF-8, qui doivent renvoyer 400 ;
- un body de plus de 1 Mo, qui doit renvoyer 413 ;
- un `Content-Type: application/json; charset=utf-8`, qui doit être accepté.

Chaque test vérifie le status, le `Content-Type: application/json` et le body exact.

## Étape 4 — Serveur réellement lancé

Une fixture pytest de scope module :

- lance `gunicorn "specs:create_app()"` sur un port libre ;
- attend que `/hello` réponde ;
- arrête le serveur à la fin.

Les tests utilisent `urllib.request` (stdlib, aucune dépendance) et couvrent :

- un cas nominal ;
- un tag invalide ;
- un 415 ;
- un 413 ;
- un 405 avec le header `Allow` ;
- un JSON malformé.

## Étape 5 — README

- Documenter la route avec un exemple `curl`, la réponse attendue et un renvoi vers la spec pour les erreurs.
- Ajouter une section « Dev » avec les commandes du `CLAUDE.md`.

## Étape 6 — Definition of Done (agent de test dédié)

- `uv run pytest` est vert.
- `uv run ruff format .` et `uv run ruff check` ne remontent aucune erreur.
- `uv run mypy .` ne remonte aucune erreur.
- `uv run mutmut run` ne laisse aucun mutant survivant sur `versioning.py`.
- Le serveur gunicorn est lancé et la route est vérifiée avec `curl -i` : nominal, pré-release, préfixe, 400 tags invalides, 400 liste vide, 400 JSON malformé, 415, 413, 404, 405. Pour chacun : le status, le `Content-Type` et le body.
- Aucune autre dépendance n'est ajoutée que `semver`, `mypy` et `mutmut`.
