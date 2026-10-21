# Specs server

The documentation of the server for the specs services.

## Install

Requires Python 3.14+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

## Local run

```bash
uv run gunicorn -w 2 -b 0.0.0.0:8080 "specs:create_app()" --timeout 180 --log-level=debug
```

Server listens on http://localhost:8080. Check it runs:

```bash
curl http://localhost:8080/hello
# {"message":"Hello, the specs server is running"}
```

## API

All errors are JSON: `{"error": "<message>"}` (including 404 and 405, which keep the `Allow` header).

### `POST /next-version`

Computes the next version from a list of git tags. Nothing is persisted.

Request (`Content-Type: application/json`, body up to 1 MB):

```json
{ "tags": ["v1.2.3", "v1.2.4"], "bump": "patch" }
```

- `tags`: list of strings `[v]X.Y.Z[-prerelease][+build]` (ASCII, no leading zeros in `X.Y.Z`, at most 15 digits each, lowercase `v` only).
- `bump`: `major`, `minor` or `patch`.

```bash
curl -i -X POST http://localhost:8080/next-version \
  -H 'Content-Type: application/json' \
  -d '{"tags": ["v1.2.3", "v1.2.4"], "bump": "patch"}'
# 200 {"next":"v1.2.5"}
```

Rules:

- The base is the highest tag by SemVer precedence (build metadata ignored; a pre-release is lower than its release: `1.3.0-rc.1 < 1.3.0`).
- Only `patch` ends a pre-release (`1.3.0-rc.1` + patch = `1.3.0`); `minor` and `major` bump from `X.Y.Z` (`1.4.0`, `2.0.0`).
- The result has no pre-release nor build metadata. It starts with `v` if at least one tag equal in precedence to the highest has it.

Errors:

| Status | Message |
|---|---|
| 400 | `body must be a JSON object` (malformed, non UTF-8, too deeply nested or non-object JSON) |
| 400 | `tags must be a list of strings` |
| 400 | `bump must be one of: major, minor, patch` |
| 400 | `tags must not be empty` |
| 400 | `invalid tags: a, b` (in input order, duplicates listed each time) |
| 404 / 405 | unknown route / method not allowed |
| 413 | body larger than 1 MB |
| 415 | `Content-Type` is not JSON |

Checks are done in this order: body, `tags` type, `bump`, empty `tags`, invalid tags.

## Development

```bash
uv run pytest                               # tests
uv run ruff format . && uv run ruff check --fix
uv run mypy .                               # typing
uv run mutmut run && uv run mutmut results  # mutation testing (versions.py)
```
