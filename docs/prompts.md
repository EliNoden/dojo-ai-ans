## prompt 1 — contrat seul

Branche `feat/prompt-1` depuis `main`.

Ajoute une route POST /next-version qui calcule la prochaine version à partir d'une liste de tags.
Body JSON : { "tags": string[], "bump": "major" | "minor" | "patch" }
Réponse : { "next": "<version>" }

## prompt 2 — contrat + spec

Branche `feat/prompt-2` depuis `main`.

Ajoute une route qui calcule la prochaine version à partir d'une liste de tags.
Contrat d'interface :
  - Route : POST /next-version
  - Header : Content-Type: application/json
  - Body JSON : { "tags": string[], "bump": "major" | "minor" | "patch" }
  - Réponse 200 : { "next": "<version>" }
Règles :
  - Un tag valide a la forme X.Y.Z (entiers sans zéro initial), avec préfixe "v" minuscule optionnel (v1.2.3 et 1.2.3 valides),
    une pré-release optionnelle "-rc.1" et une build metadata optionnelle "+abc"
    (identifiants alphanumériques ou "-", non vides, séparés par des points). Tout le reste est invalide.
  - La base est la plus haute version : X, puis Y, puis Z comparés numériquement (1.10.0 > 1.9.0).
    À X.Y.Z égal, une pré-release est plus petite que la version finale (1.3.0-rc.1 < 1.3.0),
    mais elle compte (1.3.0-rc.1 > 1.2.9). La build metadata est ignorée dans la comparaison.
  - Le résultat est la base bumpée ; bumper une pré-release la termine (1.3.0-rc.1 + patch → 1.3.0).
  - Le résultat garde le préfixe du tag le plus haut. En cas d'égalité (v1.2.3 et 1.2.3), "v" l'emporte.
Erreurs (status 400, body { "error": "<message>" }) :
  - Un ou plusieurs tags invalides : "invalid tags: <tags invalides dans l'ordre d'entrée, séparés par ', '>"
  - Liste vide : "tags must not be empty"
  - Body non-JSON, tags absent / pas une liste de strings, bump absent / hors major|minor|patch : message explicite.

## prompt 3 — contrat + spec + outils

Branche `feat/prompt-3` depuis `feat/claude-skills` (skill /feature), avec CLAUDE.md.

/feature Ajoute une route qui calcule la prochaine version à partir d'une liste de tags.
Contrat d'interface :
  - Route : POST /next-version
  - Header : Content-Type: application/json
  - Body JSON : { "tags": string[], "bump": "major" | "minor" | "patch" }
  - Réponse 200 : { "next": "<version>" }
Règles :
  - Un tag valide a la forme X.Y.Z (entiers sans zéro initial), avec préfixe "v" minuscule optionnel (v1.2.3 et 1.2.3 valides),
    une pré-release optionnelle "-rc.1" et une build metadata optionnelle "+abc"
    (identifiants alphanumériques ou "-", non vides, séparés par des points). Tout le reste est invalide.
  - La base est la plus haute version : X, puis Y, puis Z comparés numériquement (1.10.0 > 1.9.0).
    À X.Y.Z égal, une pré-release est plus petite que la version finale (1.3.0-rc.1 < 1.3.0),
    mais elle compte (1.3.0-rc.1 > 1.2.9). La build metadata est ignorée dans la comparaison.
  - Le résultat est la base bumpée ; bumper une pré-release la termine (1.3.0-rc.1 + patch → 1.3.0).
  - Le résultat garde le préfixe du tag le plus haut. En cas d'égalité (v1.2.3 et 1.2.3), "v" l'emporte.
Erreurs (status 400, body { "error": "<message>" }) :
  - Un ou plusieurs tags invalides : "invalid tags: <tags invalides dans l'ordre d'entrée, séparés par ', '>"
  - Liste vide : "tags must not be empty"
  - Body non-JSON, tags absent / pas une liste de strings, bump absent / hors major|minor|patch : message explicite.
