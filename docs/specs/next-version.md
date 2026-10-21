# Spec — `POST /next-version`

## Why

Release tooling needs the next version to tag from an existing list of git tags, without each caller
re-implementing SemVer parsing, ordering and bump rules (prefix `v`, pre-releases, build metadata).
One HTTP route centralises that logic so every pipeline computes the same answer.

## Result

- Route `POST /next-version`, `Content-Type: application/json`.
- Body `{ "tags": string[], "bump": "major" | "minor" | "patch" }`.
- `200` → `{ "next": "<version>" }`.
- Errors → `{ "error": "<message>" }` (JSON for every HTTP error, including 404/405/413/415).
- Pure business logic in `versioning.py` (no Flask), HTTP layer in `specs.py` validates and delegates.
- Parsing / comparison / bump delegated to the `semver` library (SemVer 2.0.0), no home-made regex.

## Use cases / edge cases

| Input tags | bump | Expected |
|---|---|---|
| `["1.2.3"]` | patch | `200 {"next": "1.2.4"}` |
| `["1.2.3"]` | minor | `1.3.0` |
| `["1.2.3"]` | major | `2.0.0` |
| `["1.9.0", "1.10.0"]` | patch | `1.10.1` (numeric compare) |
| `["1.2.9", "1.3.0-rc.1"]` | patch | `1.3.0` (pre-release counts, bump terminates it) |
| `["1.3.0-rc.1", "1.3.0"]` | patch | `1.3.1` (final > pre-release) |
| `["1.3.0-rc.1"]` | minor | `1.3.0` |
| `["1.3.1-rc.1"]` | minor | `1.4.0` |
| `["2.0.0-rc.1"]` | major | `2.0.0` |
| `["1.3.0-rc.1"]` | major | `2.0.0` |
| `["1.2.3+abc", "1.2.2"]` | patch | `1.2.4` (build ignored, dropped from result) |
| `["v1.2.3", "1.0.0"]` | patch | `v1.2.4` (prefix of highest kept) |
| `["1.2.3", "v1.2.3"]` | patch | `v1.2.4` (tie → `v` wins, any order) |
| `["1.2.3+a", "v1.2.3+b"]` | patch | `v1.2.4` (tie ignoring build → `v` wins) |
| `[]` | patch | `400 "tags must not be empty"` |
| `["1.2", "1.2.3", "V1.2.3", "01.2.3"]` | patch | `400 "invalid tags: 1.2, V1.2.3, 01.2.3"` |
| `["x", "x"]` | patch | `400 "invalid tags: x, x"` (duplicates kept, input order) |
| other invalid: `""`, `" 1.2.3"`, `"1.2.3-"`, `"1.2.3+"`, `"1.2.3-a..b"`, `"1.2.3-rc_1"`, `"vv1.2.3"`, `"1.2.3-rc.01"` | | listed in `invalid tags` |
| body not JSON (malformed, non UTF-8) | | `400 "body must be valid JSON"` |
| body JSON but not an object (`[]`, `"x"`, `null`) | | `400 "body must be a JSON object"` |
| `tags` missing / not a list / contains non-string | | `400 "tags must be a list of strings"` |
| `bump` missing / not one of major, minor, patch | | `400 "bump must be one of: major, minor, patch"` |
| `Content-Type` not JSON | | `415` JSON error |
| body > 1 MB | | `413` JSON error |
| `GET /next-version` | | `405` JSON error, `Allow` header kept |
| unknown route | | `404` JSON error |

## Questions / options / decisions

Non-interactive run: each question resolved with the recommended option.

1. **Parsing: library vs regex?**
   a) `semver` lib (recommended) · b) home-made regex.
   → **a**. CLAUDE.md: known format → dedicated lib. Strip optional lowercase `v`, then `semver.Version.parse`.
   Consequence: numeric pre-release identifiers with a leading zero (`1.2.3-rc.01`) are **invalid**, as in SemVer 2.0.0.
   This is stricter than the literal brief ("alphanumeric or -"), accepted as aligning with the standard.
2. **Bump of a pre-release for minor/major?** Brief only gives the patch example.
   a) npm/SemVer `inc` semantics via `Version.next_version` (recommended) · b) always drop the pre-release only · c) only patch terminates.
   → **a**. `1.3.0-rc.1`+minor → `1.3.0`, `1.3.1-rc.1`+minor → `1.4.0`, `2.0.0-rc.1`+major → `2.0.0`.
3. **Order among pre-releases of the same X.Y.Z** (`rc.1` vs `rc.2`, `alpha` vs `beta`)?
   → SemVer 2.0.0 precedence (lib default). No impact on result anyway: bumping any of them gives the same version.
4. **Validation order when several errors?**
   → body JSON → body object → `tags` type → `bump` → empty list → invalid tags. First error wins.
5. **Build metadata in result?** → dropped (bump produces a clean version).
6. **Duplicates in invalid tags?** → kept, input order (message lists them as received).
7. **Content-Type check strictness?** → Flask `request.is_json` (accepts `application/json; charset=utf-8` and `+json`).
8. **413 limit** → Flask `MAX_CONTENT_LENGTH = 1 MiB`.
