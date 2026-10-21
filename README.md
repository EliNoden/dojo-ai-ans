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


## Routes

### `POST /next-version`

Returns the next version to tag, from the existing tags and a bump type.

- Body (`Content-Type: application/json`, max 1 MB): `{"tags": string[], "bump": "major" | "minor" | "patch"}`
- Tags are strict SemVer 2.0 with an optional lowercase `v` prefix (`v1.2.3`, `1.3.0-rc.1`, `1.2.3+build`).
- The base is the highest tag by SemVer precedence. A pre-release base is just finished (`1.3.0-rc.1` → `1.3.0`, whatever the bump); otherwise it is bumped.
- The result keeps the base's `v` prefix (`v` wins a tie) and never carries a pre-release or build metadata.

```bash
curl -i -X POST http://localhost:8080/next-version \
  -H 'Content-Type: application/json' \
  -d '{"tags": ["v1.9.0", "v1.10.0"], "bump": "minor"}'
# HTTP/1.1 200 OK
# {"next":"v1.11.0"}
```

### Errors

Every error is JSON: `{"error": "<message>"}`.

| Status | When |
|--------|------|
| 400 | `body must be a JSON object`, `tags must be a list of strings`, `bump must be one of: major, minor, patch`, `tags must not be empty`, `invalid tags: <tags>` (checked in this order) |
| 404 | Unknown route |
| 405 | Wrong method (the `Allow` header is kept) |
| 413 | Body over 1 MB |
| 415 | `Content-Type` is not JSON |

## Development

```bash
uv run pytest                               # tests (includes a real gunicorn server)
uv run ruff format . && uv run ruff check --fix
uv run mypy .
uv run mutmut run && uv run mutmut results  # mutation testing on versioning.py
```
