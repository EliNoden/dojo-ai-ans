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

Computes the next SemVer version to tag from a list of existing tags (optional lowercase `v` prefix,
pre-releases and build metadata supported, see `docs/specs/next-version.md`).

```bash
curl -i -X POST http://localhost:8080/next-version \
  -H 'Content-Type: application/json' \
  -d '{"tags": ["v1.2.3", "1.0.0"], "bump": "patch"}'
# 200 {"next":"v1.2.4"}
```

- Body: `{"tags": string[], "bump": "major" | "minor" | "patch"}`.
- Errors are JSON `{"error": "<message>"}`: 400 (invalid body, empty list, `invalid tags: a, b`),
  415 (non-JSON `Content-Type`), 413 (body > 1 MiB), 404, 405.

## Development

```bash
uv run pytest                                   # tests (Flask test client + real server)
uv run ruff format . && uv run ruff check --fix # format + lint
uv run mypy .                                   # type check (strict)
uv run mutmut run && uv run mutmut results      # mutation testing on versioning.py
```
