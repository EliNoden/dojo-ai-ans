# Spec — `POST /next-version`

## Why

Une pipeline CI doit poser le prochain tag de release sans réimplémenter la logique SemVer dans chaque repo. Elle envoie les tags git existants et le type de bump ; le serveur renvoie le prochain tag à poser, en gardant la convention de préfixe du repo (`v` ou rien).

## Result

Route `POST /next-version`, `Content-Type: application/json`.

Requête :

```json
{ "tags": ["v1.2.3", "1.3.0-rc.1"], "bump": "patch" }
```

Réponse `200` :

```json
{ "next": "1.3.0" }
```

Règles :

- **Tag valide** : SemVer 2.0 strict (`X.Y.Z`, entiers sans zéro initial, pré-release `-…` et build `+…` optionnelles), précédé d'un `v` minuscule optionnel. Tout le reste est invalide (`V1.2.3`, `1.2`, `01.2.3`, espaces, `1.2.3-`, `1.2.3+`, `1.2.3-01`, chiffres non ASCII…).
- **Base** = tag de plus haute précédence SemVer : X, Y, Z numériquement ; à X.Y.Z égal, pré-release < finale ; pré-releases comparées selon SemVer (`rc.1 < rc.2`) ; build ignorée.
- **Bump** = sémantique npm (`semver.Version.next_version`) : une pré-release déjà au niveau du bump est terminée, sinon bump normal. Build metadata supprimée du résultat.
- **Préfixe** : celui du tag le plus haut ; à précédence égale (`v1.2.3` / `1.2.3`, `v1.2.3` / `1.2.3+abc`), `v` l'emporte.
- **Erreurs** : JSON `{"error": "<message>"}`, une seule erreur, la première dans l'ordre du tableau ci-dessous.

| # | Cas | Status | Message |
| --- | --- | --- | --- |
| 1 | `Content-Type` non JSON | 415 | `content type must be application/json` |
| 2 | Body > 1 Mo | 413 | `request body too large` |
| 3 | JSON malformé / non UTF-8 / trop imbriqué | 400 | `body must be valid JSON` |
| 4 | Racine JSON non objet | 400 | `body must be a JSON object` |
| 5 | Champs inconnus | 400 | `unknown fields: foo, bar` (ordre du body) |
| 6 | `tags` absent | 400 | `tags is required` |
| 7 | `tags` pas une liste de strings | 400 | `tags must be a list of strings` |
| 8 | `bump` absent | 400 | `bump is required` |
| 9 | `bump` hors `major`/`minor`/`patch` (sensible à la casse, non-string inclus) | 400 | `bump must be one of: major, minor, patch` |
| 10 | `tags` vide | 400 | `tags must not be empty` |
| 11 | Tags invalides | 400 | `invalid tags: x, x` (ordre d'entrée, doublons conservés) |
| — | Route inconnue | 404 | `not found` |
| — | Méthode non autorisée | 405 | `method not allowed` (header `Allow` conservé) |

## Use cases / edge cases

| Tags | Bump | `next` |
| --- | --- | --- |
| `["1.2.3"]` | patch | `1.2.4` |
| `["1.2.3"]` | minor | `1.3.0` |
| `["1.2.3"]` | major | `2.0.0` |
| `["1.9.0", "1.10.0"]` | patch | `1.10.1` (comparaison numérique) |
| `["1.2.9", "1.3.0-rc.1"]` | patch | `1.3.0` (la pré-release compte et est terminée) |
| `["1.3.0-rc.1", "1.3.0"]` | patch | `1.3.1` (finale > pré-release) |
| `["1.3.0-rc.1"]` | minor | `1.3.0` |
| `["1.3.0-rc.1"]` | major | `2.0.0` |
| `["2.0.0-rc.1"]` | major | `2.0.0` |
| `["1.3.1-rc.1"]` | minor | `1.4.0` |
| `["1.3.0-rc.1", "1.3.0-rc.2"]` | patch | `1.3.0` |
| `["v1.2.3", "1.2.4"]` | patch | `1.2.5` (préfixe du plus haut) |
| `["v1.2.4", "1.2.3"]` | patch | `v1.2.5` |
| `["1.2.3", "v1.2.3"]` | patch | `v1.2.4` (égalité → `v`) |
| `["1.2.3+abc", "v1.2.3"]` | patch | `v1.2.4` (build ignorée, égalité → `v`) |
| `["1.2.3+abc"]` | minor | `1.3.0` (build supprimée) |
| `["v1.0.0-rc.1"]` | patch | `v1.0.0` |
| `["1.0.0", "V1.0.0", "x", "1.0.0", "x"]` | patch | 400 `invalid tags: V1.0.0, x, x` |
| `[]` | patch | 400 `tags must not be empty` |
| `[]` | `"PATCH"` | 400 `bump must be one of: major, minor, patch` (priorité) |
| `["1.0.0", 1]` | patch | 400 `tags must be a list of strings` |

## Questions / options / decisions

| # | Question | Options | Décision |
| --- | --- | --- | --- |
| Q1 | Besoin | CI release tagging / kata / outil humain | **CI release tagging** |
| Q2 | Grammaire pré-release | SemVer 2.0 complet / `-rc.N` seul / comme build | **SemVer 2.0 complet** |
| Q3 | Bump minor/major d'une pré-release | npm / toujours terminer / terminer en patch seulement | **Sémantique npm** |
| Q4 | Parsing / comparaison | python-semver / packaging / regex maison | **python-semver** (3.1.0, vérifié : parse strict, précédence, `next_version` npm) ; seul le préfixe `v` est géré à la main |
| Q5 | Plusieurs erreurs | première dans l'ordre forme → métier / toutes concaténées | **Une seule, ordre du tableau** |
| Q6 | Doublons dans les tags invalides | garder / dédupliquer | **Garder** |
| Q7 | Champs inconnus | ignorer / rejeter | **Rejeter (400)** |
| Q8 | Build metadata dans le résultat | supprimer / conserver | **Supprimer** |
| Q9 | Position du check champs inconnus | juste après le JSON / après tags et bump | **Juste après le JSON** |
| Q10 | Messages d'erreur | proposés / personnalisés | **Proposés (tableau ci-dessus)** |

Hors scope : préfixes autres que `v`, tri/filtrage de tags non SemVer, génération de pré-releases.
