# Spec : POST /next-version

## Why

Calculer la prochaine version d'un projet à partir de la liste de ses tags git, sans que chaque client réimplémente la comparaison de versions et le bump. La route est une fonction pure exposée en HTTP : aucune donnée persistée.

## Result

### Contrat

- Route : `POST /next-version`
- Header : `Content-Type: application/json`
- Body : `{ "tags": string[], "bump": "major" | "minor" | "patch" }`
- 200 : `{ "next": "<version>" }`
- Erreurs : status 400 (sauf 404/405/413/415 génériques), body `{ "error": "<message>" }`

### Grammaire d'un tag valide (ASCII uniquement)

```
[v]X.Y.Z[-prerelease][+build]
```

- `v` minuscule optionnel (`V1.2.3` invalide).
- `X`, `Y`, `Z` : entiers sans zéro initial (`0` valide, `01` invalide), **1 à 15 chiffres** (décision : au-delà, tag invalide).
- `prerelease` : identifiants non vides séparés par `.`, chacun `[0-9A-Za-z-]+` (zéros initiaux autorisés, ex. `rc.01`).
- `build` : même forme que `prerelease`.
- Tout le reste est invalide (espaces, vide, `1.2`, `1.2.3.4`, `1.2.3-`, `1.2.3+`, `1..2`, chiffres Unicode, etc.).

### Comparaison (précédence)

1. `X`, puis `Y`, puis `Z`, comparés numériquement (`1.10.0 > 1.9.0`).
2. À `X.Y.Z` égal : pré-release < version finale (`1.3.0-rc.1 < 1.3.0`), mais `1.3.0-rc.1 > 1.2.9`.
3. Entre deux pré-releases de même `X.Y.Z` : précédence SemVer complète, identifiant par identifiant :
   - numérique vs numérique : comparaison numérique (`rc.2 < rc.10`) ; implémentée par (longueur, chaîne) pour éviter toute conversion en `int` ;
   - alphanumérique vs alphanumérique : ordre lexical ASCII ;
   - numérique < alphanumérique ;
   - à préfixe égal, la liste la plus courte est la plus petite (`rc < rc.1`).
4. La build metadata est ignorée.

### Calcul du résultat

La base est la plus haute version. Le résultat est écrit sans pré-release ni build metadata :

| Base | bump | Résultat |
|---|---|---|
| `1.2.3` | patch | `1.2.4` |
| `1.2.3` | minor | `1.3.0` |
| `1.2.3` | major | `2.0.0` |
| `1.3.0-rc.1` | patch | `1.3.0` (termine la pré-release) |
| `1.3.0-rc.1` | minor | `1.4.0` |
| `1.3.0-rc.1` | major | `2.0.0` |

Préfixe : celui du tag le plus haut. Si plusieurs tags sont égaux en précédence (ex. `v1.2.3`, `1.2.3`, `1.2.3+abc`), `v` l'emporte dès qu'au moins un de ces tags l'a. L'égalité s'entend sur la précédence (build metadata ignorée).

### Erreurs 400

| Cas | Message |
|---|---|
| Body non JSON / JSON malformé / non UTF-8 / non objet | message explicite (ex. `body must be a JSON object`) |
| `tags` absent ou pas une liste de strings | `tags must be a list of strings` |
| `bump` absent ou hors `major\|minor\|patch` | `bump must be one of: major, minor, patch` |
| `tags` vide | `tags must not be empty` |
| Tags invalides | `invalid tags: <tags invalides dans l'ordre d'entrée, séparés par ', '>` (doublons listés à chaque occurrence) |

Ordre de validation (la première erreur gagne) : body JSON objet → `tags` (type) → `bump` → `tags` vide → tags invalides.

### Erreurs génériques (CLAUDE.md)

- `Content-Type` non JSON : 415 ; body > 1 Mo : 413 ; 404 et 405 (avec header `Allow`) en JSON `{"error": ...}`.
- Jamais de 5xx sur entrée client (JSON très imbriqué, non UTF-8, types inattendus).

## Cas d'usage / cas limites

Nominaux :

- `["v1.2.3", "v1.2.4"]` + patch → `v1.2.5`
- `["1.9.0", "1.10.0"]` + minor → `1.11.0`
- `["1.2.9", "1.3.0-rc.1"]` + patch → `1.3.0`
- `["1.3.0-rc.1", "1.3.0"]` + patch → `1.3.1`
- `["1.3.0-rc.2", "1.3.0-rc.10"]` + minor → `1.4.0`
- `["v1.2.3", "1.2.3"]` + patch → `v1.2.4` (égalité : `v` l'emporte)
- `["1.2.3+abc", "1.2.3+def"]` + patch → `1.2.4` (build ignorée)
- `["0.0.0"]` + major → `1.0.0`
- Un seul tag.

Limites / invalides :

- `["1.2.3", "foo", "01.2.3", "bar"]` → `invalid tags: foo, 01.2.3, bar`
- `["foo", "foo"]` → `invalid tags: foo, foo`
- `["V1.2.3"]`, `[" 1.2.3"]`, `["1.2.3\n"]`, `["1.2"]`, `["1.2.3-"]`, `["1.2.3-rc..1"]`, `["1.2.3+"]`, `["١.٢.٣"]` (chiffres arabes-indiques) → invalides
- Composant de 16 chiffres ou plus (ex. 5000 chiffres) → invalide (pas de 5xx)
- `[]` → `tags must not be empty`
- `[1, 2]`, `"1.2.3"`, `null`, `tags` absent → erreur de type
- `bump` absent, `"MAJOR"`, `"premajor"`, `1`, `null` → erreur de bump
- `{"tags": [], "bump": "x"}` → erreur de bump (structure d'abord)
- Body `[]`, `"x"`, `42`, `null`, `{`, octets non UTF-8, imbrication très profonde → 400
- `GET /next-version` → 405 JSON avec `Allow: POST`
- `Content-Type: text/plain` → 415 ; body > 1 Mo → 413

## Questions / options / décisions

| # | Question | Décision |
|---|---|---|
| 1 | Bump minor/major sur une pré-release | Seul `patch` termine la pré-release ; minor/major bumpent normalement depuis `X.Y.Z` |
| 2 | Ordre entre pré-releases de même `X.Y.Z` | Précédence SemVer complète |
| 3 | Parsing | Regex ASCII stricte maison dans un module dédié (la grammaire diffère de SemVer : préfixe `v`, zéros initiaux autorisés dans les ids de pré-release) |
| 4 | Très grands entiers | Composant `X.Y.Z` limité à 15 chiffres, sinon tag invalide ; comparaison des ids numériques de pré-release par (longueur, chaîne), sans `int` |
| 5 | Priorité des erreurs | Structure d'abord (body → tags type → bump → tags vide → tags invalides) |
| 6 | Sortie et doublons | Sortie sans build ni pré-release ; doublons invalides listés à chaque occurrence |

Points ouverts (à valider) :

- La limite de 15 chiffres déroge à « entiers sans zéro initial » de l'énoncé : un tag à 16 chiffres est invalide alors qu'il respecte la grammaire. OK ?
- Le message d'erreur exact pour body non JSON / non objet (`body must be a JSON object`) et pour `tags` / `bump` (voir tableau) n'est pas imposé par l'énoncé. OK ?
- Découpage prévu : logique pure dans `versions.py` (parse, compare, bump), handler fin dans `specs.py`.
- Outils dev manquants à ajouter via `uv add --dev` : `mypy`, `mutmut`, `hypothesis` (validation requise avant toute commande).
