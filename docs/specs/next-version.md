# Feature: `POST /next-version`

## Why

Release tooling needs to know the next version to tag, based on the tags
that already exist in a repo. Doing this by hand is error-prone: string sorting
puts `1.9.0` above `1.10.0`, pre-releases get mishandled, and the `v` prefix
gets dropped. One HTTP route gives a single, tested answer.

## Result

- New route `POST /next-version`, body `{"tags": string[], "bump": "major"|"minor"|"patch"}`,
  returns `200 {"next": "<version>"}`.
- Pure business logic in its own module (`versioning.py`); the Flask handler
  only validates input and delegates.
- Parsing and comparison use the `semver` library (python-semver). Only the
  optional `v` prefix is handled by our code.
- Global JSON error handlers, as CLAUDE.md requires (they don't exist yet):
  every HTTP error returns `{"error": "<message>"}`, including 404 and 405
  (with the `Allow` header kept), 413 (body > 1 MB) and 415 (non-JSON
  `Content-Type`).
- README updated (new route plus a curl example).

### Rules

- **Valid tag**: `[v]X.Y.Z[-pre][+build]`, strict SemVer 2.0:
  - X, Y and Z are integers without leading zeros.
  - The prefix is either nothing or a lowercase `v` (`V1.2.3` is invalid).
  - Pre-release: dot-separated identifiers of `[0-9A-Za-z-]`, none empty;
    numeric identifiers have no leading zeros (`-rc.1`, `-alpha`, `-0.3.7`).
  - Build: dot-separated identifiers of `[0-9A-Za-z-]`, none empty.
  - Anything else is invalid, including surrounding whitespace and a trailing `\n`.
- **Base** = the highest version under SemVer precedence:
  - X, then Y, then Z are compared numerically.
  - At equal X.Y.Z, a pre-release is lower than the final version.
  - Two pre-releases are compared with SemVer rules (`rc.1 < rc.2`).
  - Build metadata is ignored.
- **Bump**:
  - If the base is a pre-release, any bump just drops the suffix:
    `1.3.0-rc.1` with major, minor or patch → `1.3.0`.
  - Otherwise, a normal bump: major → `X+1.0.0`, minor → `X.Y+1.0`,
    patch → `X.Y.Z+1`.
- **Output**: the base's prefix plus `X.Y.Z`. It never carries a pre-release
  or build metadata.
- **Prefix**: taken from the highest tag. If the highest version appears both
  with and without the prefix (equal precedence, build ignored), `v` wins.

### Errors (400, `{"error": "..."}`)

Checked in this order; the first one that applies is returned:

| # | Condition | Message |
|---|-----------|---------|
| 1 | Body is not valid JSON (malformed, not UTF-8, too deeply nested) or not an object | `body must be a JSON object` |
| 2 | `tags` missing, or not a list of strings | `tags must be a list of strings` |
| 3 | `bump` missing, or not `major`/`minor`/`patch` | `bump must be one of: major, minor, patch` |
| 4 | `tags` is empty | `tags must not be empty` |
| 5 | At least one invalid tag | `invalid tags: <tags in input order, joined by ', ', repeats kept>` |

Other fields in the body are ignored.

## Use cases / edge cases

| tags | bump | → |
|------|------|---|
| `["1.2.3"]` | patch | `200 {"next":"1.2.4"}` |
| `["1.2.3"]` | minor | `1.3.0` |
| `["1.2.3"]` | major | `2.0.0` |
| `["1.9.0","1.10.0"]` | patch | `1.10.1` (numeric comparison) |
| `["1.2.9","1.3.0-rc.1"]` | patch | `1.3.0` (the pre-release counts and is finished) |
| `["1.3.0-rc.1","1.3.0"]` | patch | `1.3.1` (the final version beats its pre-release) |
| `["1.3.0-rc.1"]` | major | `1.3.0` (any bump finishes a pre-release) |
| `["1.3.0-rc.1","1.3.0-rc.2"]` | minor | `1.3.0` |
| `["v1.2.3","1.0.0"]` | patch | `v1.2.4` (prefix of the highest tag) |
| `["1.2.3","v1.0.0"]` | patch | `1.2.4` |
| `["1.2.3","v1.2.3"]` | patch | `v1.2.4` (`v` wins a tie) |
| `["1.2.3+b","v1.2.3+a"]` | patch | `v1.2.4` (build ignored, `v` wins) |
| `["v1.2.3+abc"]` | patch | `v1.2.4` (build dropped) |
| `["1.2.3","01.2.3","x","x"]` | patch | `400 invalid tags: 01.2.3, x, x` |
| `["V1.2.3"]`, `["1.2"]`, `["1.2.3-"]`, `["1.2.3+"]`, `["1.2.3-rc..1"]`, `["1.2.3-01"]`, `[" 1.2.3"]`, `["1.2.3\n"]`, `["vv1.2.3"]`, `[""]` | patch | 400 invalid tags |
| `[]` | patch | `400 tags must not be empty` |
| `[]` | `"huge"` | `400 bump must be ...` (bump is checked before empty) |
| `["1.2.3", 4]`, `"1.2.3"`, `null`, missing | patch | `400 tags must be a list of strings` |
| `["1.2.3"]` | `"Patch"`, `1`, missing | `400 bump must be one of: major, minor, patch` |
| `[1,2]` (body), `"x"`, malformed JSON, non-UTF-8 bytes, 100k levels of nesting | — | `400 body must be a JSON object` |
| `Content-Type: text/plain` | — | `415` JSON error |
| body > 1 MB | — | `413` JSON error (accepted Werkzeug limit: a chunked body without Content-Length of exactly 1 MiB also gets a 413) |
| `GET /next-version` | — | `405` JSON error plus `Allow: POST, OPTIONS` header |
| unknown route | — | `404` JSON error |

## Questions / options / decisions

| Question | Options | Decision |
|----------|---------|----------|
| Bump on a pre-release | npm semver style / always just finish / strip then bump | **Always just finish** (`1.3.0-rc.1` with major → `1.3.0`) |
| Allowed pre-release forms | any SemVer / only `-rc.N` | **Any SemVer pre-release** |
| Error priority | body→tags→bump→empty→invalid / tag content first | **body→tags→bump→empty→invalid** |
| Repeated invalid tags | keep / de-duplicate | **Keep** (strict input order) |
| Extra fields in the body | ignore / reject | **Ignore** |
| Error messages | one for missing, one for wrong type / one per field | **One per field** (table above) |
| Parsing | `semver` lib / hand-written regex | **`semver` lib**, prefix handled by us |
| Build metadata in the output | drop / keep | **Drop** |
| Global JSON error handlers (404/405/413/415) | — | **Added** in this feature (CLAUDE.md requirement) |
